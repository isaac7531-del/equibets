import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from equibets.live_scoring import (
    discover_payloads,
    refresh_live_scoring,
    write_live_scoring_snapshot,
)


class LiveScoringRefreshTests(unittest.TestCase):
    def test_manifest_pull_consolidates_current_event_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "manifest.json").write_text(
                json.dumps({"search_results": [{"url": "fei.json"}, {"url": "usea.json"}]}),
                encoding="utf-8",
            )
            (root / "fei.json").write_text(
                json.dumps(
                    {
                        "source_id": "data_fei",
                        "collected_at": "2026-05-15T12:00:00Z",
                        "events": [
                            {
                                "event_name": "Kentucky Spring Horse Trials",
                                "event_date": "2026-05-14",
                                "level": "CCI3-S",
                                "country": "USA",
                                "results": [
                                    {
                                        "source_record_id": "fei-100",
                                        "rider_name": "Alex Rider",
                                        "horse_name": "Pocket Rocket",
                                        "dressage_score": 29.8,
                                        "show_jumping_penalties": 0,
                                        "cross_country_jump_penalties": 0,
                                        "cross_country_time_penalties": 2.4,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "usea.json").write_text(
                json.dumps(
                    {
                        "source_id": "usea",
                        "events": [
                            {
                                "event_name": "Kentucky Spring Horse Trials",
                                "event_date": "2026-05-14",
                                "level": "CCI3-S",
                                "country": "USA",
                                "results": [
                                    {
                                        "source_record_id": "usea-100",
                                        "rider_name": "Alex Rider",
                                        "horse_name": "Pocket Rocket",
                                        "dressage_score": 31.0,
                                        "show_jumping_penalties": 4,
                                        "cross_country_jump_penalties": 0,
                                        "cross_country_time_penalties": 3.2,
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            snapshot = refresh_live_scoring(
                [root / "manifest.json"],
                collected_at=datetime(2026, 5, 15, 13, 0, tzinfo=UTC),
            )

        self.assertEqual(snapshot["summary"]["discovered_payload_count"], 2)
        self.assertEqual(snapshot["summary"]["pulled_result_count"], 2)
        self.assertEqual(snapshot["summary"]["consolidated_result_count"], 1)
        self.assertEqual(snapshot["results"][0]["source_id"], "data_fei")
        self.assertEqual(snapshot["results"][0]["finishing_score"], 32.2)
        self.assertEqual(snapshot["predictions"][0]["likely_finishing_score"], 32.2)
        self.assertEqual(snapshot["predictions"][0]["confidence"], "low")

    def test_directory_search_and_since_filter_keep_new_results(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "old.json").write_text(
                json.dumps(
                    {
                        "source_id": "data_fei",
                        "results": [
                            {
                                "source_record_id": "old-1",
                                "rider": "Old Rider",
                                "horse": "Old Horse",
                                "event": "Older Event",
                                "event_date": "2026-05-01",
                                "level": "CCI2-S",
                                "country": "GBR",
                                "dressage_penalties": 33.0,
                                "sj_penalties": 0,
                                "xc_jump_penalties": 0,
                                "xc_time_penalties": 0,
                                "collected_at": "2026-05-10T00:00:00Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / "new.json").write_text(
                json.dumps(
                    {
                        "source_id": "data_fei",
                        "results": [
                            {
                                "rider": "Fresh Rider",
                                "horse": "Fresh Horse",
                                "event": "Fresh Event",
                                "event_date": "2026-05-15",
                                "level": "CCI2-S",
                                "country": "GBR",
                                "dressage_penalties": 30.0,
                                "sj_penalties": 4,
                                "xc_jump_penalties": 0,
                                "xc_time_penalties": 0.8,
                                "collected_at": "2026-05-15T09:00:00Z",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            discovered = discover_payloads([root])
            snapshot = refresh_live_scoring(
                [root],
                since=datetime(2026, 5, 15, 0, 0, tzinfo=UTC),
                collected_at=datetime(2026, 5, 15, 10, 0, tzinfo=UTC),
            )

        self.assertEqual([Path(path).name for path in discovered], ["new.json", "old.json"])
        self.assertEqual(snapshot["summary"]["pulled_result_count"], 1)
        self.assertEqual(snapshot["results"][0]["rider_name"], "Fresh Rider")
        self.assertEqual(snapshot["results"][0]["source_record_id"], "data-fei::2026-05-15::fresh-event::cci2-s::fresh-rider::fresh-horse")

    def test_writes_snapshot_json(self):
        snapshot = {
            "version": 1,
            "collected_at": "2026-05-15T00:00:00Z",
            "summary": {"pulled_result_count": 0},
            "results": [],
            "predictions": [],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "nested" / "live_scores.json"

            write_live_scoring_snapshot(snapshot, output)

            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), snapshot)


if __name__ == "__main__":
    unittest.main()
