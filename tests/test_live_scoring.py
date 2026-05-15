import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from equibets.live_scoring import (
    build_live_score_report,
    build_live_score_rows,
    current_event_window,
    main,
)
from equibets.results import EventingResult


def result(**overrides):
    values = {
        "source_id": "data_fei",
        "source_record_id": "fei-1",
        "source_priority": 0,
        "rider_name": "Alex Rider",
        "horse_name": "Pocket Rocket",
        "event_name": "Current Horse Trials",
        "event_date": "2026-05-15",
        "level": "CCI2",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-05-15T11:00:00+00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


def result_mapping(item):
    return {
        "source_id": item.source_id,
        "source_record_id": item.source_record_id,
        "source_priority": item.source_priority,
        "rider_name": item.rider_name,
        "horse_name": item.horse_name,
        "event_name": item.event_name,
        "event_date": item.event_date.isoformat(),
        "level": item.level,
        "country": item.country,
        "dressage_score": item.dressage_score,
        "show_jumping_penalties": item.show_jumping_penalties,
        "cross_country_jump_penalties": item.cross_country_jump_penalties,
        "cross_country_time_penalties": item.cross_country_time_penalties,
        "collected_at": item.collected_at.isoformat(),
        "is_user_entered": item.is_user_entered,
    }


class LiveScoringTests(unittest.TestCase):
    def test_current_event_window_includes_recent_and_next_day_results(self):
        window = current_event_window(date(2026, 5, 15), lookback_days=3, lookahead_days=1)

        self.assertEqual(window.start_date, date(2026, 5, 12))
        self.assertEqual(window.end_date, date(2026, 5, 16))

    def test_live_rows_rank_each_event_by_lowest_total(self):
        rows = build_live_score_rows(
            [
                result(source_record_id="fei-1", rider_name="Alex Rider", dressage_score=30.2),
                result(
                    source_record_id="fei-2",
                    rider_name="Blair Rider",
                    horse_name="River Star",
                    dressage_score=28.0,
                    show_jumping_penalties=0,
                ),
                result(
                    source_record_id="old-1",
                    event_name="Old Horse Trials",
                    event_date="2026-04-01",
                    dressage_score=25.0,
                ),
            ],
            current_event_window(date(2026, 5, 15)),
        )

        self.assertEqual([row.rider_name for row in rows], ["Blair Rider", "Alex Rider"])
        self.assertEqual([row.rank for row in rows], [1, 2])
        self.assertEqual(rows[0].total_penalties, 29.6)

    def test_live_report_groups_events_and_tracks_freshness(self):
        report = build_live_score_report(
            [
                result(source_record_id="fei-1"),
                result(
                    source_record_id="fei-2",
                    event_name="Second Horse Trials",
                    event_date="2026-05-16",
                    collected_at="2026-05-15T12:00:00+00:00",
                ),
            ],
            generated_at=datetime.fromisoformat("2026-05-15T13:00:00+00:00"),
            on_date=date(2026, 5, 15),
        )

        self.assertEqual(report["event_count"], 2)
        self.assertEqual(report["result_count"], 2)
        self.assertEqual(report["latest_collected_at"], "2026-05-15T12:00:00+00:00")
        self.assertEqual(report["events"][0]["results"][0]["rank"], 1)

    def test_cli_writes_live_score_report_from_existing_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            results_path = Path(tmp) / "results.json"
            output_path = Path(tmp) / "live_scores.json"
            results_path.write_text(
                json.dumps({"results": [result_mapping(result(source_record_id="fei-cli-1"))]}),
                encoding="utf-8",
            )

            exit_code = main(
                [
                    "--results-file",
                    str(results_path),
                    "--output",
                    str(output_path),
                    "--on-date",
                    "2026-05-15",
                ]
            )
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["event_count"], 1)
        self.assertEqual(payload["events"][0]["event_name"], "Current Horse Trials")


if __name__ == "__main__":
    unittest.main()
