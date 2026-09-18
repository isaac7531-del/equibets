"""Tests for EventingScores live result-board parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.eventingscores import (
    EventingScoresBoard,
    blenheim_sep_2026_boards,
    parse_leaderboard_results,
)


SAMPLE_EIGHT_NINE_YO_HTML = """
<html>
  <head><title>EventingScores</title></head>
  <body>
    <table>
      <thead>
        <tr>
          <th>No</th><th></th><th>Rider</th><th>Horse</th>
          <th>M %</th><th>C %</th><th>E %</th><th>Dressage</th>
          <th>SJ</th><th>XCT</th><th>XCJ</th><th>Total</th><th>Place</th>
        </tr>
      </thead>
      <tbody>
        <tr class="scored allPhasesVerified first">
          <td>101</td>
          <td class="flag"><img src="/images/Flags/GBR.svg" alt="GBR" /></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD DANNY DE MUZE" data-number="101"
              data-rider="Tom McEwen (GBR)">BROOKFIELD DANNY DE MUZE<span class="owners"><br>Mrs Alison Swinburn</span></td>
          <td class="score">71.88%</td>
          <td class="score">71.67%</td>
          <td class="score">74.79%</td>
          <td class="score"><a href="/movements.html">27.2</a></td>
          <td class="score"></td>
          <td class="score"></td>
          <td class="score"></td>
          <td class="score">27.2</td>
          <td>1st</td>
        </tr>
        <tr class="scored allPhasesVerified first">
          <td>102</td>
          <td class="flag"><img src="/images/Flags/NZL.svg" alt="NZL" /></td>
          <td>Samantha Lissington (NZL)</td>
          <td data-horse="CHAKITA" data-number="102"
              data-rider="Samantha Lissington (NZL)">CHAKITA</td>
          <td class="score">63.75%</td>
          <td class="score">66.88%</td>
          <td class="score">63.96%</td>
          <td class="score">35.1</td>
          <td class="score">4</td>
          <td class="score">0 in 6.40</td>
          <td class="score">0</td>
          <td class="score">39.1</td>
          <td>2nd</td>
        </tr>
        <tr class="unscored first">
          <td>105</td>
          <td class="flag"><img src="/images/Flags/GBR.svg" alt="GBR" /></td>
          <td>Kirsty Chabert (GBR)</td>
          <td data-horse="CLIMATE CHANGE" data-number="105"
              data-rider="Kirsty Chabert (GBR)">CLIMATE CHANGE</td>
          <td></td><td></td><td></td>
          <td>Thu 09:24</td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SAMPLE_CCI4_LONG_START_LIST_HTML = """
<html>
  <head><title>EventingScores</title></head>
  <body>
    <table>
      <thead>
        <tr>
          <th>No</th><th></th><th>Rider</th><th>Horse</th>
          <th>M %</th><th>C %</th><th>E %</th><th>Dressage</th>
          <th>XCT</th><th>XCJ</th><th>SJ</th><th>Total</th><th>Place</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1</td>
          <td></td>
          <td>Clarke Johnstone (NZL)</td>
          <td data-horse="COOLEY STIRLING" data-number="1"
              data-rider="Clarke Johnstone (NZL)">COOLEY STIRLING</td>
          <td></td><td></td><td></td>
          <td>Thu 10:25</td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


class EventingScoresParseTests(unittest.TestCase):
    def test_blenheim_boards_cover_eight_nine_yo_and_cci4_long(self):
        boards = blenheim_sep_2026_boards()
        self.assertEqual(
            [board.level for board in boards],
            ["CCI4*-S", "CCI4*-L"],
        )
        self.assertTrue(boards[0].url.endswith("69244.html?eventid=2990"))
        self.assertTrue(boards[1].url.endswith("69243.html?eventid=2990"))

    def test_numeric_dressage_rows_are_ingested_and_start_times_skipped(self):
        board = EventingScoresBoard(
            url="https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69244.html?eventid=2990",
            event_name="Blenheim · CCI4*-S 8/9YO",
            level="CCI4*-S",
            event_date=date(2026, 9, 17),
            country="GBR",
        )
        results = parse_leaderboard_results(
            SAMPLE_EIGHT_NINE_YO_HTML,
            board=board,
            collected_at=datetime(2026, 9, 17, 8, 24, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 2)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Tom McEwen (GBR)")
        self.assertEqual(leader.horse_name, "BROOKFIELD DANNY DE MUZE")
        self.assertEqual(leader.dressage_score, 27.2)
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(leader.cross_country_time_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 27.2)
        self.assertEqual(leader.source_id, "eventingscores")
        self.assertEqual(leader.event_name, "Blenheim · CCI4*-S 8/9YO")

        second = results[1]
        self.assertEqual(second.horse_name, "CHAKITA")
        self.assertEqual(second.dressage_score, 35.1)
        self.assertEqual(second.show_jumping_penalties, 4.0)
        self.assertEqual(second.cross_country_time_penalties, 0.0)
        self.assertEqual(second.cross_country_jump_penalties, 0.0)
        self.assertEqual(second.finishing_score, 39.1)

        horses = {result.horse_name for result in results}
        self.assertNotIn("CLIMATE CHANGE", horses)

    def test_start_list_only_cci4_long_board_yields_no_results(self):
        board = EventingScoresBoard(
            url="https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69243.html?eventid=2990",
            event_name="Blenheim · CCI4*-L",
            level="CCI4*-L",
            event_date=date(2026, 9, 17),
            country="GBR",
        )
        results = parse_leaderboard_results(SAMPLE_CCI4_LONG_START_LIST_HTML, board=board)
        self.assertEqual(results, [])

    def test_friday_numeric_dressage_is_ingested_and_remaining_start_times_skipped(self):
        board = EventingScoresBoard(
            url="https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69244.html?eventid=2990",
            event_name="Blenheim · CCI4*-S 8/9YO",
            level="CCI4*-S",
            event_date=date(2026, 9, 17),
            country="GBR",
        )
        html = """
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>No</th><th></th><th>Rider</th><th>Horse</th>
          <th>M %</th><th>C %</th><th>E %</th><th>Dressage</th>
          <th>SJ</th><th>XCT</th><th>XCJ</th><th>Total</th><th>Place</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>160</td>
          <td></td>
          <td>Ginny Howe (GBR)</td>
          <td data-horse="CHF CAPTAIN JACOB" data-number="160"
              data-rider="Ginny Howe (GBR)">CHF CAPTAIN JACOB</td>
          <td class="score">56.04%</td>
          <td class="score">59.17%</td>
          <td class="score">59.38%</td>
          <td class="score">41.7</td>
          <td></td><td></td><td></td><td class="score">41.7</td><td></td>
        </tr>
        <tr>
          <td>161</td>
          <td></td>
          <td>Mina Saiagh (FRA)</td>
          <td data-horse="OFF-WHITE ISAIE SAINT JEAN AA" data-number="161"
              data-rider="Mina Saiagh (FRA)">OFF-WHITE ISAIE SAINT JEAN AA</td>
          <td></td><td></td><td></td>
          <td>Fri 09:06</td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        results = parse_leaderboard_results(
            html,
            board=board,
            collected_at=datetime(2026, 9, 18, 8, 5, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 1)
        first = results[0]
        self.assertEqual(first.rider_name, "Ginny Howe (GBR)")
        self.assertEqual(first.horse_name, "CHF CAPTAIN JACOB")
        self.assertEqual(first.dressage_score, 41.7)
        self.assertEqual(first.finishing_score, 41.7)
        self.assertEqual(first.source_id, "eventingscores")
        self.assertNotIn("OFF-WHITE ISAIE SAINT JEAN AA", {result.horse_name for result in results})

    def test_later_friday_numeric_dressage_is_ingested_and_break_start_times_skipped(self):
        board = EventingScoresBoard(
            url="https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69244.html?eventid=2990",
            event_name="Blenheim · CCI4*-S 8/9YO",
            level="CCI4*-S",
            event_date=date(2026, 9, 17),
            country="GBR",
        )
        html = """
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>No</th><th></th><th>Rider</th><th>Horse</th>
          <th>M %</th><th>C %</th><th>E %</th><th>Dressage</th>
          <th>SJ</th><th>XCT</th><th>XCJ</th><th>Total</th><th>Place</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>165</td>
          <td></td>
          <td>Rosalind Canter (GBR)</td>
          <td data-horse="ARMSCOTE EXPLORER" data-number="165"
              data-rider="Rosalind Canter (GBR)">ARMSCOTE EXPLORER</td>
          <td class="score">68.54%</td>
          <td class="score">70.00%</td>
          <td class="score">69.38%</td>
          <td class="score">30.7</td>
          <td></td><td></td><td></td><td class="score">30.7</td><td>9th</td>
        </tr>
        <tr>
          <td>164</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="SHANNONDALE ARNOLD" data-number="164"
              data-rider="Tom McEwen (GBR)">SHANNONDALE ARNOLD</td>
          <td class="score">67.29%</td>
          <td class="score">67.92%</td>
          <td class="score">66.04%</td>
          <td class="score">32.9</td>
          <td></td><td></td><td></td><td class="score">32.9</td><td></td>
        </tr>
        <tr>
          <td>171</td>
          <td></td>
          <td>Pia Leuwer (GER)</td>
          <td data-horse="HANAMI 4" data-number="171"
              data-rider="Pia Leuwer (GER)">HANAMI 4</td>
          <td></td><td></td><td></td>
          <td>Fri 10:25</td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        results = parse_leaderboard_results(
            html,
            board=board,
            collected_at=datetime(2026, 9, 18, 9, 6, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 2)
        by_horse = {result.horse_name: result for result in results}
        self.assertEqual(by_horse["ARMSCOTE EXPLORER"].rider_name, "Rosalind Canter (GBR)")
        self.assertEqual(by_horse["ARMSCOTE EXPLORER"].dressage_score, 30.7)
        self.assertEqual(by_horse["ARMSCOTE EXPLORER"].finishing_score, 30.7)
        self.assertEqual(by_horse["SHANNONDALE ARNOLD"].dressage_score, 32.9)
        self.assertNotIn("HANAMI 4", by_horse)

    def test_post_break_friday_numeric_dressage_is_ingested_and_remaining_start_times_skipped(self):
        eight_nine_board = EventingScoresBoard(
            url="https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69244.html?eventid=2990",
            event_name="Blenheim · CCI4*-S 8/9YO",
            level="CCI4*-S",
            event_date=date(2026, 9, 17),
            country="GBR",
        )
        eight_nine_html = """
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>No</th><th></th><th>Rider</th><th>Horse</th>
          <th>M %</th><th>C %</th><th>E %</th><th>Dressage</th>
          <th>SJ</th><th>XCT</th><th>XCJ</th><th>Total</th><th>Place</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>173</td>
          <td></td>
          <td>Izzy Taylor (GBR)</td>
          <td data-horse="BARRINGTON BOY" data-number="173"
              data-rider="Izzy Taylor (GBR)">BARRINGTON BOY</td>
          <td class="score">73.75%</td>
          <td class="score">71.46%</td>
          <td class="score">72.71%</td>
          <td class="score">27.4</td>
          <td></td><td></td><td></td><td class="score">27.4</td><td>2nd</td>
        </tr>
        <tr>
          <td>171</td>
          <td></td>
          <td>Pia Leuwer (GER)</td>
          <td data-horse="HANAMI 4" data-number="171"
              data-rider="Pia Leuwer (GER)">HANAMI 4</td>
          <td class="score">67.29%</td>
          <td class="score">66.46%</td>
          <td class="score">66.88%</td>
          <td class="score">33.1</td>
          <td></td><td></td><td></td><td class="score">33.1</td><td></td>
        </tr>
        <tr>
          <td>178</td>
          <td></td>
          <td>Bubby Upton (GBR)</td>
          <td data-horse="AUCKLAND 7" data-number="178"
              data-rider="Bubby Upton (GBR)">AUCKLAND 7</td>
          <td></td><td></td><td></td>
          <td>Fri 11:07</td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        eight_nine_results = parse_leaderboard_results(
            eight_nine_html,
            board=eight_nine_board,
            collected_at=datetime(2026, 9, 18, 10, 4, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 2)
        self.assertEqual(eight_nine_by_horse["BARRINGTON BOY"].rider_name, "Izzy Taylor (GBR)")
        self.assertEqual(eight_nine_by_horse["BARRINGTON BOY"].dressage_score, 27.4)
        self.assertEqual(eight_nine_by_horse["BARRINGTON BOY"].finishing_score, 27.4)
        self.assertEqual(eight_nine_by_horse["HANAMI 4"].dressage_score, 33.1)
        self.assertNotIn("AUCKLAND 7", eight_nine_by_horse)

        cci4_board = EventingScoresBoard(
            url="https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69243.html?eventid=2990",
            event_name="Blenheim · CCI4*-L",
            level="CCI4*-L",
            event_date=date(2026, 9, 17),
            country="GBR",
        )
        cci4_html = """
<html>
  <body>
    <table>
      <thead>
        <tr>
          <th>No</th><th></th><th>Rider</th><th>Horse</th>
          <th>M %</th><th>C %</th><th>E %</th><th>Dressage</th>
          <th>XCT</th><th>XCJ</th><th>SJ</th><th>Total</th><th>Place</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>52</td>
          <td></td>
          <td>Alexandre D’Orso (FRA)</td>
          <td data-horse="CANON ST MARTIN" data-number="52"
              data-rider="Alexandre D’Orso (FRA)">CANON ST MARTIN</td>
          <td class="score">67.08%</td>
          <td class="score">66.88%</td>
          <td class="score">67.08%</td>
          <td class="score">33.0</td>
          <td></td><td></td><td></td><td class="score">33.0</td><td></td>
        </tr>
        <tr>
          <td>59</td>
          <td></td>
          <td>John Westmore (GBR)</td>
          <td data-horse="OUGHTERARD QUALITY" data-number="59"
              data-rider="John Westmore (GBR)">OUGHTERARD QUALITY</td>
          <td></td><td></td><td></td>
          <td>Fri 11:07</td>
          <td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 18, 10, 4, tzinfo=timezone.utc),
        )
        self.assertEqual(len(cci4_results), 1)
        self.assertEqual(cci4_results[0].rider_name, "Alexandre D’Orso (FRA)")
        self.assertEqual(cci4_results[0].horse_name, "CANON ST MARTIN")
        self.assertEqual(cci4_results[0].dressage_score, 33.0)
        self.assertEqual(cci4_results[0].finishing_score, 33.0)
        self.assertNotIn("OUGHTERARD QUALITY", {result.horse_name for result in cci4_results})


if __name__ == "__main__":
    unittest.main()
