"""Tests for World Sport Timing final classification parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.worldsporttiming import (
    WorldSportTimingBoard,
    mondial_du_lion_oct_2026_boards,
    morven_park_oct_2026_boards,
    parse_result_page,
)


SAMPLE_HTML = """
<table>
  <tr class="line_odd">
    <td class="table-col font-weight-bold">1.</td>
    <td class="table-col"><div class="w-100">48</div>
      <div class="flag flag-liste div-big flag-USA">
        <img src="https://static.wstapi.fr/results/assets/img/flags/USA.png" alt="flag">
      </div>
    </td>
    <td class="table-col row">
      <div class="col-12 font-weight-bold rider">
        Sharon WHITE
        <span class="infos text-uppercase font-weight-normal text-black-50 table-none">Sharon WHITE</span>
      </div>
      <div class="col-12 horse horse-info-container">
        <span class="horse font-weight-bold text-uppercase">CLAUS 63</span>
        <span class="infos text-uppercase font-weight-normal text-black-50 table-none">HOLST</span>
      </div>
    </td>
    <td class="table-col table-xs"></td>
    <td class="table-col table-none">26.0<br>(2.)</td>
    <td class="table-col table-none">0&nbsp;/&nbsp;4.8<br>10&#039;21&quot;</td>
    <td class="table-col">30.8<br>(3.)</td>
    <td class="table-col table-none">0&nbsp;/&nbsp;0.0<br>70"</td>
    <td class="table-col"><div class="font-weight-bold">30.8</div>
      <div class="text-black-50 infos text-center">USD&nbsp;66667.00</div>
    </td>
  </tr>
  <tr class="line_even">
    <td class="table-col font-weight-bold">7.</td>
    <td class="table-col"><div class="w-100">41</div>
      <img src="https://static.wstapi.fr/results/assets/img/flags/USA.png" alt="flag">
    </td>
    <td>
      <div class="rider">Isabelle BOSLEY</div>
      <span class="horse">CONNER</span>
    </td>
    <td></td>
    <td>28.9<br>(9.)</td>
    <td>0 / 0.0<br>10&#039;09&quot;</td>
    <td>28.9<br>(2.)</td>
    <td>12 / 1.6<br>75"</td>
    <td><div>42.5</div></td>
  </tr>
  <tr class="line_odd">
    <td></td>
    <td><div>50</div></td>
    <td>
      <div class="rider">Bruce O. DAVIDSON JR.</div>
      <span class="horse">SOROCAIMA</span>
    </td>
    <td></td>
    <td>37.4<br>(31.)</td>
    <td></td>
    <td></td>
    <td></td>
    <td>WD-XC</td>
  </tr>
  <tr class="line_even">
    <td></td>
    <td><div>45</div></td>
    <td>
      <div class="rider">Lauren NICHOLSON</div>
      <span class="horse">I&#039;LL HAVE ANOTHER</span>
    </td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
    <td></td>
    <td>WD-DR</td>
  </tr>
</table>
"""

MISMATCH_HTML = """
<table>
  <tr class="line_odd">
    <td>1.</td>
    <td><div>48</div></td>
    <td>
      <div class="rider">Sharon WHITE</div>
      <span class="horse">CLAUS 63</span>
    </td>
    <td></td>
    <td>26.0</td>
    <td>0 / 4.8</td>
    <td>30.8</td>
    <td>0 / 0.0</td>
    <td>99.9</td>
  </tr>
</table>
"""


def _board() -> WorldSportTimingBoard:
    return WorldSportTimingBoard(
        url="https://results.example/4L-SJ/result",
        event_name="Morven Park · CCI4*-L",
        level="CCI4*-L",
        event_date=date(2026, 10, 8),
        country="USA",
    )


class WorldSportTimingTests(unittest.TestCase):
    def test_parses_final_phase_penalties_and_skips_status_rows(self) -> None:
        collected_at = datetime(2026, 10, 12, 2, 30, tzinfo=timezone.utc)
        results = parse_result_page(SAMPLE_HTML, board=_board(), collected_at=collected_at)

        self.assertEqual(
            [(result.rider_name, result.horse_name) for result in results],
            [("Sharon WHITE (USA)", "CLAUS 63"), ("Isabelle BOSLEY (USA)", "CONNER")],
        )
        leader = results[0]
        self.assertEqual(leader.dressage_score, 26.0)
        self.assertEqual(leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(leader.cross_country_time_penalties, 4.8)
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 30.8)
        self.assertEqual(leader.event_name, "Morven Park · CCI4*-L")
        self.assertEqual(leader.event_date, date(2026, 10, 8))
        self.assertEqual(leader.country, "USA")
        self.assertEqual(leader.source_id, "worldsporttiming")
        self.assertEqual(leader.source_priority, 6)
        self.assertFalse(leader.is_user_entered)

        show_jumping_round = results[1]
        self.assertEqual(show_jumping_round.show_jumping_penalties, 13.6)
        self.assertEqual(show_jumping_round.finishing_score, 42.5)

    def test_rejects_a_total_that_does_not_match_phase_penalties(self) -> None:
        with self.assertRaises(ValueError):
            parse_result_page(MISMATCH_HTML, board=_board())

    def test_morven_park_boards_use_the_show_start_date(self) -> None:
        boards = morven_park_oct_2026_boards()
        self.assertEqual([board.level for board in boards], ["CCI4*-L", "CCI4*-S"])
        self.assertTrue(all(board.event_date == date(2026, 10, 8) for board in boards))
        self.assertTrue(all(board.country == "USA" for board in boards))
        self.assertTrue(all(board.url.startswith("https://results.worldsporttiming.com/") for board in boards))

    def test_mondial_du_lion_board_is_the_finished_six_year_old_final(self) -> None:
        boards = mondial_du_lion_oct_2026_boards()
        self.assertEqual(len(boards), 1)
        board = boards[0]
        self.assertEqual(board.event_name, "Mondial du Lion · 6-year-old")
        self.assertEqual(board.level, "6-year-old")
        self.assertEqual(board.event_date, date(2026, 10, 15))
        self.assertEqual(board.country, "FRA")
        self.assertTrue(board.url.endswith("/6YO-SJ/result"))


if __name__ == "__main__":
    unittest.main()
