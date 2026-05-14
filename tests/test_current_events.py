import unittest
from pathlib import Path

from equibets.current_events import (
    current_event_results_as_eventing_results,
    live_leaderboard,
    load_current_event_results,
    search_current_event_results,
)


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "current_events.json"


class CurrentEventResultTests(unittest.TestCase):
    def test_loads_current_event_feed_and_scores_live_rows(self):
        results = load_current_event_results(DATA_FILE)
        mara = next(result for result in results if result.horse_name == "Copper Chance")

        self.assertEqual(len(results), 4)
        self.assertEqual(mara.live_score, 38.6)
        self.assertEqual(mara.completed_phase_count, 4)

    def test_searches_current_event_results(self):
        results = load_current_event_results(DATA_FILE)
        matches = search_current_event_results(results, "cci3-s")

        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].event_name, "Chatsworth International")

    def test_live_leaderboard_prefers_complete_scores(self):
        results = load_current_event_results(DATA_FILE)
        leaderboard = live_leaderboard(results)

        self.assertEqual(leaderboard[0].horse_name, "Orchard Lane")
        self.assertEqual(leaderboard[-1].horse_name, "Maple Run")

    def test_normalizes_current_event_rows_to_eventing_results(self):
        results = load_current_event_results(DATA_FILE)
        eventing_results = current_event_results_as_eventing_results(results)

        self.assertEqual(eventing_results[0].source_id, "data_fei")
        self.assertEqual(eventing_results[0].finishing_score, results[0].live_score)

    def test_can_require_final_rows_before_normalization(self):
        results = load_current_event_results(DATA_FILE)
        partial = next(result for result in results if result.horse_name == "Windfall Bay")

        with self.assertRaises(ValueError):
            partial.to_eventing_result(require_final=True)


if __name__ == "__main__":
    unittest.main()
