"""Tests for Asian Games individual eventing phase parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.asiangames import (
    ASIAN_GAMES_EVENTING_2026,
    parse_individual_results,
    results_url,
)


def _competitor(
    reg: str,
    name: str,
    horse: str,
    result: str | None,
    irm: str = "OK",
    extensions: list[tuple[str, str]] | None = None,
) -> dict[str, object]:
    return {
        "Reg": reg,
        "Name": name,
        "Result": result,
        "IRM": irm,
        "Extensions": [
            {"Code": code, "Value": value}
            for code, value in [("HORSE", horse), *(extensions or [])]
        ],
    }


class AsianGamesParseTests(unittest.TestCase):
    def test_results_url_uses_the_public_individual_endpoint(self):
        url = results_url("O.EVENINDV----------.XC--.000200--")
        self.assertIn("/s/AG2026/en/EQU/results/", url)
        self.assertTrue(url.endswith("O.EVENINDV----------.XC--.000200--"))

    def test_phase_penalties_join_and_unscored_rows_are_skipped(self):
        event = ASIAN_GAMES_EVENTING_2026
        dressage = {
            "Competitors": [
                _competitor(
                    "1",
                    "KHAW-NGAM Supap",
                    "VINETTO 3",
                    "47.30",
                    extensions=[("PERCENTAGE", "52.70")],
                ),
                _competitor("2", "KANG Hansu", "FIRST DE MONTIEGE", "38.30"),
                _competitor("3", "HO Annie", "EVITA AP", "31.10"),
                _competitor("4", "Later Starter", "NO SCORE", None),
            ]
        }
        jumping = {
            "Competitors": [
                _competitor(
                    "1",
                    "KHAW-NGAM Supap",
                    "VINETTO 3",
                    "47.30",
                    extensions=[("PEN_JUMP", "0"), ("PEN_TIME", "0.00"), ("TOTAL_PENALTIES", "0.00")],
                ),
                _competitor(
                    "2",
                    "KANG Hansu",
                    "FIRST DE MONTIEGE",
                    "46.30",
                    extensions=[("PEN_JUMP", "8"), ("PEN_TIME", "0.00"), ("TOTAL_PENALTIES", "8.00")],
                ),
                _competitor(
                    "3",
                    "HO Annie",
                    "EVITA AP",
                    "35.10",
                    extensions=[("PEN_JUMP", "4"), ("PEN_TIME", "0.00"), ("TOTAL_PENALTIES", "4.00")],
                ),
            ]
        }
        cross_country = {
            "Competitors": [
                _competitor(
                    "1",
                    "KHAW-NGAM Supap",
                    "VINETTO 3",
                    "93.70",
                    extensions=[("PEN_JUMP", "20"), ("PEN_TIME", "26.40"), ("TOTAL_PENALTIES", "46.40")],
                ),
                _competitor("2", "KANG Hansu", "FIRST DE MONTIEGE", "EL", irm="EL"),
                _competitor("3", "HO Annie", "EVITA AP", "35.10"),
            ]
        }

        results = parse_individual_results(
            dressage,
            jumping,
            cross_country,
            event_name=str(event["event_name"]),
            level=str(event["level"]),
            event_date=event["event_date"],
            country=str(event["country"]),
            collected_at=datetime(2026, 9, 23, 4, 0, tzinfo=timezone.utc),
        )

        self.assertEqual([result.horse_name for result in results], ["VINETTO 3"])
        scored = results[0]
        self.assertEqual(scored.rider_name, "KHAW-NGAM Supap")
        self.assertEqual(scored.event_name, "Asian Games · Eventing Individual")
        self.assertEqual(scored.level, "Eventing Individual")
        self.assertEqual(scored.event_date, date(2026, 9, 22))
        self.assertEqual(scored.country, "JPN")
        self.assertEqual(scored.dressage_score, 47.3)
        self.assertEqual(scored.show_jumping_penalties, 0.0)
        self.assertEqual(scored.cross_country_jump_penalties, 20.0)
        self.assertEqual(scored.cross_country_time_penalties, 26.4)
        self.assertEqual(scored.finishing_score, 93.7)
        self.assertEqual(scored.source_id, "asiangames")
        self.assertTrue(scored.source_record_id.startswith("asiangames:"))


if __name__ == "__main__":
    unittest.main()
