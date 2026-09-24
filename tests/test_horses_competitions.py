"""Tests for Horses & Competitions public ranking parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.horses_competitions import (
    lignieres_sep_2026_event,
    parse_ranking,
    ranking_url,
)


def _row(
    *,
    bib: str = "52",
    firstname: str = "Jillian",
    lastname: str = "GIESSEN",
    nation: str = "NED",
    horse: str = "TENDRESSE VAN DE MEYHOEVE",
    dressage_total: float | int | str = 25.8,
    dressage_percent: float | int | str = 74.16,
    dressage_label: str = "",
    total_label: str = "25.8",
    out_of_rank: bool = False,
    jumping_total: float = 0,
    xc_jump: float = 0,
    xc_time: float = 0,
) -> dict[str, object]:
    return {
        "bib": bib,
        "outOfRank": out_of_rank,
        "rank": 1,
        "result": {
            "total_label": total_label,
            "test": {
                "dressage": {
                    "total": dressage_total,
                    "total_percent": dressage_percent,
                    "indice_label": dressage_label,
                },
                "jumping": [{"total": jumping_total, "pts": jumping_total, "pts_time": 0}],
                "eventing": {"pts": xc_jump, "pts_time": xc_time},
            },
        },
        "rider": {"firstname": firstname, "lastname": lastname, "nation": nation},
        "horse": {"name": horse},
    }


def _payload(*rows: dict[str, object], name: str = "CCI2*-L", event_date: str = "2026-09-23") -> dict[str, object]:
    return {
        "show": {"name": name, "date": event_date, "number": 3},
        "ranking": list(rows),
    }


class HorsesCompetitionsParseTests(unittest.TestCase):
    def test_ranking_url_uses_the_public_event_show_endpoint(self):
        self.assertEqual(
            ranking_url(4640, 3),
            "https://api.horses-and-competitions.com/fr/api/v1/event/4640/show/3/ranking",
        )

    def test_lignieres_event_uses_the_public_2026_id(self):
        event = lignieres_sep_2026_event()
        self.assertEqual(event.event_id, 4640)
        self.assertEqual(event.country, "FRA")

    def test_scored_dressage_row_is_kept_and_unscored_rows_are_skipped(self):
        event = lignieres_sep_2026_event()
        results = parse_ranking(
            _payload(
                _row(),
                _row(
                    bib="1",
                    firstname="Thomas",
                    lastname="CARLILE",
                    nation="FRA",
                    horse="IMPERIALE DAM",
                    dressage_total=0,
                    dressage_percent=0,
                    total_label="",
                ),
                _row(
                    bib="9",
                    firstname="Retired",
                    lastname="RIDER",
                    horse="OUT",
                    out_of_rank=True,
                ),
            ),
            event=event,
            collected_at=datetime(2026, 9, 23, 14, 20, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 1)
        scored = results[0]
        self.assertEqual(scored.source_id, "horses_competitions")
        self.assertTrue(scored.source_record_id.startswith("horses_competitions:"))
        self.assertEqual(scored.rider_name, "Jillian GIESSEN (NED)")
        self.assertEqual(scored.horse_name, "TENDRESSE VAN DE MEYHOEVE")
        self.assertEqual(scored.event_name, "Lignières · CCI2*-L")
        self.assertEqual(scored.event_date, date(2026, 9, 23))
        self.assertEqual(scored.level, "CCI2*-L")
        self.assertEqual(scored.country, "FRA")
        self.assertEqual(scored.dressage_score, 25.8)
        self.assertEqual(scored.show_jumping_penalties, 0.0)
        self.assertEqual(scored.cross_country_jump_penalties, 0.0)
        self.assertEqual(scored.cross_country_time_penalties, 0.0)
        self.assertEqual(scored.finishing_score, 25.8)

    def test_later_phase_penalties_are_added_to_the_finishing_score(self):
        results = parse_ranking(
            _payload(
                _row(jumping_total=4, xc_jump=20, xc_time=1.2),
            ),
            event=lignieres_sep_2026_event(),
        )

        scored = results[0]
        self.assertEqual(scored.show_jumping_penalties, 4.0)
        self.assertEqual(scored.cross_country_jump_penalties, 20.0)
        self.assertEqual(scored.cross_country_time_penalties, 1.2)
        self.assertEqual(scored.finishing_score, 51.0)

    def test_non_fei_class_names_are_skipped(self):
        results = parse_ranking(
            _payload(_row(), name="Pro 2 - 7 ans"),
            event=lignieres_sep_2026_event(),
        )
        self.assertEqual(results, [])

    def test_status_labels_are_skipped(self):
        results = parse_ranking(
            _payload(_row(dressage_label="EL")),
            event=lignieres_sep_2026_event(),
        )
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
