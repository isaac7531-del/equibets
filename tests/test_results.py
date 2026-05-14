import unittest

from equibets.results import (
    EventingResult,
    consolidate_results,
    live_leaderboard,
    load_current_event_results,
    predict_finishing_score,
)


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Spring Horse Trials",
        "event_date": "2026-03-01",
        "level": "CCI2",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-03-08T00:00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class ResultConsolidationTests(unittest.TestCase):
    def test_finishing_score_adds_all_phases(self):
        score = result().finishing_score

        self.assertEqual(score, 35.8)

    def test_official_source_replaces_duplicate_user_score(self):
        user_score = result(
            source_id="user_submission",
            source_record_id="user-1",
            source_priority=100,
            dressage_score=31.0,
            collected_at="2026-03-07T00:00:00",
            is_user_entered=True,
        )
        official_score = result()

        consolidated = consolidate_results([user_score, official_score])

        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated[0].source_id, "data_fei")
        self.assertEqual(consolidated[0].finishing_score, 35.8)

    def test_prediction_uses_recent_consolidated_scores(self):
        results = [
            result(source_record_id="fei-1", event_date="2026-01-01", dressage_score=32.0),
            result(source_record_id="fei-2", event_date="2026-02-01", dressage_score=30.0),
            result(
                source_id="user_submission",
                source_record_id="user-3",
                source_priority=100,
                event_name="Local Combined Training",
                event_date="2026-03-01",
                dressage_score=29.0,
                show_jumping_penalties=0,
                collected_at="2026-03-04T00:00:00",
                is_user_entered=True,
            ),
        ]

        prediction = predict_finishing_score(results, "Alex Rider", "Pocket Rocket")

        self.assertEqual(prediction.recent_result_count, 3)
        self.assertEqual(prediction.confidence, "medium")
        self.assertEqual(prediction.source_ids, ("data_fei", "user_submission"))
        self.assertEqual(prediction.likely_finishing_score, 33.4)

    def test_current_event_snapshot_loads_live_scores(self):
        results = load_current_event_results()
        leaderboard = live_leaderboard(limit=3)

        self.assertGreaterEqual(len(results), 15)
        self.assertEqual(leaderboard[0].horse_name, "Weekapaug Groove")
        self.assertEqual(leaderboard[0].finishing_score, 18.5)
        self.assertEqual(leaderboard[1].horse_name, "Lost at Sea")
        self.assertEqual(leaderboard[2].source_id, "badminton_horse_trials")


if __name__ == "__main__":
    unittest.main()
