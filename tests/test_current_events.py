import unittest

from equibets.current_events import (
    CurrentEventQuery,
    build_current_event_searches,
    results_from_payload,
)


class CurrentEventTests(unittest.TestCase):
    def test_build_searches_prioritizes_fei_for_current_results(self):
        searches = build_current_event_searches(
            CurrentEventQuery(
                event_name="Badminton Horse Trials",
                rider_name="Avery Stone",
                horse_name="Juniper",
                region="uk",
                year=2026,
            )
        )

        self.assertEqual(searches[0].source_id, "data_fei")
        self.assertIn("Badminton Horse Trials", searches[0].query)
        self.assertIn("site:data.fei.org", searches[0].query)
        self.assertIn("british_eventing", [search.source_id for search in searches])

    def test_results_from_payload_normalizes_live_records(self):
        results = results_from_payload(
            {
                "results": [
                    {
                        "source_id": "data_fei",
                        "source_record_id": "fei-1",
                        "source_priority": 0,
                        "rider_name": "Avery Stone",
                        "horse_name": "Juniper",
                        "event_name": "Spring International",
                        "event_date": "2026-05-16",
                        "level": "CCI3",
                        "country": "GBR",
                        "dressage_score": 28.4,
                        "show_jumping_penalties": 4,
                        "cross_country_jump_penalties": 0,
                        "cross_country_time_penalties": 1.2,
                        "collected_at": "2026-05-16T04:00:00",
                    }
                ]
            }
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].finishing_score, 33.6)
        self.assertEqual(results[0].combination_key, "avery-stone::juniper")


if __name__ == "__main__":
    unittest.main()
