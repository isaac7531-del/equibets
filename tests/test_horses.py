import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from equibets.horses import build_horse_index, save_horse_index
from equibets.results import EventingResult


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Spring Horse Trials",
        "event_date": "2026-03-01",
        "level": "CCI2-S",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-03-08T00:00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class HorseIndexTests(unittest.TestCase):
    def test_builds_one_record_per_collected_horse(self):
        records = build_horse_index(
            [
                result(source_record_id="fei-1", event_date="2025-01-01"),
                result(source_record_id="fei-2", rider_name="Morgan Lee", event_date="2026-01-01", level="CCI3-S"),
                result(
                    source_record_id="fei-3",
                    horse_name="Atlas Bay",
                    rider_name="Mia Hughes",
                    event_date="2026-02-01",
                    level="CCI4-S",
                ),
            ],
            active_since=date(2025, 7, 1),
        )

        self.assertEqual([record.horse_name for record in records], ["Atlas Bay", "Pocket Rocket"])
        pocket_rocket = records[1]
        self.assertEqual(pocket_rocket.result_count, 2)
        self.assertEqual(pocket_rocket.riders, ("Alex Rider", "Morgan Lee"))
        self.assertEqual(pocket_rocket.levels, ("CCI2-S", "CCI3-S"))
        self.assertTrue(pocket_rocket.is_currently_eventing)

    def test_marks_stale_horses_as_not_currently_eventing(self):
        records = build_horse_index(
            [result(event_date="2023-01-01")],
            active_since=date(2025, 1, 1),
        )

        self.assertFalse(records[0].is_currently_eventing)

    def test_saves_horse_index_counts(self):
        records = build_horse_index(
            [result(event_date="2026-01-01"), result(horse_name="Atlas Bay", event_date="2024-01-01")],
            active_since=date(2025, 1, 1),
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "horse_index.json"
            save_horse_index(records, path)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["horse_count"], 2)
        self.assertEqual(payload["current_horse_count"], 1)
        self.assertEqual(len(payload["horses"]), 2)


if __name__ == "__main__":
    unittest.main()
