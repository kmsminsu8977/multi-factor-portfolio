# Multi-Factor Portfolio

멀티팩터 포트폴리오 프로젝트의 기본 연구 구조와 재현 가능한 baseline 산출물을 담은 저장소입니다.

**핵심 연구 질문**

> 복수 팩터를 같은 척도로 표준화하면 어떤 종목이 안정적으로 상위권에 남는가?

## 작업 기준 문서

- `AGENTS.md`: 저장소 작업 기준과 품질 기준
- `SOURCE.md`: KAIST-DFMBA 참고 경로와 프로젝트별 컨텐츠 재구성 기준

## 저장소 구조

```text
multi-factor-portfolio/
├── src/                         # baseline 계산 로직과 실행 엔트리포인트
├── data/sample/                 # 합성 샘플 입력 데이터
├── docs/                        # 방법론과 해석 기준
├── notebooks/                   # 실행 흐름을 보여주는 최소 노트북
├── outputs/tables/              # 재현 가능한 결과 CSV
├── presentation/                # 발표/보고서 초안
└── references/                  # 재작성 개념 노트와 참고문헌 메모
```

## 빠른 시작

```bash
python -m src.run_baseline
```

실행 결과는 `outputs/tables/baseline_results.csv`에 저장됩니다.

## 구현 범위

- 팩터별 원점수를 z-score로 바꾸고 동일 가중 composite score를 계산한다.
- 상위 종목은 composite score에 비례해 배분하되 concentration을 확인한다.
- 종목명과 점수는 팩터 결합 절차를 설명하는 합성 예시다.

## 주요 파일

- `src/multi_factor_baseline.py`: 가치, 모멘텀, 퀄리티, 저변동성 점수를 합성해 포트폴리오 후보를 선별한다.
- `data/sample/factor_scores.csv`: baseline 실행용 합성 입력값
- `docs/methodology.md`: 계산 절차, 입력/출력 정의, 해석상 주의점
- `outputs/tables/baseline_results.csv`: 현재 baseline 산출물

## 다음 확장 방향

- 실제 공개 데이터 또는 별도 수집 데이터 연결
- notebook 기반 탐색 분석 추가
- 차트와 표를 포함한 최종 보고서 작성
- 모델 검증, 민감도 분석, 비용/리스크 가정 보강
