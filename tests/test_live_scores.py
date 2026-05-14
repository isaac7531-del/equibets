import unittest
from datetime import date

from equibets.live_scores import current_live_events, load_live_score_snapshot, top_live_leaders


class LiveScoreSnapshotTests(unittest.TestCase):
    def test_loads_current_event_score_snapshot(self):
        snapshot = load_live_score_snapshot()

        self.assertEqual(snapshot.version, 1)
        self.assertEqual(snapshot.collected_at.year, 2026)
        self.assertGreaterEqual(len(snapshot.events), 4)
        self.assertGreater(snapshot.leader_count, 0)

    def test_current_live_events_include_active_events(self):
        snapshot = load_live_score_snapshot()

        event_ids = [event.id for event in current_live_events(snapshot, on_date=date(2026, 5, 14))]

        self.assertIn("fei-nations-cup-marbach-2026", event_ids)

    def test_top_live_leaders_are_sorted_by_lowest_score(self):
        snapshot = load_live_score_snapshot()

        leaders = top_live_leaders(snapshot, limit=3)

        self.assertEqual([leader.score for leader in leaders], sorted(leader.score for leader in leaders))
        self.assertEqual(leaders[0].horse_name, "Weekapaug Groove")


if __name__ == "__main__":
    unittest.main()
