import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from equibets.live_scoring import (
    LiveEventResult,
    build_live_leaderboard,
    new_results_since,
    pull_live_scoring_snapshot,
    search_current_event_results,
)


def live_result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-current-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Current Spring International",
        "event_date": "2026-05-15",
        "level": "CCI3",
        "division": "CCI3 Section A",
        "country": "GBR",
        "dressage_score": 28.4,
        "show_jumping_penalties": 0,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.2,
        "collected_at": "2026-05-15T01:00:00+00:00",
        "status": "cross_country",
        "is_user_entered": False,
    }
    values.update(overrides)
    return LiveEventResult.from_mapping(values)


class LiveScoringTests(unittest.TestCase):
    def test_searches_current_events_by_combination_or_event(self):
        results = [
            live_result(),
            live_result(
                source_record_id="fei-current-2",
                rider_name="Taylor Lane",
                horse_name="Harbor Master",
                event_name="Coastal Horse Trials",
            ),
        ]

        horse_matches = search_current_event_results(results, "pocket")
        event_matches = search_current_event_results(results, event_name="coastal")

        self.assertEqual([item.result.horse_name for item in horse_matches], ["Pocket Rocket"])
        self.assertEqual([item.result.event_name for item in event_matches], ["Coastal Horse Trials"])

    def test_leaderboard_deduplicates_and_ranks_lowest_live_score(self):
        user_duplicate = live_result(
            source_id="user_submission",
            source_record_id="user-current-1",
            source_priority=100,
            dressage_score=31.4,
            collected_at="2026-05-15T00:45:00+00:00",
            is_user_entered=True,
        )
        official_result = live_result()
        leader = live_result(
            source_record_id="fei-current-3",
            rider_name="Morgan Reed",
            horse_name="Quick Step",
            dressage_score=24.8,
            cross_country_time_penalties=0,
            status="final",
        )

        leaderboard = build_live_leaderboard([user_duplicate, official_result, leader])

        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0].rank, 1)
        self.assertEqual(leaderboard[0].live_result.result.horse_name, "Quick Step")
        self.assertEqual(leaderboard[1].live_result.result.source_id, "data_fei")

    def test_new_results_since_returns_only_fresh_records(self):
        stale = live_result(collected_at="2026-05-15T00:55:00+00:00")
        fresh = live_result(
            source_record_id="fei-current-4",
            horse_name="Fresh Update",
            collected_at="2026-05-15T01:05:00+00:00",
        )

        results = new_results_since(
            [stale, fresh],
            datetime.fromisoformat("2026-05-15T01:00:00+00:00"),
        )

        self.assertEqual([item.result.horse_name for item in results], ["Fresh Update"])

    def test_pull_snapshot_filters_and_keeps_feed_timestamp(self):
        payload = {
            "collected_at": "2026-05-15T01:10:00+00:00",
            "results": [
                {
                    "source_id": "data_fei",
                    "source_record_id": "fei-current-1",
                    "source_priority": 0,
                    "rider_name": "Alex Rider",
                    "horse_name": "Pocket Rocket",
                    "event_name": "Current Spring International",
                    "event_date": "2026-05-15",
                    "level": "CCI3",
                    "country": "GBR",
                    "dressage_score": 28.4,
                    "show_jumping_penalties": 0,
                    "cross_country_jump_penalties": 0,
                    "cross_country_time_penalties": 1.2,
                    "collected_at": "2026-05-15T01:00:00+00:00",
                    "status": "cross_country",
                    "is_user_entered": False,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "current_event_results.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            snapshot = pull_live_scoring_snapshot(path, country="GBR")

        self.assertEqual(snapshot.collected_at.isoformat(), "2026-05-15T01:10:00+00:00")
        self.assertEqual(snapshot.source_ids, ("data_fei",))
        self.assertEqual(snapshot.entries[0].live_result.finishing_score, 29.6)


if __name__ == "__main__":
    unittest.main()
