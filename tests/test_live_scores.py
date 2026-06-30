import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.live_scores import build_live_score_payload, current_event_window, write_live_score_payload
from equibets.results import EventingResult


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Current Horse Trials",
        "event_date": "2026-05-18",
        "level": "CCI3*-S",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4.0,
        "cross_country_jump_penalties": 0.0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-05-18T12:00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class LiveScoreTests(unittest.TestCase):
    def test_current_event_window_includes_recent_and_upcoming_events(self):
        start_date, end_date = current_event_window(date(2026, 5, 18), days_back=3, days_forward=2)

        self.assertEqual(start_date, date(2026, 5, 15))
        self.assertEqual(end_date, date(2026, 5, 20))

    def test_build_live_score_payload_filters_groups_and_ranks_results(self):
        payload = build_live_score_payload(
            [
                result(source_record_id="leader", rider_name="Best Rider", horse_name="Fast Horse", dressage_score=25.0),
                result(source_record_id="second", rider_name="Second Rider", horse_name="Steady Horse", dressage_score=31.0),
                result(
                    source_record_id="old",
                    event_name="Old Horse Trials",
                    event_date="2026-04-01",
                    dressage_score=20.0,
                ),
            ],
            start_date=date(2026, 5, 17),
            end_date=date(2026, 5, 19),
            generated_at=datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(payload["event_count"], 1)
        self.assertEqual(payload["result_count"], 2)
        self.assertEqual(payload["generated_at"], "2026-05-18T13:00:00+00:00")
        event = payload["events"][0]
        self.assertEqual(event["event_name"], "Current Horse Trials")
        self.assertEqual(event["result_count"], 2)
        self.assertEqual(event["standings"][0]["rank"], 1)
        self.assertEqual(event["standings"][0]["horse_name"], "Fast Horse")
        self.assertEqual(event["standings"][0]["finishing_score"], 30.6)
        self.assertEqual(event["standings"][1]["rank"], 2)

    def test_write_live_score_payload_creates_stable_json(self):
        payload = build_live_score_payload(
            [result()],
            start_date=date(2026, 5, 18),
            end_date=date(2026, 5, 18),
            generated_at=datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc),
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "live_scores.json"
            write_live_score_payload(payload, output)
            contents = output.read_text(encoding="utf-8")

        self.assertIn('"event_count": 1', contents)
        self.assertTrue(contents.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
