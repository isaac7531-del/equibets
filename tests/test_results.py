import unittest

from equibets.results import (
    EventingResult,
    consolidate_results,
    list_riders,
    predict_finishing_score,
    search_results,
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

    def test_search_results_matches_rider_horse_event_level_and_country(self):
        results = [
            result(source_record_id="fei-1", rider_name="Ros Canter", horse_name="Lordships Graffalo", event_name="Badminton Horse Trials", level="CCI5*-L", country="GBR"),
            result(source_record_id="fei-2", rider_name="Laura Collett", horse_name="London 52", event_name="Luhmuhlen Horse Trials", level="CCI5*-L", country="GBR"),
            result(source_record_id="fei-3", rider_name="Boyd Martin", horse_name="Fedarman B", event_name="Maryland 5 Star", level="CCI5*-L", country="USA"),
        ]

        self.assertEqual([item.rider_name for item in search_results(results, "badminton")], ["Ros Canter"])
        self.assertEqual([item.rider_name for item in search_results(results, "London")], ["Laura Collett"])
        self.assertEqual([item.rider_name for item in search_results(results, "USA")], ["Boyd Martin"])

    def test_list_riders_summarizes_searchable_combinations(self):
        results = [
            result(source_record_id="fei-1", rider_name="Ros Canter", horse_name="Lordships Graffalo", event_date="2024-05-05", dressage_score=26.0),
            result(source_record_id="fei-2", rider_name="Ros Canter", horse_name="Lordships Graffalo", event_date="2023-08-12", dressage_score=21.3),
            result(source_record_id="fei-3", rider_name="Laura Collett", horse_name="London 52", event_date="2023-06-18", dressage_score=20.3),
        ]

        summaries = list_riders(results, query="Ros")

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].rider_name, "Ros Canter")
        self.assertEqual(summaries[0].result_count, 2)
        self.assertEqual(summaries[0].best_finishing_score, 26.9)


if __name__ == "__main__":
    unittest.main()
