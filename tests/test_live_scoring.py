import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.live_scoring import (
    build_live_scoreboards,
    live_scoreboards_payload,
    load_result_files,
    write_live_scoreboards,
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
        "event_date": "2026-05-14",
        "level": "CCI2",
        "country": "GBR",
        "dressage_score": 30.2,
        "show_jumping_penalties": 4,
        "cross_country_jump_penalties": 0,
        "cross_country_time_penalties": 1.6,
        "collected_at": "2026-05-15T12:00:00+00:00",
        "is_user_entered": False,
    }
    values.update(overrides)
    return EventingResult.from_mapping(values)


class LiveScoringTests(unittest.TestCase):
    def test_build_live_scoreboards_filters_current_events_and_ranks_scores(self):
        scoreboards = build_live_scoreboards(
            [
                result(source_record_id="fei-1", dressage_score=30.2),
                result(
                    source_record_id="fei-2",
                    rider_name="Blair Vale",
                    horse_name="Oak Star",
                    dressage_score=28.5,
                    show_jumping_penalties=0,
                    cross_country_time_penalties=0.4,
                    collected_at="2026-05-15T13:00:00+00:00",
                ),
                result(
                    source_record_id="old",
                    event_name="Winter Horse Trials",
                    event_date="2026-04-01",
                    dressage_score=20,
                ),
            ],
            as_of=date(2026, 5, 15),
            lookback_days=3,
            lookahead_days=1,
        )

        self.assertEqual(len(scoreboards), 1)
        scoreboard = scoreboards[0]
        self.assertEqual(scoreboard.event_key, "spring-horse-trials-2026-05-14-cci2-gbr")
        self.assertEqual(scoreboard.result_count, 2)
        self.assertEqual(scoreboard.leader.rider_name, "Blair Vale")
        self.assertEqual(scoreboard.leader.total_penalties, 28.9)
        self.assertEqual([score.rank for score in scoreboard.scores], [1, 2])
        self.assertEqual(scoreboard.last_collected_at.isoformat(), "2026-05-15T13:00:00+00:00")

    def test_build_live_scoreboards_consolidates_duplicate_starts(self):
        scoreboards = build_live_scoreboards(
            [
                result(
                    source_id="user_submission",
                    source_record_id="user-1",
                    source_priority=100,
                    dressage_score=35,
                    collected_at="2026-05-15T11:00:00+00:00",
                    is_user_entered=True,
                ),
                result(source_record_id="fei-1", dressage_score=30.2),
            ],
            as_of=date(2026, 5, 15),
        )

        self.assertEqual(scoreboards[0].result_count, 1)
        self.assertEqual(scoreboards[0].leader.source_id, "data_fei")
        self.assertEqual(scoreboards[0].leader.total_penalties, 35.8)

    def test_live_scoreboards_payload_and_writer_are_json_serializable(self):
        scoreboards = build_live_scoreboards([result()], as_of=date(2026, 5, 15))
        generated_at = datetime(2026, 5, 15, 14, 30, tzinfo=timezone.utc)

        payload = live_scoreboards_payload(
            scoreboards,
            generated_at=generated_at,
            as_of=date(2026, 5, 15),
        )

        self.assertEqual(payload["generated_at"], "2026-05-15T14:30:00+00:00")
        self.assertEqual(payload["source_ids"], ["data_fei"])
        self.assertEqual(payload["events"][0]["leader"]["horse_name"], "Pocket Rocket")

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "live_scoring.json"
            write_live_scoreboards(
                scoreboards,
                output,
                generated_at=generated_at,
                as_of=date(2026, 5, 15),
            )
            written = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(written["events"][0]["scores"][0]["total_penalties"], 35.8)

    def test_load_result_files_skips_missing_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "results": [
                            {
                                "source_id": "data_fei",
                                "source_record_id": "fei-1",
                                "source_priority": 0,
                                "rider_name": "Alex Rider",
                                "horse_name": "Pocket Rocket",
                                "event_name": "Spring Horse Trials",
                                "event_date": "2026-05-14",
                                "level": "CCI2",
                                "country": "GBR",
                                "dressage_score": 30.2,
                                "show_jumping_penalties": 4,
                                "cross_country_jump_penalties": 0,
                                "cross_country_time_penalties": 1.6,
                                "collected_at": "2026-05-15T12:00:00+00:00",
                                "is_user_entered": False,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = load_result_files([Path(tmp) / "missing.json", path])

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].horse_name, "Pocket Rocket")


if __name__ == "__main__":
    unittest.main()
