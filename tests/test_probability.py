import unittest

from equibets.probability import (
    FieldEntry,
    ProbabilityPriors,
    estimate_phase_model,
    simulate_market_probabilities,
)
from equibets.results import EventingResult


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Mia Hughes",
        "horse_name": "Atlas Bay",
        "event_name": "Spring International",
        "event_date": "2026-03-01",
        "level": "CCI3-S",
        "country": "GBR",
        "dressage_score": 28.0,
        "show_jumping_penalties": 0,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.0,
        "collected_at": "2026-03-05T00:00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class ProbabilityModelTests(unittest.TestCase):
    def test_phase_model_uses_recent_weighted_scores(self):
        results = [
            result(source_record_id="fei-1", event_date="2026-01-01", dressage_score=32.0, show_jumping_penalties=4),
            result(source_record_id="fei-2", event_date="2026-02-01", dressage_score=30.0, show_jumping_penalties=0),
            result(source_record_id="fei-3", event_date="2026-03-01", dressage_score=28.0, show_jumping_penalties=0),
        ]

        model = estimate_phase_model(results, "Mia Hughes", "Atlas Bay")

        self.assertEqual(model.expected_dressage_score, 29.3)
        self.assertEqual(model.expected_show_jumping_penalties, 0.7)
        self.assertEqual(model.clear_show_jumping_probability, 0.833)
        self.assertEqual(model.clear_cross_country_probability, 1.0)
        self.assertEqual(model.expected_finishing_score, 31.0)
        self.assertEqual(model.confidence, "medium")

    def test_simulation_orders_stronger_combination_ahead_of_field(self):
        results = [
            result(source_record_id="atlas-1", event_date="2026-01-01", dressage_score=28.0),
            result(source_record_id="atlas-2", event_date="2026-02-01", dressage_score=27.0),
            result(source_record_id="atlas-3", event_date="2026-03-01", dressage_score=26.0),
            result(
                source_record_id="north-1",
                rider_name="Theo Carter",
                horse_name="Northwind",
                event_date="2026-01-01",
                dressage_score=34.0,
                show_jumping_penalties=4,
                cross_country_time_penalties=3.0,
            ),
            result(
                source_record_id="north-2",
                rider_name="Theo Carter",
                horse_name="Northwind",
                event_date="2026-02-01",
                dressage_score=35.0,
                show_jumping_penalties=4,
                cross_country_time_penalties=4.0,
            ),
            result(
                source_record_id="river-1",
                rider_name="Sophie Bell",
                horse_name="Riverglass",
                event_date="2026-01-01",
                dressage_score=31.0,
                cross_country_jump_penalties=20,
                cross_country_time_penalties=2.0,
            ),
            result(
                source_record_id="river-2",
                rider_name="Sophie Bell",
                horse_name="Riverglass",
                event_date="2026-02-01",
                dressage_score=30.0,
                cross_country_jump_penalties=20,
                cross_country_time_penalties=2.0,
            ),
        ]

        markets = simulate_market_probabilities(
            results,
            [
                FieldEntry("Mia Hughes", "Atlas Bay"),
                FieldEntry("Theo Carter", "Northwind"),
                FieldEntry("Sophie Bell", "Riverglass"),
            ],
            iterations=1200,
            seed=7,
            priors=ProbabilityPriors(
                elimination_probability=0.0,
                retirement_probability=0.0,
                withdrawal_probability=0.0,
            ),
        )

        atlas, northwind, riverglass = markets
        self.assertGreater(atlas.win_probability, northwind.win_probability)
        self.assertGreater(atlas.win_probability, riverglass.win_probability)
        self.assertGreater(atlas.best_dressage_probability, northwind.best_dressage_probability)
        self.assertEqual(atlas.top_3_probability, 1.0)
        self.assertEqual(northwind.top_3_probability, 1.0)
        self.assertEqual(riverglass.top_3_probability, 1.0)

    def test_simulation_requires_results_for_each_entry(self):
        with self.assertRaisesRegex(ValueError, "No results found"):
            simulate_market_probabilities(
                [result()],
                [FieldEntry("Unknown Rider", "Unknown Horse")],
                iterations=10,
            )


if __name__ == "__main__":
    unittest.main()
