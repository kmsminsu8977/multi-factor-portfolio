"""멀티팩터 포트폴리오 baseline 엔진.

이 모듈은 `KAIST-DFMBA/Quant-and-Factor-Investment-Strategies/Final`의
제출본과 답안본을 비교해, 재현 가능한 연구 코드로 다시 구성한 버전이다.

핵심 구현 기준은 다음과 같다.

1. GP, OP, PER, PBR, 12개월 모멘텀, 6개월 모멘텀을 같은 방향의 점수로 바꾼다.
2. 개별 특성값을 먼저 z-score로 표준화한다.
3. quality, value, momentum 카테고리 점수를 다시 z-score로 표준화한다.
4. 세 카테고리의 합을 최종 z-score로 바꾼 뒤 상위 후보를 고른다.
5. 선택 후보에 대해 1% 이상, 5% 이하 비중 제약을 둔 최소분산 포트폴리오를 계산한다.

원본 시험 데이터는 저장소에 포함하지 않는다. 대신 `data/sample/factor_input_panel.csv`에
합성 예시를 두어 계산 방향, 정규화 순서, 제약 조건을 빠르게 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd

try:  # scipy가 없는 환경에서도 입력/점수 계산까지는 살펴볼 수 있게 선택 의존성으로 둔다.
    from scipy.optimize import minimize
except ImportError:  # pragma: no cover - 실행 환경 의존 fallback
    minimize = None


PROJECT: Final[dict[str, str]] = {
    "title_ko": "멀티팩터 포트폴리오",
    "title_en": "Multi-Factor Portfolio",
    "category": "Factor Investing",
    "question": "복수 팩터를 같은 척도로 표준화하면 어떤 종목이 안정적으로 상위권에 남는가?",
}

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
DATA_PATH: Final[Path] = ROOT / "data" / "sample" / "factor_input_panel.csv"
TABLE_DIR: Final[Path] = ROOT / "outputs" / "tables"

OUTPUT_PATHS: Final[dict[str, Path]] = {
    "factor_characteristics": TABLE_DIR / "factor_characteristics.csv",
    "factor_scores": TABLE_DIR / "factor_scores.csv",
    "portfolio_weights": TABLE_DIR / "portfolio_weights.csv",
    "comparison_summary": TABLE_DIR / "comparison_summary.csv",
    # 기존 README와 노트북에서 참조하던 파일명은 유지하되, 내용은 최종 포트폴리오 비중표로 맞춘다.
    "baseline_results": TABLE_DIR / "baseline_results.csv",
}

RETURN_COLUMNS: Final[tuple[str, ...]] = tuple(f"ret_m{i:02d}" for i in range(1, 13))
METADATA_COLUMNS: Final[tuple[str, ...]] = ("asset", "name", "sector", "market_cap")
RAW_FACTOR_COLUMNS: Final[tuple[str, ...]] = ("gp", "op", "per", "pbr")
REQUIRED_COLUMNS: Final[tuple[str, ...]] = METADATA_COLUMNS + RAW_FACTOR_COLUMNS + RETURN_COLUMNS


@dataclass(frozen=True)
class PortfolioConfig:
    """포트폴리오 구성 파라미터.

    `top_n=30`, `lower_bound=0.01`, `upper_bound=0.05`는 기말 답안 예제의
    최소분산 포트폴리오 제약식과 동일하다. `covariance_shrinkage`는 12개월처럼 짧은
    표본으로 많은 종목의 공분산을 추정할 때 생기는 특이행렬 문제를 줄이기 위한 안정화
    파라미터다.
    """

    top_n: int = 30
    lower_bound: float = 0.01
    upper_bound: float = 0.05
    covariance_shrinkage: float = 0.25


def load_factor_panel(path: Path = DATA_PATH) -> pd.DataFrame:
    """합성 factor/return 패널을 읽고 기본 검증을 수행한다.

    입력 파일은 이미 시험 원천 엑셀의 가격/재무제표를 연구용 패널로 정리한 형태다.
    `ret_m01`은 가장 오래된 월, `ret_m12`는 가장 최근 월 수익률이며, 모멘텀은 이
    12개월 월간 수익률에서 다시 계산한다. 이렇게 해야 제출본의 오류였던
    `pct_change(..., limit=6/12)`와 누적 6/12개월 수익률의 혼동을 피할 수 있다.
    """

    df = pd.read_csv(path)
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"입력 파일에 필요한 컬럼이 없습니다: {missing}")

    if df["asset"].duplicated().any():
        duplicated = sorted(df.loc[df["asset"].duplicated(), "asset"].unique())
        raise ValueError(f"asset 식별자가 중복되었습니다: {duplicated}")

    numeric_columns = ("market_cap",) + RAW_FACTOR_COLUMNS + RETURN_COLUMNS
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # PER/PBR은 양수인 기업만 사용한다. 답안본도 EPS와 BPS가 양수인 기업만 남긴 뒤
    # 낮은 PER/PBR이 좋은 특성이 되도록 부호를 뒤집었다.
    usable = df.dropna(subset=list(REQUIRED_COLUMNS)).copy()
    usable = usable[(usable["per"] > 0) & (usable["pbr"] > 0)]
    if usable.empty:
        raise ValueError("분석 가능한 행이 없습니다. PER/PBR 양수 조건과 결측값을 확인하세요.")
    return usable.reset_index(drop=True)


def zscore(series: pd.Series) -> pd.Series:
    """횡단면 z-score를 계산한다.

    팩터끼리는 단위가 다르다. GP/A는 비율, PER/PBR은 배수, 모멘텀은 누적수익률이므로
    원값을 직접 더하면 배율이 큰 변수가 최종 점수를 지배한다. z-score는 각 시점의
    횡단면 평균을 0, 표준편차를 1로 바꾸어 특성값의 상대적 위치만 비교하게 해준다.
    """

    values = pd.to_numeric(series, errors="coerce")
    std = values.std(ddof=1)
    if pd.isna(std) or std == 0:
        return pd.Series(np.zeros(len(values)), index=series.index, dtype=float)
    return (values - values.mean()) / std


def compute_factor_characteristics(panel: pd.DataFrame) -> pd.DataFrame:
    """원천 입력에서 여섯 개 기업 특성값을 만든다.

    - `gp`: 매출총이익 / 총자산. 퀄리티 중 수익성을 나타낸다.
    - `op`: EBIT / 총자본. 영업이익 창출력을 나타낸다.
    - `neg_per`: 낮은 PER이 매력적이므로 `-PER`로 부호를 바꾼다.
    - `neg_pbr`: 낮은 PBR이 매력적이므로 `-PBR`로 부호를 바꾼다.
    - `mom12`: 최근 12개월 월간 수익률의 누적수익률이다.
    - `mom6`: 최근 6개월 월간 수익률의 누적수익률이다.
    """

    returns = panel.loc[:, RETURN_COLUMNS]
    characteristics = panel.loc[:, METADATA_COLUMNS].copy()
    characteristics["gp"] = panel["gp"]
    characteristics["op"] = panel["op"]
    characteristics["neg_per"] = -panel["per"]
    characteristics["neg_pbr"] = -panel["pbr"]
    characteristics["mom12"] = (1.0 + returns).prod(axis=1) - 1.0
    characteristics["mom6"] = (1.0 + returns.loc[:, RETURN_COLUMNS[-6:]]).prod(axis=1) - 1.0

    ordered = [
        "asset",
        "name",
        "sector",
        "market_cap",
        "gp",
        "op",
        "neg_per",
        "neg_pbr",
        "mom12",
        "mom6",
    ]
    return characteristics.loc[:, ordered].sort_values("asset").reset_index(drop=True)


def compute_factor_scores(characteristics: pd.DataFrame) -> pd.DataFrame:
    """특성값 z-score, 카테고리 점수, 최종 점수를 계산한다.

    답안본은 `firm_char.apply(normalize)`로 개별 특성을 먼저 표준화한 뒤,
    quality/value/momentum 카테고리 합산값을 다시 표준화했다. 이 구현도 같은 순서를
    따른다. 제출본처럼 rank를 만든 뒤 z-score를 계산하면 rank 방향과 점수 방향을
    동시에 관리해야 해 부호 실수가 생기기 쉽다.
    """

    scores = characteristics.loc[:, METADATA_COLUMNS].copy()
    scores["gp_z"] = zscore(characteristics["gp"])
    scores["op_z"] = zscore(characteristics["op"])
    scores["neg_per_z"] = zscore(characteristics["neg_per"])
    scores["neg_pbr_z"] = zscore(characteristics["neg_pbr"])
    scores["mom12_z"] = zscore(characteristics["mom12"])
    scores["mom6_z"] = zscore(characteristics["mom6"])

    # 각 카테고리 안에서 2개 특성의 합을 한 번 더 표준화한다. 이렇게 하면
    # quality/value/momentum 세 카테고리가 최종 합성 점수에서 동일한 단위와 분산을 가진다.
    scores["quality_score"] = zscore(scores["gp_z"] + scores["op_z"])
    scores["value_score"] = zscore(scores["neg_per_z"] + scores["neg_pbr_z"])
    scores["momentum_score"] = zscore(scores["mom12_z"] + scores["mom6_z"])
    scores["final_score"] = zscore(scores["quality_score"] + scores["value_score"] + scores["momentum_score"])
    scores["final_rank"] = scores["final_score"].rank(ascending=False, method="first").astype(int)

    ordered = [
        "asset",
        "name",
        "sector",
        "market_cap",
        "gp_z",
        "op_z",
        "neg_per_z",
        "neg_pbr_z",
        "mom12_z",
        "mom6_z",
        "quality_score",
        "value_score",
        "momentum_score",
        "final_score",
        "final_rank",
    ]
    return scores.loc[:, ordered].sort_values("final_rank").reset_index(drop=True)


def select_candidates(scores: pd.DataFrame, panel: pd.DataFrame, config: PortfolioConfig) -> pd.DataFrame:
    """최종 점수 상위 후보를 선택한다.

    최소분산 포트폴리오는 과거 12개월 수익률 공분산을 필요로 한다. 따라서 점수가 높아도
    수익률 이력이 결측이면 후보에서 제외하고, 다음 순위 종목으로 채운다. 이는 제출본에서
    결측 종목을 제거한 뒤 후보를 다시 확장하려던 의도를 명확한 함수로 분리한 것이다.
    """

    returns_available = panel.set_index("asset").loc[:, RETURN_COLUMNS].notna().all(axis=1)
    valid_assets = set(returns_available[returns_available].index)
    candidates = scores[scores["asset"].isin(valid_assets)].sort_values("final_score", ascending=False)
    selected_count = min(config.top_n, len(candidates))
    if selected_count == 0:
        raise ValueError("수익률 이력이 있는 후보 종목이 없습니다.")
    return candidates.head(selected_count).reset_index(drop=True)


def make_return_matrix(panel: pd.DataFrame, assets: list[str]) -> pd.DataFrame:
    """선택 종목의 월간 수익률 행렬을 만든다.

    반환값은 행이 월, 열이 종목인 형태다. `DataFrame.cov()`가 종목 간 공분산 행렬을
    계산하도록 이 방향을 유지한다.
    """

    return (
        panel.set_index("asset")
        .loc[assets, RETURN_COLUMNS]
        .transpose()
        .rename_axis(index="month", columns="asset")
        .astype(float)
    )


def nearest_positive_semidefinite(matrix: np.ndarray) -> np.ndarray:
    """공분산 행렬을 가장 가까운 양의 준정부호 행렬로 보정한다.

    표본 수가 짧고 종목 수가 많으면 표본 공분산이 수치적으로 음의 고유값을 가질 수 있다.
    최소분산 최적화의 이차형식은 양의 준정부호 행렬을 전제하므로, 음수 고유값을 0으로
    잘라 안정적인 최적화 입력으로 바꾼다.
    """

    symmetric = (matrix + matrix.T) / 2.0
    eigvals, eigvecs = np.linalg.eigh(symmetric)
    eigvals = np.clip(eigvals, 0.0, None)
    psd = eigvecs @ np.diag(eigvals) @ eigvecs.T
    return (psd + psd.T) / 2.0


def estimate_covariance(return_matrix: pd.DataFrame, shrinkage: float) -> np.ndarray:
    """짧은 수익률 표본에서 안정적인 공분산 행렬을 추정한다.

    샘플은 12개월 수익률로 30개 후보를 최적화하므로 표본 공분산만 쓰면 행렬의 rank가
    부족하다. 대각 행렬 쪽으로 일부 shrinkage를 주면 종목 간 공분산 정보는 유지하면서도
    과도한 헤지 조합이 만들어지는 문제를 줄일 수 있다.
    """

    if not 0.0 <= shrinkage <= 1.0:
        raise ValueError("covariance_shrinkage는 0과 1 사이여야 합니다.")

    sample_cov = return_matrix.cov().to_numpy(dtype=float)
    diagonal_cov = np.diag(np.diag(sample_cov))
    shrunk = (1.0 - shrinkage) * sample_cov + shrinkage * diagonal_cov
    return nearest_positive_semidefinite(shrunk)


def minimum_variance_weights(return_matrix: pd.DataFrame, config: PortfolioConfig) -> pd.Series:
    """비중 하한/상한 제약을 반영한 최소분산 포트폴리오를 계산한다.

    목적함수는 `w.T @ Sigma @ w`이고, 제약은 `sum(w)=1`, `lower<=w_i<=upper`다.
    기말 답안의 수식은 앞에 1/2이 붙지만, 상수배는 최적해를 바꾸지 않는다.
    """

    n_assets = return_matrix.shape[1]
    if config.lower_bound * n_assets > 1.0:
        raise ValueError("하한 제약이 너무 높아 비중 합계 1을 만들 수 없습니다.")
    if config.upper_bound * n_assets < 1.0:
        raise ValueError("상한 제약이 너무 낮아 비중 합계 1을 만들 수 없습니다.")

    cov = estimate_covariance(return_matrix, config.covariance_shrinkage)
    x0 = np.repeat(1.0 / n_assets, n_assets)
    bounds = tuple((config.lower_bound, config.upper_bound) for _ in range(n_assets))

    if minimize is None:
        if np.all((x0 >= config.lower_bound) & (x0 <= config.upper_bound)):
            return pd.Series(x0, index=return_matrix.columns, name="selected_weight")
        raise RuntimeError("scipy가 없어 최소분산 최적화를 실행할 수 없습니다.")

    result = minimize(
        fun=lambda weights: float(weights.T @ cov @ weights),
        x0=x0,
        method="SLSQP",
        bounds=bounds,
        constraints=({"type": "eq", "fun": lambda weights: float(weights.sum() - 1.0)},),
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    if not result.success:
        raise RuntimeError(f"최소분산 최적화가 수렴하지 않았습니다: {result.message}")

    # 수치 오차로 합계가 1에서 아주 조금 벗어날 수 있어 마지막에 다시 정규화한다.
    weights = np.clip(result.x, config.lower_bound, config.upper_bound)
    weights = weights / weights.sum()
    return pd.Series(weights, index=return_matrix.columns, name="selected_weight")


def build_portfolio_table(
    selected: pd.DataFrame,
    return_matrix: pd.DataFrame,
    config: PortfolioConfig,
) -> pd.DataFrame:
    """선택 종목, 최적 비중, 리스크 기여도를 하나의 표로 결합한다."""

    weights = minimum_variance_weights(return_matrix, config)
    cov = estimate_covariance(return_matrix.loc[:, weights.index], config.covariance_shrinkage)
    weight_vector = weights.to_numpy(dtype=float)
    portfolio_variance = float(weight_vector.T @ cov @ weight_vector)
    marginal_risk = cov @ weight_vector
    risk_contribution = weight_vector * marginal_risk
    risk_contribution_pct = risk_contribution / portfolio_variance if portfolio_variance > 0 else np.zeros_like(weight_vector)

    table = selected.set_index("asset").loc[weights.index].reset_index()
    table["selected_weight"] = weights.to_numpy()
    table["weight_pct"] = table["selected_weight"] * 100.0
    table["risk_contribution_pct"] = risk_contribution_pct
    table["portfolio_monthly_volatility"] = portfolio_variance**0.5
    table["portfolio_annualized_volatility"] = (portfolio_variance * 12.0) ** 0.5

    ordered = [
        "asset",
        "name",
        "sector",
        "final_rank",
        "quality_score",
        "value_score",
        "momentum_score",
        "final_score",
        "selected_weight",
        "weight_pct",
        "risk_contribution_pct",
        "portfolio_monthly_volatility",
        "portfolio_annualized_volatility",
        "market_cap",
    ]
    return table.loc[:, ordered].sort_values("selected_weight", ascending=False).reset_index(drop=True)


def build_comparison_summary() -> pd.DataFrame:
    """제출본과 답안본의 구현 차이를 연구 규칙으로 정리한다."""

    rows = [
        {
            "check_point": "모멘텀 계산",
            "submitted_source": "6/12개월 함수가 `pct_change`의 fill limit만 바꾸어 월간 수익률에 가까운 값을 만들었다.",
            "answer_source": "최근 12개월 월간 수익률을 누적 곱하고, 6개월 모멘텀은 그중 최근 6개월만 누적했다.",
            "repo_decision": "`ret_m01`~`ret_m12`에서 `mom12`, `mom6`을 누적수익률로 다시 계산한다.",
        },
        {
            "check_point": "밸류 부호",
            "submitted_source": "E/P, B/P를 높을수록 좋은 값으로 쓰려 했지만 rank z-score 방향 관리가 불안정했다.",
            "answer_source": "PER, PBR은 낮을수록 좋으므로 `-PER`, `-PBR`로 부호를 명시했다.",
            "repo_decision": "양수 PER/PBR만 사용하고 `neg_per`, `neg_pbr`을 표준화한다.",
        },
        {
            "check_point": "정규화 순서",
            "submitted_source": "특성 rank z-score 후 MinMaxScaler를 적용해 점수 해석이 0~1 스케일에 묶였다.",
            "answer_source": "특성 z-score, 카테고리 z-score, 최종 z-score를 순서대로 적용했다.",
            "repo_decision": "모든 횡단면 표준화는 평균 0, 표준편차 1의 z-score로 통일한다.",
        },
        {
            "check_point": "후보 선택",
            "submitted_source": "상위 30개를 고른 뒤 수익률 결측 종목을 제거하고 추가 후보를 일부 보충했다.",
            "answer_source": "결측이 없는 공통 유니버스에서 최종 점수 상위 30개를 선택했다.",
            "repo_decision": "수익률 이력이 있는 종목만 남긴 뒤 상위 후보를 선택한다.",
        },
        {
            "check_point": "최소분산 포트폴리오",
            "submitted_source": "cvxpy와 PSD 보정으로 `1%<=w<=5%`, `sum(w)=1` 제약을 풀었다.",
            "answer_source": "scipy SLSQP로 같은 하한/상한/합계 제약의 최소변동성 문제를 풀었다.",
            "repo_decision": "scipy SLSQP를 기본으로 쓰고, 공분산 행렬은 대각 shrinkage와 고유값 보정으로 안정화한다.",
        },
    ]
    return pd.DataFrame(rows)


def build_research_tables(
    path: Path = DATA_PATH,
    config: PortfolioConfig = PortfolioConfig(),
) -> dict[str, pd.DataFrame]:
    """입력 패널에서 연구 산출물 4종을 생성한다."""

    panel = load_factor_panel(path)
    characteristics = compute_factor_characteristics(panel)
    scores = compute_factor_scores(characteristics)
    selected = select_candidates(scores, panel, config)
    return_matrix = make_return_matrix(panel, selected["asset"].tolist())
    portfolio = build_portfolio_table(selected, return_matrix, config)
    comparison = build_comparison_summary()

    return {
        "factor_characteristics": characteristics,
        "factor_scores": scores,
        "portfolio_weights": portfolio,
        "comparison_summary": comparison,
    }


def run_baseline() -> list[dict[str, object]]:
    """기존 노트북/README 호환을 위해 최종 포트폴리오 표를 dict 목록으로 반환한다."""

    return build_research_tables()["portfolio_weights"].to_dict(orient="records")


def write_results(tables: dict[str, pd.DataFrame] | None = None) -> dict[str, Path]:
    """산출물 테이블을 `outputs/tables/`에 저장한다."""

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    research_tables = build_research_tables() if tables is None else tables
    written: dict[str, Path] = {}
    for name, table in research_tables.items():
        path = OUTPUT_PATHS[name]
        table.to_csv(path, index=False, encoding="utf-8")
        written[name] = path

    baseline_path = OUTPUT_PATHS["baseline_results"]
    research_tables["portfolio_weights"].to_csv(baseline_path, index=False, encoding="utf-8")
    written["baseline_results"] = baseline_path
    return written


def main() -> None:
    """명령행 실행 시 전체 연구 테이블을 재생성한다."""

    written = write_results()
    for name, path in written.items():
        print(f"wrote {name}: {path}")


if __name__ == "__main__":
    main()
