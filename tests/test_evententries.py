"""Tests for Event Entries scoring-board parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

import json

from equibets.evententries import (
    EventEntriesClass,
    parse_scoring_board,
    parse_scoring_strings,
)


COLLECTED_AT = datetime(2026, 9, 25, 13, 30, tzinfo=timezone.utc)
EVENT = EventEntriesClass(
    token="board-token",
    level="CCI4*-S",
    event_title="Stable View",
    event_date=date(2026, 9, 25),
    country="USA",
)


class EventEntriesParserTests(unittest.TestCase):
    def test_reads_dressage_penalties_and_skips_unfinished_rows(self) -> None:
        strings = [
            "CCI4-S",
            "CCI Four Star - S (CCI4-S)",
            "Dyri\nOwner: Horse Scout\nHeight: 16.2\nFEI: 106XB93",
            "Dyri",
            "1",
            "Lucienne Bellissimo (GBR)",
            "5.5\n7.5\n7.0",
            "66.67",
            "7.0\n7.5\n6.5",
            "69.79",
            "31.8",
            "Vandyke\nOwner: The RICO Syndicate\nHeight: 16.3\nFEI: 106VT19",
            "Vandyke",
            "3",
            "Allison Springer (USA)",
            "6.5\n6.0\n7.0",
            "65.00",
            "6.5\n6.0\n6.5",
            "62.92",
            "Qatar M\nOwner: Horse Scout\nHeight: 16.2\nFEI: H0587581",
            "Qatar M",
            "8",
            "Dress Score",
        ]

        results = parse_scoring_strings(strings, event=EVENT, collected_at=COLLECTED_AT)

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result.rider_name, "Lucienne Bellissimo (GBR)")
        self.assertEqual(result.horse_name, "Dyri")
        self.assertEqual(result.dressage_score, 31.8)
        self.assertEqual(result.show_jumping_penalties, 0.0)
        self.assertEqual(result.cross_country_jump_penalties, 0.0)
        self.assertEqual(result.cross_country_time_penalties, 0.0)
        self.assertEqual(result.level, "CCI4*-S")
        self.assertEqual(result.event_name, "Stable View · CCI4*-S")
        self.assertEqual(result.event_date, date(2026, 9, 25))
        self.assertEqual(result.country, "USA")
        self.assertEqual(result.source_id, "evententries")
        self.assertEqual(result.source_priority, 55)

    def test_skips_eliminated_rows(self) -> None:
        strings = [
            "CCI3-S",
            "Corvett\nOwner: Black Flag\nHeight: 16.1\nFEI: 105QF45",
            "Corvett",
            "17",
            "Emily Hamel (USA)",
            "6.0\n6.5",
            "60.00",
            "6.0\n6.0",
            "61.00",
            "39.5",
            "EL",
        ]

        results = parse_scoring_strings(strings, event=EVENT, collected_at=COLLECTED_AT)

        self.assertEqual(results, [])

    def test_index_stream_keeps_both_horses_for_one_rider(self) -> None:
        strings = [
            "com.kyler.ee.shared.ScoringItem/1",
            "java.util.ArrayList/1",
            "com.kyler.ee.shared.ScoringBoardEntry/1",
            "CCI2-S",
            "Alyssa Phillips (USA)",
            "",
            "Nadal",
            "Nadal\nOwner: Alyssa Phillips\nHeight: 17.2\nFEI: 108PO07",
            "25.9",
            "75.68",
            "72.50",
            "8.0\n7.5",
            "6.5\n7.5",
            "1",
            "63",
            "Rockett 19",
            "Rockett 19\nOwner: Alyssa Phillips\nHeight: 16.1\nFEI: 107GE40",
            "33.0",
            "67.92",
            "66.04",
            "8.0\n7.0",
            "8.0\n7.5",
            "3",
            "19",
            "EL",
        ]

        def ref(value: str) -> str:
            return str(strings.index(value) + 1)

        def entry(horse: str, bio: str, rider: str, bib: str, penalty: str, percent_a: str, marks_a: str, percent_b: str, marks_b: str, place: str) -> list[str]:
            return [
                ref(place),
                ref("com.kyler.ee.shared.ScoringItem/1"),
                ref(penalty),
                ref("com.kyler.ee.shared.ScoringItem/1"),
                ref(percent_b),
                ref(marks_b),
                ref("com.kyler.ee.shared.ScoringItem/1"),
                ref(percent_a),
                ref(marks_a),
                ref("com.kyler.ee.shared.ScoringItem/1"),
                ref(rider),
                ref("java.util.ArrayList/1"),
                ref(rider),
                ref(""),
                ref("com.kyler.ee.shared.ScoringItem/1"),
                ref(bib),
                ref(""),
                ref("com.kyler.ee.shared.ScoringItem/1"),
                ref(horse),
                ref(bio),
                ref("com.kyler.ee.shared.ScoringItem/1"),
                ref("com.kyler.ee.shared.ScoringBoardEntry/1"),
            ]

        indexes = [
            ref("CCI2-S"),
            *entry(
                "Rockett 19",
                "Rockett 19\nOwner: Alyssa Phillips\nHeight: 16.1\nFEI: 107GE40",
                "Alyssa Phillips (USA)",
                "19",
                "33.0",
                "67.92",
                "8.0\n7.0",
                "66.04",
                "8.0\n7.5",
                "3",
            ),
            *entry(
                "Nadal",
                "Nadal\nOwner: Alyssa Phillips\nHeight: 17.2\nFEI: 108PO07",
                "Alyssa Phillips (USA)",
                "63",
                "25.9",
                "75.68",
                "8.0\n7.5",
                "72.50",
                "6.5\n7.5",
                "1",
            ),
            ref("EL"),
        ]
        body = f"//OK[{','.join(indexes)},{json.dumps(strings)},0,7]".encode()
        results = parse_scoring_board(body, event=EVENT, collected_at=COLLECTED_AT)
        by_horse = {result.horse_name: result for result in results}

        self.assertEqual(set(by_horse), {"Nadal", "Rockett 19"})
        self.assertEqual(by_horse["Nadal"].rider_name, "Alyssa Phillips (USA)")
        self.assertEqual(by_horse["Nadal"].dressage_score, 25.9)
        self.assertEqual(by_horse["Rockett 19"].dressage_score, 33.0)
        self.assertEqual(by_horse["Nadal"].level, "CCI2*-S")


if __name__ == "__main__":
    unittest.main()
