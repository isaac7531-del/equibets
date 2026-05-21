import tempfile
import unittest
from pathlib import Path

from equibets.results import EventingResult, ResultStore
from equibets.update_public_data import consolidate_public_results, discover_result_files


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Spring Horse Trials",
        "event_date": "2026-03-01",
        "level": "CCI2",
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


class PublicDataUpdateTests(unittest.TestCase):
    def test_consolidates_fei_and_national_result_stores(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fei_path = tmp_path / "fei_results.json"
            national_path = tmp_path / "national" / "usea.json"
            ResultStore(fei_path, source_id="data_fei").save([result()])
            ResultStore(national_path, source_id="usea").save(
                [
                    result(
                        source_id="usea",
                        source_record_id="usea-duplicate",
                        source_priority=50,
                        dressage_score=31.0,
                    ),
                    result(
                        source_id="usea",
                        source_record_id="usea-2",
                        source_priority=50,
                        rider_name="National Rider",
                        horse_name="Local Star",
                        event_name="Local Horse Trials",
                        level="Training",
                        country="USA",
                    ),
                ]
            )

            input_files = discover_result_files(
                [fei_path],
                include_default_fei=False,
                national_results_dir=national_path.parent,
            )
            consolidated, summary = consolidate_public_results(input_files)

        self.assertEqual(input_files, (national_path, fei_path))
        self.assertEqual(len(consolidated), 2)
        self.assertEqual(consolidated[0].source_id, "data_fei")
        self.assertEqual(summary.countries, ("GBR", "USA"))
        self.assertEqual(summary.source_ids, ("data_fei", "usea"))
        self.assertEqual(summary.configured_national_federations, 135)


if __name__ == "__main__":
    unittest.main()
