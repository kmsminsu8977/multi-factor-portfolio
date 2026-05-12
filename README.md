# Multi-Factor Portfolio

퀀트 및 팩터투자전략 기말 시험의 제출본과 답안본을 비교해, 멀티팩터 포트폴리오 연구 노트와 재현 가능한 코드베이스로 재구성한 저장소입니다.

**핵심 연구 질문**

> 복수 팩터를 같은 척도로 표준화하면 어떤 종목이 안정적으로 상위권에 남는가?

## 구현 요약

이 저장소의 baseline은 답안본의 흐름을 기준으로 삼습니다.

1. GP, OP, PER, PBR, 12개월 모멘텀, 6개월 모멘텀을 계산한다.
2. PER/PBR은 낮을수록 좋은 밸류 특성이므로 `-PER`, `-PBR`로 부호를 바꾼다.
3. 개별 특성을 z-score로 표준화한다.
4. `quality`, `value`, `momentum` 카테고리 점수를 만들고 다시 z-score로 표준화한다.
5. 최종 점수 상위 30개 후보를 선택한다.
6. `1% <= w_i <= 5%`, `sum(w)=1` 제약의 최소분산 포트폴리오를 계산한다.

## 빠른 시작

```bash
pip install -r requirements.txt
python -m src.run_baseline
```

## 주요 산출물

- `outputs/tables/factor_characteristics.csv`: 여섯 개 기업 특성값
- `outputs/tables/factor_scores.csv`: 특성 z-score, 카테고리 점수, 최종 순위
- `outputs/tables/portfolio_weights.csv`: 최소분산 포트폴리오 비중과 리스크 기여도
- `outputs/tables/comparison_summary.csv`: 제출본과 답안본의 차이 및 저장소 반영 기준
- `outputs/tables/baseline_results.csv`: 기존 실행 경로 호환용 포트폴리오 비중표

## 저장소 구조

```text
multi-factor-portfolio/
├── data/sample/                 # 합성 factor/return 입력 패널
├── docs/                        # 방법론과 제출본/답안본 비교
├── notebooks/                   # baseline 실행 흐름 노트북
├── outputs/tables/              # 재현 가능한 결과 CSV
├── presentation/                # 발표/보고서 초안
├── references/                  # 재작성 개념 노트
└── src/                         # 멀티팩터 계산 로직
```

## 참고 범위

- 로컬: `KAIST-DFMBA/Quant-and-Factor-Investment-Strategies/Final/Submit/Multi_Factor_Portfolio_20239047_김민수.ipynb`
- 로컬: `KAIST-DFMBA/Quant-and-Factor-Investment-Strategies/Final/Solution/퀀트 및 팩터투자전략 기말고사.ipynb`
- Notion: 퀀트 및 팩터투자전략, 멀티팩터, 팩터 모델과 CAPM, 퀄리티 팩터, 저위험 노트

원본 자료의 코드와 설명은 그대로 복사하지 않고, 현재 프로젝트의 연구 질문에 맞게 독립적인 합성 데이터와 재현 가능한 함수로 재구성했습니다.
