import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.live_scoring import build_live_score_feed, current_event_window, save_live_score_feed
from equibets.results import EventingResult


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Current Horse Trials",
        "event_date": "2026-06-17",
        "level": "CCI3*-S",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-06-17T12:00:00+00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class LiveScoringTests(unittest.TestCase):
    def test_current_event_window_includes_recent_and_upcoming_days(self):
        window_start, window_end = current_event_window(
            date(2026, 6, 17),
            lookback_days=1,
            lookahead_days=2,
        )

        self.assertEqual(window_start, date(2026, 6, 16))
        self.assertEqual(window_end, date(2026, 6, 19))

    def test_live_score_feed_groups_events_and_ranks_lowest_score_first(self):
        feed = build_live_score_feed(
            [
                result(source_record_id="fei-1", rider_name="Alex Rider", horse_name="Pocket Rocket"),
                result(
                    source_record_id="fei-2",
                    rider_name="Morgan Lee",
                    horse_name="Copperfield",
                    dressage_score=28.0,
                    show_jumping_penalties=0,
                    cross_country_jump_penalties=0,
                    cross_country_time_penalties=0,
                ),
                result(
                    source_record_id="old",
                    event_name="Old Horse Trials",
                    event_date="2026-06-10",
                ),
            ],
            window_start=date(2026, 6, 16),
            window_end=date(2026, 6, 18),
            updated_at=datetime(2026, 6, 17, 13, tzinfo=timezone.utc),
        )

        self.assertEqual(feed["score_count"], 2)
        self.assertEqual(feed["event_count"], 1)
        event = feed["events"][0]
        self.assertEqual(event["event_name"], "Current Horse Trials")
        self.assertEqual(event["entry_count"], 2)
        self.assertEqual(event["leader"]["horse_name"], "Copperfield")
        self.assertEqual(event["leader"]["finishing_score"], 28.0)
        self.assertEqual([entry["rank"] for entry in event["entries"]], [1, 2])

    def test_save_live_score_feed_writes_json_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live_scores.json"
            payload = save_live_score_feed(
                [result()],
                path,
                window_start=date(2026, 6, 16),
                window_end=date(2026, 6, 18),
            )

            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(saved, payload)
        self.assertEqual(saved["source_id"], "data_fei")
        self.assertEqual(saved["events"][0]["entries"][0]["rider_name"], "Alex Rider")


if __name__ == "__main__":
    unittest.main()
