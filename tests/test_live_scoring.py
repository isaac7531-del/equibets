import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from equibets.live_scoring import (
    build_live_score_payload,
    current_event_window,
    save_live_score_payload,
)
from equibets.results import EventingResult


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Spring Horse Trials",
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
    def test_current_event_window_uses_rolling_dates(self):
        window_start, window_end = current_event_window(
            date(2026, 5, 18),
            days_back=3,
            days_forward=2,
        )

        self.assertEqual(window_start, date(2026, 5, 15))
        self.assertEqual(window_end, date(2026, 5, 20))

    def test_payload_filters_current_window_and_ranks_low_scores_first(self):
        payload = build_live_score_payload(
            [
                result(source_record_id="fei-2", rider_name="Zoe Rider", dressage_score=28.0),
                result(),
                result(source_record_id="old", event_date="2026-04-01", dressage_score=10.0),
            ],
            window_start=date(2026, 5, 17),
            window_end=date(2026, 5, 19),
            generated_at=datetime.fromisoformat("2026-05-18T18:00:00+00:00"),
        )

        self.assertEqual(payload["result_count"], 2)
        self.assertEqual(payload["source_ids"], ["data_fei"])
        scores = [item["finishing_score"] for item in payload["results"]]
        self.assertEqual(scores, [33.6, 35.8])
        self.assertEqual(payload["results"][0]["rider_name"], "Zoe Rider")

    def test_save_live_score_payload_writes_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live_scores.json"
            payload = save_live_score_payload(
                [result()],
                path=path,
                window_start=date(2026, 5, 18),
                window_end=date(2026, 5, 18),
            )

            saved = path.read_text(encoding="utf-8")

        self.assertIn('"result_count": 1', saved)
        self.assertEqual(payload["results"][0]["finishing_score"], 35.8)


if __name__ == "__main__":
    unittest.main()
