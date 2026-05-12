# 발표 초안

## 1. 문제 정의

복수 팩터를 같은 척도로 표준화하면 어떤 종목이 안정적으로 상위권에 남는가?

이 프로젝트는 기말 시험 제출본과 답안본의 차이를 출발점으로, 멀티팩터 포트폴리오를 연구 코드와 설명 문서로 재구성한다.

## 2. 소스 비교에서 얻은 교훈

- 6개월/12개월 모멘텀은 월간 수익률 하나가 아니라 기간 누적수익률이다.
- PER/PBR은 낮을수록 좋은 밸류 특성이므로 부호를 명시적으로 바꿔야 한다.
- rank, MinMax, z-score를 섞기보다 특성, 카테고리, 최종 점수 모두 z-score로 통일하는 편이 검증 가능하다.
- 상위 후보 선택과 최소분산 포트폴리오 비중 산출은 별도 단계로 분리해야 한다.

## 3. 데이터와 가정

- 입력: `data/sample/factor_input_panel.csv`
- 데이터 성격: 원본 시험 데이터를 복사하지 않은 합성 패널
- 표본: 36개 종목, 최근 12개월 월간 수익률
- 후보: final score 상위 30개
- 비중 제약: 종목당 1% 이상 5% 이하
- 비용 가정: 현재 baseline에는 거래비용과 세금을 반영하지 않음

## 4. 방법

1. GP, OP, `-PER`, `-PBR`, MOM12, MOM6를 만든다.
2. 개별 특성을 z-score로 표준화한다.
3. quality, value, momentum 카테고리 점수를 계산하고 다시 z-score화한다.
4. final score 상위 30개를 선택한다.
5. 공분산 shrinkage와 PSD 보정 후 최소분산 포트폴리오를 계산한다.

## 5. 현재 산출물

- 실행 스크립트: `python -m src.run_baseline`
- 특성값: `outputs/tables/factor_characteristics.csv`
- 점수와 순위: `outputs/tables/factor_scores.csv`
- 포트폴리오 비중: `outputs/tables/portfolio_weights.csv`
- 비교 요약: `outputs/tables/comparison_summary.csv`

## 6. 해석상 주의

현재 결과는 합성 데이터 기반이므로 투자 성과가 아니다. 실제 데이터 연구로 확장하려면 재무제표 공시 지연, 상장폐지 처리, 거래비용, 리밸런싱 시점, 회전율, 섹터 쏠림을 별도로 점검해야 한다.
