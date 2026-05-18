import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.live_scoring import (
    build_live_scoring_feed,
    current_event_window,
    write_live_scoring_feed,
)
from equibets.results import EventingResult


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Spring International",
        "event_date": "2026-05-18",
        "level": "CCI2",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-05-18T12:00:00+00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class LiveScoringTests(unittest.TestCase):
    def test_current_event_window_covers_multiday_events(self):
        start_date, end_date = current_event_window(date(2026, 5, 18))

        self.assertEqual(start_date, date(2026, 5, 14))
        self.assertEqual(end_date, date(2026, 5, 19))

    def test_live_feed_groups_current_results_and_ranks_scores(self):
        feed = build_live_scoring_feed(
            [
                result(source_record_id="fei-1", rider_name="Alex Rider", horse_name="Pocket Rocket", dressage_score=30.2),
                result(
                    source_record_id="fei-2",
                    rider_name="Blair Smith",
                    horse_name="Juniper",
                    dressage_score=29.0,
                    show_jumping_penalties=0,
                    cross_country_time_penalties=0,
                ),
                result(
                    source_id="user_submission",
                    source_record_id="user-1",
                    source_priority=100,
                    dressage_score=31.0,
                    collected_at="2026-05-18T11:00:00+00:00",
                    is_user_entered=True,
                ),
                result(
                    source_record_id="fei-old",
                    event_name="Winter Horse Trials",
                    event_date="2026-01-04",
                ),
            ],
            start_date=date(2026, 5, 14),
            end_date=date(2026, 5, 19),
            updated_at=datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(feed["feed_type"], "current_event_live_scoring")
        self.assertEqual(feed["summary"]["result_count"], 2)
        self.assertEqual(feed["summary"]["leaderboard_count"], 1)
        self.assertEqual(feed["source_ids"], ["data_fei"])
        event = feed["events"][0]
        self.assertEqual(event["event_name"], "Spring International")
        self.assertEqual(event["leader_count"], 2)
        self.assertEqual([leader["horse_name"] for leader in event["leaders"]], ["Juniper", "Pocket Rocket"])
        self.assertEqual([leader["rank"] for leader in event["leaders"]], [1, 2])
        self.assertEqual([leader["finishing_score"] for leader in event["leaders"]], [29.0, 35.8])

    def test_equal_scores_share_rank(self):
        feed = build_live_scoring_feed(
            [
                result(source_record_id="fei-1", rider_name="Alex Rider", horse_name="Pocket Rocket", dressage_score=30.0),
                result(source_record_id="fei-2", rider_name="Blair Smith", horse_name="Juniper", dressage_score=30.0),
                result(source_record_id="fei-3", rider_name="Casey Lee", horse_name="Harbor", dressage_score=31.0),
            ],
            start_date=date(2026, 5, 18),
            end_date=date(2026, 5, 18),
        )

        ranks = [leader["rank"] for leader in feed["events"][0]["leaders"]]

        self.assertEqual(ranks, [1, 1, 3])

    def test_write_live_scoring_feed_creates_json(self):
        feed = build_live_scoring_feed(
            [result()],
            start_date=date(2026, 5, 18),
            end_date=date(2026, 5, 18),
            updated_at=datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "live.json"
            write_live_scoring_feed(output_path, feed)

            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["summary"]["result_count"], 1)
        self.assertEqual(payload["events"][0]["leaders"][0]["finishing_score"], 35.8)


if __name__ == "__main__":
    unittest.main()
