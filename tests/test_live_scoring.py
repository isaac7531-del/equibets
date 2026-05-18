import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.live_scoring import (
    current_event_results,
    current_event_window,
    live_scoreboard_mapping,
    save_live_scoreboard,
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
        window = current_event_window(
            today=date(2026, 5, 18),
            lookback_days=3,
            lookahead_days=2,
        )

        self.assertEqual(window.start_date, date(2026, 5, 15))
        self.assertEqual(window.end_date, date(2026, 5, 20))

    def test_current_event_results_filter_and_consolidate_scores(self):
        user_duplicate = result(
            source_id="user_submission",
            source_record_id="user-1",
            source_priority=100,
            dressage_score=36,
            is_user_entered=True,
        )
        older_result = result(
            source_record_id="old-1",
            event_name="Older Horse Trials",
            event_date="2026-05-01",
        )

        scores = current_event_results(
            [user_duplicate, older_result, result()],
            start_date=date(2026, 5, 15),
            end_date=date(2026, 5, 18),
        )

        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].source_id, "data_fei")
        self.assertEqual(scores[0].finishing_score, 35.8)

    def test_live_scoreboard_mapping_contains_freshness_and_phase_scores(self):
        payload = live_scoreboard_mapping(
            [result()],
            start_date=date(2026, 5, 18),
            end_date=date(2026, 5, 18),
            generated_at=datetime(2026, 5, 18, 13, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(payload["result_count"], 1)
        self.assertEqual(payload["generated_at"], "2026-05-18T13:00:00+00:00")
        self.assertEqual(payload["latest_collected_at"], "2026-05-18T12:00:00+00:00")
        self.assertEqual(payload["scores"][0]["rider_name"], "Alex Rider")
        self.assertEqual(payload["scores"][0]["finishing_score"], 35.8)

    def test_save_live_scoreboard_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "live_scores.json"
            save_live_scoreboard(
                [result()],
                path,
                start_date=date(2026, 5, 18),
                end_date=date(2026, 5, 18),
            )

            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["window"]["start_date"], "2026-05-18")
        self.assertEqual(payload["scores"][0]["horse_name"], "Pocket Rocket")


if __name__ == "__main__":
    unittest.main()
