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

    def test_saturday_compound_show_jumping_penalties_are_summed(self):
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
          <td>101</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD DANNY DE MUZE" data-number="101"
              data-rider="Tom McEwen (GBR)">BROOKFIELD DANNY DE MUZE</td>
          <td></td><td></td><td></td>
          <td class="score">27.2</td>
          <td class="score">0</td>
          <td>Sat 07:50</td><td></td>
          <td class="score">27.2</td>
          <td></td>
        </tr>
        <tr>
          <td>105</td>
          <td></td>
          <td>Kirsty Chabert (GBR)</td>
          <td data-horse="CLIMATE CHANGE" data-number="105"
              data-rider="Kirsty Chabert (GBR)">CLIMATE CHANGE</td>
          <td></td><td></td><td></td>
          <td class="score">30.8</td>
          <td class="score">4 + 0.4</td>
          <td></td><td></td>
          <td class="score">35.2</td>
          <td></td>
        </tr>
        <tr>
          <td>160</td>
          <td></td>
          <td>Piggy March (GBR)</td>
          <td data-horse="VANIR KAMIRA" data-number="160"
              data-rider="Piggy March (GBR)">VANIR KAMIRA</td>
          <td></td><td></td><td></td>
          <td>Sat 10:51</td>
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
            collected_at=datetime(2026, 9, 19, 7, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 2)
        by_horse = {result.horse_name: result for result in results}
        clear = by_horse["BROOKFIELD DANNY DE MUZE"]
        self.assertEqual(clear.show_jumping_penalties, 0.0)
        self.assertEqual(clear.finishing_score, 27.2)
        rails_and_time = by_horse["CLIMATE CHANGE"]
        self.assertEqual(rails_and_time.show_jumping_penalties, 4.4)
        self.assertEqual(rails_and_time.finishing_score, 35.2)
        self.assertNotIn("VANIR KAMIRA", by_horse)

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

    def test_post_1107_friday_numeric_dressage_is_ingested_and_lunch_start_times_skipped(self):
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
          <td>178</td>
          <td></td>
          <td>Bubby Upton (GBR)</td>
          <td data-horse="AUCKLAND 7" data-number="178"
              data-rider="Bubby Upton (GBR)">AUCKLAND 7</td>
          <td class="score">73.75%</td>
          <td class="score">72.71%</td>
          <td class="score">73.13%</td>
          <td class="score">26.9</td>
          <td></td><td></td><td></td><td class="score">26.9</td><td>1st</td>
        </tr>
        <tr>
          <td>181</td>
          <td></td>
          <td>Hazel Towers (GBR)</td>
          <td data-horse="TORPEX" data-number="181"
              data-rider="Hazel Towers (GBR)">TORPEX</td>
          <td class="score">70.42%</td>
          <td class="score">71.25%</td>
          <td class="score">71.04%</td>
          <td class="score">29.1</td>
          <td></td><td></td><td></td><td class="score">29.1</td><td></td>
        </tr>
        <tr>
          <td>187</td>
          <td></td>
          <td>India Wishart (GBR)</td>
          <td data-horse="HHS GOING COOLEY" data-number="187"
              data-rider="India Wishart (GBR)">HHS GOING COOLEY</td>
          <td></td><td></td><td></td>
          <td>Fri 12:07</td>
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
            collected_at=datetime(2026, 9, 18, 11, 5, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 2)
        self.assertEqual(eight_nine_by_horse["AUCKLAND 7"].rider_name, "Bubby Upton (GBR)")
        self.assertEqual(eight_nine_by_horse["AUCKLAND 7"].dressage_score, 26.9)
        self.assertEqual(eight_nine_by_horse["AUCKLAND 7"].finishing_score, 26.9)
        self.assertEqual(eight_nine_by_horse["TORPEX"].dressage_score, 29.1)
        self.assertNotIn("HHS GOING COOLEY", eight_nine_by_horse)

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
          <td>59</td>
          <td></td>
          <td>John Westmore (GBR)</td>
          <td data-horse="OUGHTERARD QUALITY" data-number="59"
              data-rider="John Westmore (GBR)">OUGHTERARD QUALITY</td>
          <td class="score">69.79%</td>
          <td class="score">69.38%</td>
          <td class="score">69.17%</td>
          <td class="score">30.6</td>
          <td></td><td></td><td></td><td class="score">30.6</td><td></td>
        </tr>
        <tr>
          <td>65</td>
          <td></td>
          <td>Alicia Wilkinson (GBR)</td>
          <td data-horse="CHILLI BILL" data-number="65"
              data-rider="Alicia Wilkinson (GBR)">CHILLI BILL</td>
          <td></td><td></td><td></td>
          <td>Fri 12:07</td>
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
            collected_at=datetime(2026, 9, 18, 11, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(len(cci4_results), 1)
        self.assertEqual(cci4_results[0].rider_name, "John Westmore (GBR)")
        self.assertEqual(cci4_results[0].horse_name, "OUGHTERARD QUALITY")
        self.assertEqual(cci4_results[0].dressage_score, 30.6)
        self.assertEqual(cci4_results[0].finishing_score, 30.6)
        self.assertNotIn("CHILLI BILL", {result.horse_name for result in cci4_results})

    def test_post_1207_friday_numeric_dressage_is_ingested_and_1430_start_times_skipped(self):
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
          <td>193</td>
          <td></td>
          <td>Tom Jackson (GBR)</td>
          <td data-horse="MY STAR TURN" data-number="193"
              data-rider="Tom Jackson (GBR)">MY STAR TURN</td>
          <td class="score">71.04%</td>
          <td class="score">70.00%</td>
          <td class="score">71.46%</td>
          <td class="score">29.2</td>
          <td></td><td></td><td></td><td class="score">29.2</td><td>7th</td>
        </tr>
        <tr>
          <td>185</td>
          <td></td>
          <td>India Wishart (GBR)</td>
          <td data-horse="HHS GOING COOLEY" data-number="185"
              data-rider="India Wishart (GBR)">HHS GOING COOLEY</td>
          <td class="score">65.42%</td>
          <td class="score">63.96%</td>
          <td class="score">65.83%</td>
          <td class="score">34.9</td>
          <td></td><td></td><td></td><td class="score">34.9</td><td></td>
        </tr>
        <tr>
          <td>194</td>
          <td></td>
          <td>Jack Pinkney (GBR)</td>
          <td data-horse="AYRTON SENNA" data-number="194"
              data-rider="Jack Pinkney (GBR)">AYRTON SENNA</td>
          <td></td><td></td><td></td>
          <td>Fri 14:30</td>
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
            collected_at=datetime(2026, 9, 18, 12, 5, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 2)
        self.assertEqual(eight_nine_by_horse["MY STAR TURN"].rider_name, "Tom Jackson (GBR)")
        self.assertEqual(eight_nine_by_horse["MY STAR TURN"].dressage_score, 29.2)
        self.assertEqual(eight_nine_by_horse["MY STAR TURN"].finishing_score, 29.2)
        self.assertEqual(eight_nine_by_horse["HHS GOING COOLEY"].dressage_score, 34.9)
        self.assertNotIn("AYRTON SENNA", eight_nine_by_horse)

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
          <td>60</td>
          <td></td>
          <td>Jesse Campbell (NZL)</td>
          <td data-horse="SPEEDWELL" data-number="60"
              data-rider="Jesse Campbell (NZL)">SPEEDWELL</td>
          <td class="score">73.75%</td>
          <td class="score">70.21%</td>
          <td class="score">77.50%</td>
          <td class="score">26.2</td>
          <td></td><td></td><td></td><td class="score">26.2</td><td>2nd</td>
        </tr>
        <tr>
          <td>54</td>
          <td></td>
          <td>Alicia Wilkinson (GBR)</td>
          <td data-horse="CHILLI BILL" data-number="54"
              data-rider="Alicia Wilkinson (GBR)">CHILLI BILL</td>
          <td class="score">57.29%</td>
          <td class="score">59.38%</td>
          <td class="score">54.79%</td>
          <td class="score">42.9</td>
          <td></td><td></td><td></td><td class="score">42.9</td><td></td>
        </tr>
        <tr>
          <td>62</td>
          <td></td>
          <td>Jessica McKie (GBR)</td>
          <td data-horse="JUNGLE KING" data-number="62"
              data-rider="Jessica McKie (GBR)">JUNGLE KING</td>
          <td></td><td></td><td></td>
          <td>Fri 14:30</td>
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
            collected_at=datetime(2026, 9, 18, 12, 5, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 2)
        self.assertEqual(cci4_by_horse["SPEEDWELL"].rider_name, "Jesse Campbell (NZL)")
        self.assertEqual(cci4_by_horse["SPEEDWELL"].dressage_score, 26.2)
        self.assertEqual(cci4_by_horse["SPEEDWELL"].finishing_score, 26.2)
        self.assertEqual(cci4_by_horse["CHILLI BILL"].dressage_score, 42.9)
        self.assertNotIn("JUNGLE KING", cci4_by_horse)

    def test_post_1430_friday_numeric_dressage_is_ingested_and_remaining_start_times_skipped(self):
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
          <td>196</td>
          <td></td>
          <td>Regis Prudhon (FRA)</td>
          <td data-horse="BLACK SWAN DECANDIE Z" data-number="196"
              data-rider="Regis Prudhon (FRA)">BLACK SWAN DECANDIE Z</td>
          <td class="score">70.00%</td>
          <td class="score">69.79%</td>
          <td class="score">70.00%</td>
          <td class="score">30.1</td>
          <td></td><td></td><td></td><td class="score">30.1</td><td></td>
        </tr>
        <tr>
          <td>195</td>
          <td></td>
          <td>Alexandra Knowles (USA)</td>
          <td data-horse="LS CROWN ROYAL" data-number="195"
              data-rider="Alexandra Knowles (USA)">LS CROWN ROYAL</td>
          <td class="score">69.17%</td>
          <td class="score">68.75%</td>
          <td class="score">69.17%</td>
          <td class="score">31.0</td>
          <td></td><td></td><td></td><td class="score">31.0</td><td></td>
        </tr>
        <tr>
          <td>194</td>
          <td></td>
          <td>Jack Pinkney (GBR)</td>
          <td data-horse="AYRTON SENNA" data-number="194"
              data-rider="Jack Pinkney (GBR)">AYRTON SENNA</td>
          <td class="score">64.17%</td>
          <td class="score">64.58%</td>
          <td class="score">63.96%</td>
          <td class="score">35.7</td>
          <td></td><td></td><td></td><td class="score">35.7</td><td></td>
        </tr>
        <tr>
          <td>197</td>
          <td></td>
          <td>John Tilley (GBR)</td>
          <td data-horse="COOLEY QUICKFIRE" data-number="197"
              data-rider="John Tilley (GBR)">COOLEY QUICKFIRE</td>
          <td class="score">63.13%</td>
          <td class="score">63.75%</td>
          <td class="score">63.33%</td>
          <td class="score">36.6</td>
          <td></td><td></td><td></td><td class="score">36.6</td><td></td>
        </tr>
        <tr>
          <td>198</td>
          <td></td>
          <td>Laura Collett (GBR)</td>
          <td data-horse="ROMANY CRICKET" data-number="198"
              data-rider="Laura Collett (GBR)">ROMANY CRICKET</td>
          <td></td><td></td><td></td>
          <td>Fri 14:54</td>
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
            collected_at=datetime(2026, 9, 18, 13, 52, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 4)
        self.assertEqual(eight_nine_by_horse["BLACK SWAN DECANDIE Z"].rider_name, "Regis Prudhon (FRA)")
        self.assertEqual(eight_nine_by_horse["BLACK SWAN DECANDIE Z"].dressage_score, 30.1)
        self.assertEqual(eight_nine_by_horse["LS CROWN ROYAL"].dressage_score, 31.0)
        self.assertEqual(eight_nine_by_horse["AYRTON SENNA"].dressage_score, 35.7)
        self.assertEqual(eight_nine_by_horse["COOLEY QUICKFIRE"].dressage_score, 36.6)
        self.assertNotIn("ROMANY CRICKET", eight_nine_by_horse)

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
          <td>63</td>
          <td></td>
          <td>Zara Tindall (GBR)</td>
          <td data-horse="CLASSICALS EURO STAR" data-number="63"
              data-rider="Zara Tindall (GBR)">CLASSICALS EURO STAR</td>
          <td class="score">68.54%</td>
          <td class="score">68.33%</td>
          <td class="score">68.75%</td>
          <td class="score">31.5</td>
          <td></td><td></td><td></td><td class="score">31.5</td><td>8th</td>
        </tr>
        <tr>
          <td>64</td>
          <td></td>
          <td>Kelli Frewin (NZL)</td>
          <td data-horse="HIDDEN GOLD" data-number="64"
              data-rider="Kelli Frewin (NZL)">HIDDEN GOLD</td>
          <td class="score">64.17%</td>
          <td class="score">64.38%</td>
          <td class="score">64.17%</td>
          <td class="score">35.8</td>
          <td></td><td></td><td></td><td class="score">35.8</td><td></td>
        </tr>
        <tr>
          <td>65</td>
          <td></td>
          <td>Jemima Stratton (GBR)</td>
          <td data-horse="GLOBAL EXOTIC" data-number="65"
              data-rider="Jemima Stratton (GBR)">GLOBAL EXOTIC</td>
          <td class="score">63.13%</td>
          <td class="score">63.33%</td>
          <td class="score">62.71%</td>
          <td class="score">36.9</td>
          <td></td><td></td><td></td><td class="score">36.9</td><td></td>
        </tr>
        <tr>
          <td>62</td>
          <td></td>
          <td>Jessica McKie (GBR)</td>
          <td data-horse="JUNGLE KING" data-number="62"
              data-rider="Jessica McKie (GBR)">JUNGLE KING</td>
          <td class="score">59.38%</td>
          <td class="score">59.58%</td>
          <td class="score">59.17%</td>
          <td class="score">40.6</td>
          <td></td><td></td><td></td><td class="score">40.6</td><td></td>
        </tr>
        <tr>
          <td>66</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD QUALITY" data-number="66"
              data-rider="Tom McEwen (GBR)">BROOKFIELD QUALITY</td>
          <td></td><td></td><td></td>
          <td>Fri 14:54</td>
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
            collected_at=datetime(2026, 9, 18, 13, 52, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 4)
        self.assertEqual(cci4_by_horse["CLASSICALS EURO STAR"].rider_name, "Zara Tindall (GBR)")
        self.assertEqual(cci4_by_horse["CLASSICALS EURO STAR"].dressage_score, 31.5)
        self.assertEqual(cci4_by_horse["HIDDEN GOLD"].dressage_score, 35.8)
        self.assertEqual(cci4_by_horse["GLOBAL EXOTIC"].dressage_score, 36.9)
        self.assertEqual(cci4_by_horse["JUNGLE KING"].dressage_score, 40.6)
        self.assertNotIn("BROOKFIELD QUALITY", cci4_by_horse)

    def test_late_friday_numeric_dressage_is_ingested_and_1607_start_times_skipped(self):
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
          <td>200</td>
          <td></td>
          <td>Katie Magee (GBR)</td>
          <td data-horse="CUSHLAS INDIGO" data-number="200"
              data-rider="Katie Magee (GBR)">CUSHLAS INDIGO</td>
          <td class="score">71.04%</td>
          <td class="score">71.67%</td>
          <td class="score">72.08%</td>
          <td class="score">28.4</td>
          <td>Sat 10:29</td><td></td><td></td><td class="score">28.4</td><td>5th</td>
        </tr>
        <tr>
          <td>206</td>
          <td></td>
          <td>Jonelle Price (NZL)</td>
          <td data-horse="FAERIE GOOD GOLLY" data-number="206"
              data-rider="Jonelle Price (NZL)">FAERIE GOOD GOLLY</td>
          <td class="score">69.58%</td>
          <td class="score">67.29%</td>
          <td class="score">68.33%</td>
          <td class="score">31.6</td>
          <td>Sat 10:40</td><td></td><td></td><td class="score">31.6</td><td>20th</td>
        </tr>
        <tr>
          <td>198</td>
          <td></td>
          <td>Laura Collett (GBR)</td>
          <td data-horse="ROMANY CRICKET" data-number="198"
              data-rider="Laura Collett (GBR)">ROMANY CRICKET</td>
          <td class="score">65.21%</td>
          <td class="score">65.42%</td>
          <td class="score">66.25%</td>
          <td class="score">34.4</td>
          <td>Sat 10:26</td><td></td><td></td><td class="score">34.4</td><td>36th</td>
        </tr>
        <tr>
          <td>199</td>
          <td></td>
          <td>Katey Cuthbertson (GBR)</td>
          <td data-horse="PERCIVALE" data-number="199"
              data-rider="Katey Cuthbertson (GBR)">PERCIVALE</td>
          <td class="score">58.13%</td>
          <td class="score">56.67%</td>
          <td class="score">55.21%</td>
          <td class="score">43.3</td>
          <td>Sat 10:27</td><td></td><td></td><td class="score">43.3</td><td>85th</td>
        </tr>
        <tr>
          <td>207</td>
          <td></td>
          <td>Padraig Mccarthy (IRL)</td>
          <td data-horse="KILROE TIGER" data-number="207"
              data-rider="Padraig Mccarthy (IRL)">KILROE TIGER</td>
          <td></td><td></td><td></td>
          <td>Fri 16:07</td>
          <td>Sat 10:42</td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        eight_nine_results = parse_leaderboard_results(
            eight_nine_html,
            board=eight_nine_board,
            collected_at=datetime(2026, 9, 18, 15, 10, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 4)
        self.assertEqual(eight_nine_by_horse["CUSHLAS INDIGO"].rider_name, "Katie Magee (GBR)")
        self.assertEqual(eight_nine_by_horse["CUSHLAS INDIGO"].dressage_score, 28.4)
        self.assertEqual(eight_nine_by_horse["CUSHLAS INDIGO"].finishing_score, 28.4)
        self.assertEqual(eight_nine_by_horse["FAERIE GOOD GOLLY"].dressage_score, 31.6)
        self.assertEqual(eight_nine_by_horse["ROMANY CRICKET"].dressage_score, 34.4)
        self.assertEqual(eight_nine_by_horse["PERCIVALE"].dressage_score, 43.3)
        self.assertNotIn("KILROE TIGER", eight_nine_by_horse)

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
          <td>66</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD QUALITY" data-number="66"
              data-rider="Tom McEwen (GBR)">BROOKFIELD QUALITY</td>
          <td class="score">73.75%</td>
          <td class="score">73.33%</td>
          <td class="score">73.33%</td>
          <td class="score">26.5</td>
          <td>Sat 15:38</td><td></td><td></td><td class="score">26.5</td><td>3rd</td>
        </tr>
        <tr>
          <td>68</td>
          <td></td>
          <td>Clarke Johnstone (NZL)</td>
          <td data-horse="SPARKY LAD" data-number="68"
              data-rider="Clarke Johnstone (NZL)">SPARKY LAD</td>
          <td class="score">72.92%</td>
          <td class="score">68.13%</td>
          <td class="score">68.96%</td>
          <td class="score">30.0</td>
          <td>Sat 15:42</td><td></td><td></td><td class="score">30</td><td>6th</td>
        </tr>
        <tr>
          <td>72</td>
          <td></td>
          <td>Christine Bates (AUS)</td>
          <td data-horse="BLOOMFIELD FINDON" data-number="72"
              data-rider="Christine Bates (AUS)">BLOOMFIELD FINDON</td>
          <td class="score">70.21%</td>
          <td class="score">67.92%</td>
          <td class="score">64.79%</td>
          <td class="score">32.4</td>
          <td>Sat 15:57</td><td></td><td></td><td class="score">32.4</td><td>17th</td>
        </tr>
        <tr>
          <td>69</td>
          <td></td>
          <td>Izzy Taylor (GBR)</td>
          <td data-horse="BARRINGTON REVELATION" data-number="69"
              data-rider="Izzy Taylor (GBR)">BARRINGTON REVELATION</td>
          <td class="score">61.88%</td>
          <td class="score">60.83%</td>
          <td class="score">57.71%</td>
          <td class="score">39.9</td>
          <td>Sat 15:46</td><td></td><td></td><td class="score">39.9</td><td>53rd</td>
        </tr>
        <tr>
          <td>74</td>
          <td></td>
          <td>Alexander Bragg (GBR)</td>
          <td data-horse="SHANNONDALE ALDO" data-number="74"
              data-rider="Alexander Bragg (GBR)">SHANNONDALE ALDO</td>
          <td></td><td></td><td></td>
          <td>Fri 16:07</td>
          <td>Sat 16:04</td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 18, 15, 10, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 4)
        self.assertEqual(cci4_by_horse["BROOKFIELD QUALITY"].rider_name, "Tom McEwen (GBR)")
        self.assertEqual(cci4_by_horse["BROOKFIELD QUALITY"].dressage_score, 26.5)
        self.assertEqual(cci4_by_horse["BROOKFIELD QUALITY"].finishing_score, 26.5)
        self.assertEqual(cci4_by_horse["SPARKY LAD"].dressage_score, 30.0)
        self.assertEqual(cci4_by_horse["BLOOMFIELD FINDON"].dressage_score, 32.4)
        self.assertEqual(cci4_by_horse["BARRINGTON REVELATION"].dressage_score, 39.9)
        self.assertNotIn("SHANNONDALE ALDO", cci4_by_horse)

    def test_post_1607_friday_numeric_dressage_is_ingested_and_1637_start_times_skipped(self):
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
          <td>208</td>
          <td></td>
          <td>Bubby Upton (GBR)</td>
          <td data-horse="SANCERRE DE TIJI" data-number="208"
              data-rider="Bubby Upton (GBR)">SANCERRE DE TIJI</td>
          <td class="score">73.13%</td>
          <td class="score">73.13%</td>
          <td class="score">73.13%</td>
          <td class="score">26.9</td>
          <td>Sat 10:44</td><td></td><td></td><td class="score">26.9</td><td>1st</td>
        </tr>
        <tr>
          <td>207</td>
          <td></td>
          <td>Padraig Mccarthy (IRL)</td>
          <td data-horse="KILROE TIGER" data-number="207"
              data-rider="Padraig Mccarthy (IRL)">KILROE TIGER</td>
          <td class="score">69.17%</td>
          <td class="score">68.96%</td>
          <td class="score">68.54%</td>
          <td class="score">31.1</td>
          <td>Sat 10:42</td><td></td><td></td><td class="score">31.1</td><td></td>
        </tr>
        <tr>
          <td>210</td>
          <td></td>
          <td>Gireg Le Coz (FRA)</td>
          <td data-horse="MILWAUKEE TCS" data-number="210"
              data-rider="Gireg Le Coz (FRA)">MILWAUKEE TCS</td>
          <td class="score">70.42%</td>
          <td class="score">70.21%</td>
          <td class="score">70.21%</td>
          <td class="score">29.7</td>
          <td>Sat 10:47</td><td></td><td></td><td class="score">29.7</td><td></td>
        </tr>
        <tr>
          <td>212</td>
          <td></td>
          <td>Astier Nicolas (FRA)</td>
          <td data-horse="HITCHQOTE DU COUDRAY" data-number="212"
              data-rider="Astier Nicolas (FRA)">HITCHQOTE DU COUDRAY</td>
          <td></td><td></td><td></td>
          <td>Fri 16:37</td>
          <td>Sat 10:51</td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        eight_nine_results = parse_leaderboard_results(
            eight_nine_html,
            board=eight_nine_board,
            collected_at=datetime(2026, 9, 18, 15, 33, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 3)
        self.assertEqual(eight_nine_by_horse["SANCERRE DE TIJI"].rider_name, "Bubby Upton (GBR)")
        self.assertEqual(eight_nine_by_horse["SANCERRE DE TIJI"].dressage_score, 26.9)
        self.assertEqual(eight_nine_by_horse["SANCERRE DE TIJI"].finishing_score, 26.9)
        self.assertEqual(eight_nine_by_horse["KILROE TIGER"].dressage_score, 31.1)
        self.assertEqual(eight_nine_by_horse["MILWAUKEE TCS"].dressage_score, 29.7)
        self.assertNotIn("HITCHQOTE DU COUDRAY", eight_nine_by_horse)

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
          <td>75</td>
          <td></td>
          <td>Sarah Hedges (GBR)</td>
          <td data-horse="IGNA" data-number="75"
              data-rider="Sarah Hedges (GBR)">IGNA</td>
          <td class="score">69.58%</td>
          <td class="score">69.58%</td>
          <td class="score">69.58%</td>
          <td class="score">30.4</td>
          <td>Sat 16:08</td><td></td><td></td><td class="score">30.4</td><td>8th</td>
        </tr>
        <tr>
          <td>74</td>
          <td></td>
          <td>Alexander Bragg (GBR)</td>
          <td data-horse="SHANNONDALE ALDO" data-number="74"
              data-rider="Alexander Bragg (GBR)">SHANNONDALE ALDO</td>
          <td class="score">63.33%</td>
          <td class="score">63.33%</td>
          <td class="score">63.33%</td>
          <td class="score">36.7</td>
          <td>Sat 16:04</td><td></td><td></td><td class="score">36.7</td><td></td>
        </tr>
        <tr>
          <td>77</td>
          <td></td>
          <td>Dani Stewart-Richardson (GBR)</td>
          <td data-horse="LONDONLOOK TN" data-number="77"
              data-rider="Dani Stewart-Richardson (GBR)">LONDONLOOK TN</td>
          <td class="score">69.17%</td>
          <td class="score">69.17%</td>
          <td class="score">69.38%</td>
          <td class="score">30.8</td>
          <td>Sat 16:12</td><td></td><td></td><td class="score">30.8</td><td></td>
        </tr>
        <tr>
          <td>79</td>
          <td></td>
          <td>Megan Bailey (GBR)</td>
          <td data-horse="ELECTED" data-number="79"
              data-rider="Megan Bailey (GBR)">ELECTED</td>
          <td></td><td></td><td></td>
          <td>Fri 16:37</td>
          <td>Sat 16:19</td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 18, 15, 33, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 3)
        self.assertEqual(cci4_by_horse["IGNA"].rider_name, "Sarah Hedges (GBR)")
        self.assertEqual(cci4_by_horse["IGNA"].dressage_score, 30.4)
        self.assertEqual(cci4_by_horse["SHANNONDALE ALDO"].dressage_score, 36.7)
        self.assertEqual(cci4_by_horse["LONDONLOOK TN"].dressage_score, 30.8)
        self.assertNotIn("ELECTED", cci4_by_horse)

    def test_completed_friday_dressage_is_ingested_and_withdrawals_skipped(self):
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
          <td>212</td>
          <td></td>
          <td>Astier Nicolas (FRA)</td>
          <td data-horse="HITCHQOTE DU COUDRAY" data-number="212"
              data-rider="Astier Nicolas (FRA)">HITCHQOTE DU COUDRAY</td>
          <td class="score">76.46%</td>
          <td class="score">76.46%</td>
          <td class="score">76.67%</td>
          <td class="score">23.5</td>
          <td>Sat 10:51</td><td></td><td></td><td class="score">23.5</td><td>1st</td>
        </tr>
        <tr>
          <td>214</td>
          <td></td>
          <td>Kitty King (GBR)</td>
          <td data-horse="KILCOLTRIM COOLEY" data-number="214"
              data-rider="Kitty King (GBR)">KILCOLTRIM COOLEY</td>
          <td class="score">72.29%</td>
          <td class="score">72.08%</td>
          <td class="score">72.29%</td>
          <td class="score">27.8</td>
          <td>Sat 10:55</td><td></td><td></td><td class="score">27.8</td><td></td>
        </tr>
        <tr>
          <td>215</td>
          <td></td>
          <td>Michael Jackson (GBR)</td>
          <td data-horse="GIRLS GAMBLE" data-number="215"
              data-rider="Michael Jackson (GBR)">GIRLS GAMBLE</td>
          <td class="score">69.38%</td>
          <td class="score">69.38%</td>
          <td class="score">69.38%</td>
          <td class="score">30.6</td>
          <td>Sat 10:57</td><td></td><td></td><td class="score">30.6</td><td></td>
        </tr>
        <tr>
          <td>213</td>
          <td></td>
          <td>Lara de Liedekerke-Meier (BEL)</td>
          <td data-horse="CALL ME SENORITA" data-number="213"
              data-rider="Lara de Liedekerke-Meier (BEL)">CALL ME SENORITA</td>
          <td class="score">66.04%</td>
          <td class="score">66.04%</td>
          <td class="score">65.83%</td>
          <td class="score">34.0</td>
          <td>Sat 10:53</td><td></td><td></td><td class="score">34.0</td><td></td>
        </tr>
        <tr>
          <td>211</td>
          <td></td>
          <td>Therese Viklund (SWE)</td>
          <td data-horse="HARDI D'EOLE" data-number="211"
              data-rider="Therese Viklund (SWE)">HARDI D'EOLE</td>
          <td class="score">63.13%</td>
          <td class="score">63.13%</td>
          <td class="score">63.13%</td>
          <td class="score">36.9</td>
          <td>Sat 10:49</td><td></td><td></td><td class="score">36.9</td><td></td>
        </tr>
        <tr>
          <td>154</td>
          <td></td>
          <td>India Wishart (GBR)</td>
          <td data-horse="BP QUINNTON" data-number="154"
              data-rider="India Wishart (GBR)">BP QUINNTON</td>
          <td></td><td></td><td></td>
          <td>WD</td>
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
            collected_at=datetime(2026, 9, 18, 16, 5, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 5)
        self.assertEqual(eight_nine_by_horse["HITCHQOTE DU COUDRAY"].rider_name, "Astier Nicolas (FRA)")
        self.assertEqual(eight_nine_by_horse["HITCHQOTE DU COUDRAY"].dressage_score, 23.5)
        self.assertEqual(eight_nine_by_horse["HITCHQOTE DU COUDRAY"].finishing_score, 23.5)
        self.assertEqual(eight_nine_by_horse["KILCOLTRIM COOLEY"].dressage_score, 27.8)
        self.assertEqual(eight_nine_by_horse["GIRLS GAMBLE"].dressage_score, 30.6)
        self.assertEqual(eight_nine_by_horse["CALL ME SENORITA"].dressage_score, 34.0)
        self.assertEqual(eight_nine_by_horse["HARDI D'EOLE"].dressage_score, 36.9)
        self.assertNotIn("BP QUINNTON", eight_nine_by_horse)

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
          <td>77</td>
          <td></td>
          <td>Sarah Hedges (GBR)</td>
          <td data-horse="IGNA" data-number="77"
              data-rider="Sarah Hedges (GBR)">IGNA</td>
          <td class="score">69.79%</td>
          <td class="score">70.00%</td>
          <td class="score">69.79%</td>
          <td class="score">30.1</td>
          <td>Sat 16:16</td><td></td><td></td><td class="score">30.1</td><td>7th</td>
        </tr>
        <tr>
          <td>80</td>
          <td></td>
          <td>Samuel Jeffree (AUS)</td>
          <td data-horse="SANTORO" data-number="80"
              data-rider="Samuel Jeffree (AUS)">SANTORO</td>
          <td class="score">65.00%</td>
          <td class="score">65.00%</td>
          <td class="score">65.00%</td>
          <td class="score">35.0</td>
          <td>Sat 16:27</td><td></td><td></td><td class="score">35.0</td><td></td>
        </tr>
        <tr>
          <td>78</td>
          <td></td>
          <td>Alice Casburn (GBR)</td>
          <td data-horse="LSS ILE DE RE" data-number="78"
              data-rider="Alice Casburn (GBR)">LSS ILE DE RE</td>
          <td class="score">64.17%</td>
          <td class="score">63.96%</td>
          <td class="score">63.96%</td>
          <td class="score">36.0</td>
          <td>Sat 16:19</td><td></td><td></td><td class="score">36.0</td><td></td>
        </tr>
        <tr>
          <td>79</td>
          <td></td>
          <td>Megan Bailey (GBR)</td>
          <td data-horse="ELECTED" data-number="79"
              data-rider="Megan Bailey (GBR)">ELECTED</td>
          <td class="score">62.08%</td>
          <td class="score">61.88%</td>
          <td class="score">62.08%</td>
          <td class="score">38.0</td>
          <td>Sat 16:23</td><td></td><td></td><td class="score">38.0</td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 18, 16, 5, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 4)
        self.assertEqual(cci4_by_horse["IGNA"].rider_name, "Sarah Hedges (GBR)")
        self.assertEqual(cci4_by_horse["IGNA"].dressage_score, 30.1)
        self.assertEqual(cci4_by_horse["IGNA"].finishing_score, 30.1)
        self.assertEqual(cci4_by_horse["SANTORO"].dressage_score, 35.0)
        self.assertEqual(cci4_by_horse["LSS ILE DE RE"].dressage_score, 36.0)
        self.assertEqual(cci4_by_horse["ELECTED"].dressage_score, 38.0)


if __name__ == "__main__":
    unittest.main()
