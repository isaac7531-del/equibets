import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.live_scores import build_live_score_payload, save_live_score_payload
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
        "level": "CCI2*-S",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4.0,
        "cross_country_jump_penalties": 0.0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-06-17T12:00:00+00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class LiveScorePayloadTests(unittest.TestCase):
    def test_payload_groups_current_results_and_ranks_by_total_penalties(self):
        payload = build_live_score_payload(
            [
                result(
                    source_record_id="fei-2",
                    rider_name="Bailey Eventer",
                    horse_name="Low Score",
                    dressage_score=28.0,
                    show_jumping_penalties=0.0,
                    cross_country_time_penalties=0.0,
                ),
                result(),
                result(
                    source_record_id="fei-3",
                    event_date="2026-05-01",
                    rider_name="Old Result",
                    horse_name="Past Horse",
                ),
            ],
            window_start=date(2026, 6, 10),
            window_end=date(2026, 6, 19),
            generated_at=datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(payload["event_count"], 1)
        self.assertEqual(payload["result_count"], 2)
        self.assertEqual(payload["window_start"], "2026-06-10")
        event = payload["events"][0]
        self.assertEqual(event["event_name"], "Current Horse Trials")
        self.assertEqual(event["leader"]["horse_name"], "Low Score")
        self.assertEqual(event["leader"]["total_penalties"], 28.0)
        self.assertEqual([row["rank"] for row in event["results"]], [1, 2])

    def test_save_live_score_payload_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "live_scores.json"

            payload = save_live_score_payload(
                [result()],
                output_path,
                window_start=date(2026, 6, 10),
                window_end=date(2026, 6, 19),
                generated_at=datetime(2026, 6, 17, 13, 0, tzinfo=timezone.utc),
            )
            written_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(written_payload, payload)
        self.assertEqual(written_payload["source_id"], "data_fei")
        self.assertEqual(written_payload["events"][0]["leader"]["rider_name"], "Alex Rider")


if __name__ == "__main__":
    unittest.main()
