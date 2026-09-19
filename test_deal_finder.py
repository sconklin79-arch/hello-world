import unittest

from deal_finder import (
    analyze_property,
    estimate_acquisition_cost,
    estimate_confidence,
    estimate_rehab_cost,
    run_funnel,
    score_property,
)


def make_property(**overrides):
    base = {
        "asking_price": 214900,
        "stabilized_value": 310000,
        "sqft": 1600,
        "rehab_cost_per_sqft": 25,
        "carrying_cost_per_month": 1500,
        "carrying_cost_months": 4,
        "days_on_market": 93,
        "price_reductions": 4,
        "last_sale_year": 2007,
        "comparable_sale_count": 6,
        "comparable_value_spread_pct": 0.08,
    }
    base.update(overrides)
    return base


class DealFinderTest(unittest.TestCase):
    def test_estimate_rehab_cost_from_estimate(self):
        self.assertEqual(estimate_rehab_cost({"rehab_estimate": 38000}), 38000)

    def test_estimate_rehab_cost_from_sqft(self):
        cost = estimate_rehab_cost({"sqft": 1600, "rehab_cost_per_sqft": 25})
        self.assertEqual(cost, 40000)

    def test_estimate_rehab_cost_missing_inputs(self):
        with self.assertRaises(ValueError):
            estimate_rehab_cost({})

    def test_estimate_acquisition_cost(self):
        cost = estimate_acquisition_cost(
            {"asking_price": 100000, "closing_cost_pct": 0.02,
             "carrying_cost_per_month": 1000, "carrying_cost_months": 3}
        )
        self.assertEqual(cost, 100000 + 2000 + 3000)

    def test_estimate_acquisition_cost_missing_price(self):
        with self.assertRaises(ValueError):
            estimate_acquisition_cost({})

    def test_estimate_confidence_levels(self):
        self.assertEqual(
            estimate_confidence(
                {"comparable_sale_count": 6, "comparable_value_spread_pct": 0.05}
            ),
            "high",
        )
        self.assertEqual(estimate_confidence({"comparable_sale_count": 2}), "medium")
        self.assertEqual(estimate_confidence({}), "low")

    def test_analyze_property_computes_spread_and_reasons(self):
        analysis = analyze_property(make_property())
        self.assertEqual(analysis["rehab_cost"], 40000)
        self.assertAlmostEqual(
            analysis["total_cost"], analysis["acquisition_cost"] + 40000
        )
        self.assertAlmostEqual(
            analysis["spread"], 310000 - analysis["total_cost"]
        )
        self.assertEqual(analysis["confidence"], "high")
        self.assertIn("4 price reductions", analysis["reasons"])
        self.assertIn("93 days on market", analysis["reasons"])

    def test_analyze_property_requires_stabilized_value(self):
        with self.assertRaises(ValueError):
            analyze_property({"asking_price": 100000})

    def test_score_property_weights_by_confidence(self):
        strong = make_property()
        weak = make_property(comparable_sale_count=0, comparable_value_spread_pct=None)
        self.assertGreater(score_property(strong), score_property(weak))

    def test_run_funnel_narrows_and_sorts(self):
        properties = [make_property(asking_price=214900 + i * 1000) for i in range(10)]
        stages = run_funnel(properties, stage_sizes=(10, 5, 2))
        self.assertEqual([len(stage) for stage in stages], [10, 5, 2])
        scores = [score_property(p) for p in stages[-1]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_run_funnel_requires_properties(self):
        with self.assertRaises(ValueError):
            run_funnel([])


if __name__ == "__main__":
    unittest.main()
