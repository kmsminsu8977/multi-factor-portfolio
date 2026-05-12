# Sample Data

`factor_input_panel.csv`는 시험 원천 엑셀을 그대로 복사하지 않고, 답안 산식의 핵심 흐름을 검증할 수 있도록 만든 합성 패널입니다. 한 행은 한 종목이며, 재무 특성값과 최근 12개월 월간 수익률을 함께 담습니다.

## Columns

- `asset`, `name`, `sector`: 종목 식별자와 설명용 메타데이터
- `market_cap`: 시가총액 성격의 규모 변수입니다. 현재 baseline 최적화에는 직접 쓰지 않고 결과 해석용으로 남깁니다.
- `gp`: 매출총이익/총자산에 해당하는 profitability 특성입니다.
- `op`: EBIT/총자본에 해당하는 operating profitability 특성입니다.
- `per`, `pbr`: 낮을수록 좋은 밸류 특성이므로 코드에서 `-PER`, `-PBR`로 부호를 바꿉니다.
- `ret_m01`~`ret_m12`: 오래된 월부터 최근 월까지의 월간 단순수익률입니다. `mom12`, `mom6`은 이 값으로 재계산합니다.

## Usage

```bash
python -m src.run_baseline
```
