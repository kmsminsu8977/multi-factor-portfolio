# Output Tables

아래 파일은 `python -m src.run_baseline` 실행으로 재생성됩니다.

- `factor_characteristics.csv`: GP, OP, `-PER`, `-PBR`, 12개월/6개월 모멘텀 특성값
- `factor_scores.csv`: 특성 z-score, 카테고리 z-score, 최종 점수와 순위
- `portfolio_weights.csv`: 상위 후보의 최소분산 포트폴리오 비중과 리스크 기여도
- `comparison_summary.csv`: 제출본과 답안본의 구현 차이 및 이 저장소의 반영 기준
- `baseline_results.csv`: 기존 실행 경로와의 호환을 위한 `portfolio_weights.csv` 사본

현재 결과는 합성 입력에 대한 구조 검증용 산출물입니다. 통계적 유의성, 실제 투자 가능성, 미래 성과를 주장하지 않습니다.
