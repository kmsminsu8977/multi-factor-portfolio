"""멀티팩터 baseline의 핵심 금융공학 가정을 점검하는 테스트."""

from __future__ import annotations

import unittest

import pandas as pd

from src.multi_factor_baseline import build_research_tables, compute_factor_characteristics, load_factor_panel


class MultiFactorBaselineTest(unittest.TestCase):
    def test_value_sign_is_reversed(self) -> None:
        """PER/PBR은 낮을수록 좋은 밸류 특성이므로 부호가 뒤집혀야 한다."""

        panel = load_factor_panel()
        characteristics = compute_factor_characteristics(panel)
        joined = characteristics.set_index("asset").join(panel.set_index("asset")[["per", "pbr"]])

        pd.testing.assert_series_equal(joined["neg_per"], -joined["per"], check_names=False)
        pd.testing.assert_series_equal(joined["neg_pbr"], -joined["pbr"], check_names=False)

    def test_portfolio_constraints_are_respected(self) -> None:
        """상위 30개 후보의 최소분산 비중이 시험 답안의 제약을 만족하는지 확인한다."""

        portfolio = build_research_tables()["portfolio_weights"]

        self.assertEqual(len(portfolio), 30)
        self.assertAlmostEqual(float(portfolio["selected_weight"].sum()), 1.0, places=10)
        self.assertGreaterEqual(float(portfolio["selected_weight"].min()), 0.01 - 1e-10)
        self.assertLessEqual(float(portfolio["selected_weight"].max()), 0.05 + 1e-10)
        self.assertLessEqual(int(portfolio["final_rank"].max()), 30)


if __name__ == "__main__":
    unittest.main()
