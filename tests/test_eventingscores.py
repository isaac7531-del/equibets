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

    def test_saturday_morning_show_jumping_wave_keeps_start_times_and_status(self):
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
          <td>212</td>
          <td></td>
          <td>Astier Nicolas (FRA)</td>
          <td data-horse="HITCHQOTE DU COUDRAY" data-number="212"
              data-rider="Astier Nicolas (FRA)">HITCHQOTE DU COUDRAY</td>
          <td></td><td></td><td></td>
          <td class="score">23.5</td>
          <td>Sat 10:51</td><td></td><td></td>
          <td class="score">23.5</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>118</td>
          <td></td>
          <td>Isabel English (AUS)</td>
          <td data-horse="CIL DARA BOMBAY S" data-number="118"
              data-rider="Isabel English (AUS)">CIL DARA BOMBAY S</td>
          <td></td><td></td><td></td>
          <td class="score">30.2</td>
          <td class="score">0 + 0.4</td>
          <td></td><td></td>
          <td class="score">30.6</td>
          <td></td>
        </tr>
        <tr>
          <td>142</td>
          <td></td>
          <td>Sammi Birch (AUS)</td>
          <td data-horse="MBF QUIDAMS TOUCH" data-number="142"
              data-rider="Sammi Birch (AUS)">MBF QUIDAMS TOUCH</td>
          <td></td><td></td><td></td>
          <td class="score">34.4</td>
          <td class="score">4 + 1.6</td>
          <td></td><td></td>
          <td class="score">40.0</td>
          <td></td>
        </tr>
        <tr>
          <td>151</td>
          <td></td>
          <td>Lara de Liedekerke-Meier (BEL)</td>
          <td data-horse="LA LA LAND D'ARVILLE" data-number="151"
              data-rider="Lara de Liedekerke-Meier (BEL)">LA LA LAND D'ARVILLE</td>
          <td></td><td></td><td></td>
          <td class="score">34.2</td>
          <td class="score">8</td>
          <td></td><td></td>
          <td class="score">42.2</td>
          <td></td>
        </tr>
        <tr>
          <td>133</td>
          <td></td>
          <td>Max Warburton (GBR)</td>
          <td data-horse="PRIMITIVE FUNTIME" data-number="133"
              data-rider="Max Warburton (GBR)">PRIMITIVE FUNTIME</td>
          <td></td><td></td><td></td>
          <td class="score">36.1</td>
          <td>EL</td><td></td><td></td>
          <td></td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        results = parse_leaderboard_results(
            html,
            board=board,
            collected_at=datetime(2026, 9, 19, 8, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 5)
        by_horse = {result.horse_name: result for result in results}
        leader = by_horse["HITCHQOTE DU COUDRAY"]
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 23.5)
        time_only = by_horse["CIL DARA BOMBAY S"]
        self.assertEqual(time_only.show_jumping_penalties, 0.4)
        self.assertEqual(time_only.finishing_score, 30.6)
        rails_and_time = by_horse["MBF QUIDAMS TOUCH"]
        self.assertEqual(rails_and_time.show_jumping_penalties, 5.6)
        self.assertEqual(rails_and_time.finishing_score, 40.0)
        rails_only = by_horse["LA LA LAND D'ARVILLE"]
        self.assertEqual(rails_only.show_jumping_penalties, 8.0)
        self.assertEqual(rails_only.finishing_score, 42.2)
        eliminated = by_horse["PRIMITIVE FUNTIME"]
        self.assertEqual(eliminated.show_jumping_penalties, 0.0)
        self.assertEqual(eliminated.finishing_score, 36.1)

    def test_saturday_09utc_show_jumping_wave_keeps_start_times_and_status(self):
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
          <td>212</td>
          <td></td>
          <td>Astier Nicolas (FRA)</td>
          <td data-horse="HITCHQOTE DU COUDRAY" data-number="212"
              data-rider="Astier Nicolas (FRA)">HITCHQOTE DU COUDRAY</td>
          <td></td><td></td><td></td>
          <td class="score">23.5</td>
          <td>Sat 10:51</td><td></td><td></td>
          <td class="score">23.5</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>172</td>
          <td></td>
          <td>Izzy Taylor (GBR)</td>
          <td data-horse="BARRINGTON BOY" data-number="172"
              data-rider="Izzy Taylor (GBR)">BARRINGTON BOY</td>
          <td></td><td></td><td></td>
          <td class="score">27.4</td>
          <td class="score">0</td>
          <td></td><td></td>
          <td class="score">27.4</td>
          <td></td>
        </tr>
        <tr>
          <td>146</td>
          <td></td>
          <td>Bubby Upton (GBR)</td>
          <td data-horse="LIGHT UP E" data-number="146"
              data-rider="Bubby Upton (GBR)">LIGHT UP E</td>
          <td></td><td></td><td></td>
          <td class="score">32.6</td>
          <td class="score">0 + 0.8</td>
          <td></td><td></td>
          <td class="score">33.4</td>
          <td></td>
        </tr>
        <tr>
          <td>178</td>
          <td></td>
          <td>Bubby Upton (GBR)</td>
          <td data-horse="AUCKLAND 7" data-number="178"
              data-rider="Bubby Upton (GBR)">AUCKLAND 7</td>
          <td></td><td></td><td></td>
          <td class="score">26.9</td>
          <td class="score">8 + 0.8</td>
          <td></td><td></td>
          <td class="score">35.7</td>
          <td></td>
        </tr>
        <tr>
          <td>148</td>
          <td></td>
          <td>Alicia Hawker (GBR)</td>
          <td data-horse="CHOCOTOFFRETTO Z" data-number="148"
              data-rider="Alicia Hawker (GBR)">CHOCOTOFFRETTO Z</td>
          <td></td><td></td><td></td>
          <td class="score">34.4</td>
          <td class="score">12 + 0.8</td>
          <td></td><td></td>
          <td class="score">47.2</td>
          <td></td>
        </tr>
        <tr>
          <td>177</td>
          <td></td>
          <td>Freddie Carden (GBR)</td>
          <td data-horse="MBF VITAL FINESSE" data-number="177"
              data-rider="Freddie Carden (GBR)">MBF VITAL FINESSE</td>
          <td></td><td></td><td></td>
          <td class="score">46.0</td>
          <td>EL</td><td></td><td></td>
          <td></td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        results = parse_leaderboard_results(
            html,
            board=board,
            collected_at=datetime(2026, 9, 19, 9, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 6)
        by_horse = {result.horse_name: result for result in results}
        leader = by_horse["HITCHQOTE DU COUDRAY"]
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 23.5)
        clear = by_horse["BARRINGTON BOY"]
        self.assertEqual(clear.show_jumping_penalties, 0.0)
        self.assertEqual(clear.finishing_score, 27.4)
        time_only = by_horse["LIGHT UP E"]
        self.assertEqual(time_only.show_jumping_penalties, 0.8)
        self.assertEqual(time_only.finishing_score, 33.4)
        double_rails_and_time = by_horse["AUCKLAND 7"]
        self.assertEqual(double_rails_and_time.show_jumping_penalties, 8.8)
        self.assertEqual(double_rails_and_time.finishing_score, 35.7)
        triple_rails_and_time = by_horse["CHOCOTOFFRETTO Z"]
        self.assertEqual(triple_rails_and_time.show_jumping_penalties, 12.8)
        self.assertEqual(triple_rails_and_time.finishing_score, 47.2)
        eliminated = by_horse["MBF VITAL FINESSE"]
        self.assertEqual(eliminated.show_jumping_penalties, 0.0)
        self.assertEqual(eliminated.finishing_score, 46.0)

    def test_saturday_10utc_show_jumping_wave_keeps_late_start_times_and_status(self):
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
          <td></td><td></td>
          <td class="score">27.2</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>210</td>
          <td></td>
          <td>Bubby Upton (GBR)</td>
          <td data-horse="SANCERRE DE TIJI" data-number="210"
              data-rider="Bubby Upton (GBR)">SANCERRE DE TIJI</td>
          <td></td><td></td><td></td>
          <td class="score">26.9</td>
          <td class="score">0 + 0.4</td>
          <td></td><td></td>
          <td class="score">27.3</td>
          <td></td>
        </tr>
        <tr>
          <td>214</td>
          <td></td>
          <td>Kitty King (GBR)</td>
          <td data-horse="KILCOLTRIM COOLEY" data-number="214"
              data-rider="Kitty King (GBR)">KILCOLTRIM COOLEY</td>
          <td></td><td></td><td></td>
          <td class="score">27.8</td>
          <td>Sat 10:55</td><td></td><td></td>
          <td class="score">27.8</td>
          <td></td>
        </tr>
        <tr>
          <td>212</td>
          <td></td>
          <td>Astier Nicolas (FRA)</td>
          <td data-horse="HITCHQOTE DU COUDRAY" data-number="212"
              data-rider="Astier Nicolas (FRA)">HITCHQOTE DU COUDRAY</td>
          <td></td><td></td><td></td>
          <td class="score">23.5</td>
          <td class="score">12</td>
          <td></td><td></td>
          <td class="score">35.5</td>
          <td></td>
        </tr>
        <tr>
          <td>208</td>
          <td></td>
          <td>Gireg Le Coz (FRA)</td>
          <td data-horse="MILWAUKEE TCS" data-number="208"
              data-rider="Gireg Le Coz (FRA)">MILWAUKEE TCS</td>
          <td></td><td></td><td></td>
          <td class="score">29.7</td>
          <td class="score">8 + 0.8</td>
          <td></td><td></td>
          <td class="score">38.5</td>
          <td></td>
        </tr>
        <tr>
          <td>197</td>
          <td></td>
          <td>John Tilley (GBR)</td>
          <td data-horse="COOLEY QUICKFIRE" data-number="197"
              data-rider="John Tilley (GBR)">COOLEY QUICKFIRE</td>
          <td></td><td></td><td></td>
          <td class="score">36.6</td>
          <td class="score">16 + 1.6</td>
          <td></td><td></td>
          <td class="score">54.2</td>
          <td></td>
        </tr>
        <tr>
          <td>177</td>
          <td></td>
          <td>Freddie Carden (GBR)</td>
          <td data-horse="MBF VITAL FINESSE" data-number="177"
              data-rider="Freddie Carden (GBR)">MBF VITAL FINESSE</td>
          <td></td><td></td><td></td>
          <td class="score">46.0</td>
          <td>EL</td><td></td><td></td>
          <td></td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        results = parse_leaderboard_results(
            html,
            board=board,
            collected_at=datetime(2026, 9, 19, 10, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 7)
        by_horse = {result.horse_name: result for result in results}
        leader = by_horse["BROOKFIELD DANNY DE MUZE"]
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 27.2)
        time_only = by_horse["SANCERRE DE TIJI"]
        self.assertEqual(time_only.show_jumping_penalties, 0.4)
        self.assertEqual(time_only.finishing_score, 27.3)
        remaining_start = by_horse["KILCOLTRIM COOLEY"]
        self.assertEqual(remaining_start.show_jumping_penalties, 0.0)
        self.assertEqual(remaining_start.finishing_score, 27.8)
        rails = by_horse["HITCHQOTE DU COUDRAY"]
        self.assertEqual(rails.show_jumping_penalties, 12.0)
        self.assertEqual(rails.finishing_score, 35.5)
        double_rails_and_time = by_horse["MILWAUKEE TCS"]
        self.assertEqual(double_rails_and_time.show_jumping_penalties, 8.8)
        self.assertEqual(double_rails_and_time.finishing_score, 38.5)
        heavy_compound = by_horse["COOLEY QUICKFIRE"]
        self.assertEqual(heavy_compound.show_jumping_penalties, 17.6)
        self.assertEqual(heavy_compound.finishing_score, 54.2)
        eliminated = by_horse["MBF VITAL FINESSE"]
        self.assertEqual(eliminated.show_jumping_penalties, 0.0)
        self.assertEqual(eliminated.finishing_score, 46.0)

    def test_saturday_11utc_cross_country_keeps_start_times_and_records_first_completers(self):
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
          <td>101</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD DANNY DE MUZE" data-number="101"
              data-rider="Tom McEwen (GBR)">BROOKFIELD DANNY DE MUZE</td>
          <td></td><td></td><td></td>
          <td class="score">27.2</td>
          <td class="score">0</td>
          <td></td><td></td>
          <td class="score">27.2</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>214</td>
          <td></td>
          <td>Kitty King (GBR)</td>
          <td data-horse="KILCOLTRIM COOLEY" data-number="214"
              data-rider="Kitty King (GBR)">KILCOLTRIM COOLEY</td>
          <td></td><td></td><td></td>
          <td class="score">27.8</td>
          <td class="score">0</td>
          <td></td><td></td>
          <td class="score">27.8</td>
          <td>4th</td>
        </tr>
        <tr>
          <td>215</td>
          <td></td>
          <td>Michael Jackson (GBR)</td>
          <td data-horse="GIRLS GAMBLE" data-number="215"
              data-rider="Michael Jackson (GBR)">GIRLS GAMBLE</td>
          <td></td><td></td><td></td>
          <td class="score">30.6</td>
          <td class="score">4</td>
          <td></td><td></td>
          <td class="score">34.6</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        eight_nine_results = parse_leaderboard_results(
            eight_nine_html,
            board=eight_nine_board,
            collected_at=datetime(2026, 9, 19, 11, 2, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 3)
        leader = eight_nine_by_horse["BROOKFIELD DANNY DE MUZE"]
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 27.2)
        clear_late = eight_nine_by_horse["KILCOLTRIM COOLEY"]
        self.assertEqual(clear_late.show_jumping_penalties, 0.0)
        self.assertEqual(clear_late.finishing_score, 27.8)
        four_faults = eight_nine_by_horse["GIRLS GAMBLE"]
        self.assertEqual(four_faults.show_jumping_penalties, 4.0)
        self.assertEqual(four_faults.finishing_score, 34.6)

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
          <td>17</td>
          <td></td>
          <td>Oliver Barrett (AUS)</td>
          <td data-horse="SANDHILLS BRIAR" data-number="17"
              data-rider="Oliver Barrett (AUS)">SANDHILLS BRIAR</td>
          <td></td><td></td><td></td>
          <td class="score">25.6</td>
          <td>Sat 12:46</td>
          <td></td>
          <td></td>
          <td class="score">25.6</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>2</td>
          <td></td>
          <td>Laura Collett (GBR)</td>
          <td data-horse="BALANCERO" data-number="2"
              data-rider="Laura Collett (GBR)">BALANCERO</td>
          <td></td><td></td><td></td>
          <td class="score">33.4</td>
          <td class="score">16 in 10.48</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">49.4</td>
          <td></td>
        </tr>
        <tr>
          <td>1</td>
          <td></td>
          <td>Clarke Johnstone (NZL)</td>
          <td data-horse="COOLEY STIRLING" data-number="1"
              data-rider="Clarke Johnstone (NZL)">COOLEY STIRLING</td>
          <td></td><td></td><td></td>
          <td class="score">37.4</td>
          <td class="score">8.4 in 10.29</td>
          <td class="score">11</td>
          <td></td>
          <td class="score">56.8</td>
          <td></td>
        </tr>
        <tr>
          <td>3</td>
          <td></td>
          <td>Rupert Batting (GBR)</td>
          <td data-horse="COOMBELAND TALISMAN" data-number="3"
              data-rider="Rupert Batting (GBR)">COOMBELAND TALISMAN</td>
          <td></td><td></td><td></td>
          <td class="score">43.1</td>
          <td>Sat 11:53</td>
          <td></td>
          <td></td>
          <td class="score">43.1</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 19, 11, 2, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 4)
        leader = cci4_by_horse["SANDHILLS BRIAR"]
        self.assertEqual(leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(leader.cross_country_time_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 25.6)
        time_faults = cci4_by_horse["BALANCERO"]
        self.assertEqual(time_faults.cross_country_jump_penalties, 0.0)
        self.assertEqual(time_faults.cross_country_time_penalties, 16.0)
        self.assertEqual(time_faults.finishing_score, 49.4)
        jump_and_time = cci4_by_horse["COOLEY STIRLING"]
        self.assertEqual(jump_and_time.cross_country_jump_penalties, 11.0)
        self.assertEqual(jump_and_time.cross_country_time_penalties, 8.4)
        self.assertEqual(jump_and_time.finishing_score, 56.8)
        waiting = cci4_by_horse["COOMBELAND TALISMAN"]
        self.assertEqual(waiting.cross_country_jump_penalties, 0.0)
        self.assertEqual(waiting.cross_country_time_penalties, 0.0)
        self.assertEqual(waiting.finishing_score, 43.1)

    def test_saturday_12utc_cross_country_records_next_completers(self):
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
          <td>18</td>
          <td></td>
          <td>Jesse Campbell (NZL)</td>
          <td data-horse="SPEEDWELL" data-number="18"
              data-rider="Jesse Campbell (NZL)">SPEEDWELL</td>
          <td></td><td></td><td></td>
          <td class="score">26.2</td>
          <td>Sat 15:16</td>
          <td></td>
          <td></td>
          <td class="score">26.2</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>4</td>
          <td></td>
          <td>Gemma Stevens (GBR)</td>
          <td data-horse="CHILLI'S JESTER" data-number="4"
              data-rider="Gemma Stevens (GBR)">CHILLI'S JESTER</td>
          <td></td><td></td><td></td>
          <td class="score">29.6</td>
          <td class="score">13.2 in 10.41</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">42.8</td>
          <td></td>
        </tr>
        <tr>
          <td>17</td>
          <td></td>
          <td>Oliver Barrett (AUS)</td>
          <td data-horse="SANDHILLS BRIAR" data-number="17"
              data-rider="Oliver Barrett (AUS)">SANDHILLS BRIAR</td>
          <td></td><td></td><td></td>
          <td class="score">25.6</td>
          <td class="score">19.2 in 10.56</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">44.8</td>
          <td></td>
        </tr>
        <tr>
          <td>2</td>
          <td></td>
          <td>Laura Collett (GBR)</td>
          <td data-horse="BALANCERO" data-number="2"
              data-rider="Laura Collett (GBR)">BALANCERO</td>
          <td></td><td></td><td></td>
          <td class="score">33.4</td>
          <td class="score">16 in 10.48</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">49.4</td>
          <td></td>
        </tr>
        <tr>
          <td>3</td>
          <td></td>
          <td>Rupert Batting (GBR)</td>
          <td data-horse="COOMBELAND TALISMAN" data-number="3"
              data-rider="Rupert Batting (GBR)">COOMBELAND TALISMAN</td>
          <td></td><td></td><td></td>
          <td class="score">43.1</td>
          <td class="score">27.6 in 11.17</td>
          <td class="score">11</td>
          <td></td>
          <td class="score">81.7</td>
          <td></td>
        </tr>
        <tr>
          <td>5</td>
          <td></td>
          <td>Emily Lochore (GBR)</td>
          <td data-horse="GULLITH" data-number="5"
              data-rider="Emily Lochore (GBR)">GULLITH</td>
          <td></td><td></td><td></td>
          <td class="score">36.2</td>
          <td>Sat 12:53</td>
          <td></td>
          <td></td>
          <td class="score">36.2</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 19, 12, 4, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 6)
        waiting_leader = cci4_by_horse["SPEEDWELL"]
        self.assertEqual(waiting_leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(waiting_leader.cross_country_time_penalties, 0.0)
        self.assertEqual(waiting_leader.finishing_score, 26.2)
        best_completer = cci4_by_horse["CHILLI'S JESTER"]
        self.assertEqual(best_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(best_completer.cross_country_time_penalties, 13.2)
        self.assertEqual(best_completer.finishing_score, 42.8)
        former_leader = cci4_by_horse["SANDHILLS BRIAR"]
        self.assertEqual(former_leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(former_leader.cross_country_time_penalties, 19.2)
        self.assertEqual(former_leader.finishing_score, 44.8)
        unchanged = cci4_by_horse["BALANCERO"]
        self.assertEqual(unchanged.cross_country_jump_penalties, 0.0)
        self.assertEqual(unchanged.cross_country_time_penalties, 16.0)
        self.assertEqual(unchanged.finishing_score, 49.4)
        jump_and_time = cci4_by_horse["COOMBELAND TALISMAN"]
        self.assertEqual(jump_and_time.cross_country_jump_penalties, 11.0)
        self.assertEqual(jump_and_time.cross_country_time_penalties, 27.6)
        self.assertEqual(jump_and_time.finishing_score, 81.7)
        next_to_go = cci4_by_horse["GULLITH"]
        self.assertEqual(next_to_go.cross_country_jump_penalties, 0.0)
        self.assertEqual(next_to_go.cross_country_time_penalties, 0.0)
        self.assertEqual(next_to_go.finishing_score, 36.2)

    def test_saturday_13utc_cross_country_records_next_completers(self):
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
          <td>18</td>
          <td></td>
          <td>Jesse Campbell (NZL)</td>
          <td data-horse="SPEEDWELL" data-number="18"
              data-rider="Jesse Campbell (NZL)">SPEEDWELL</td>
          <td></td><td></td><td></td>
          <td class="score">26.2</td>
          <td>Sat 15:16</td>
          <td></td>
          <td></td>
          <td class="score">26.2</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>28</td>
          <td></td>
          <td>Oliver Townend (GBR)</td>
          <td data-horse="SOMMERSBY" data-number="28"
              data-rider="Oliver Townend (GBR)">SOMMERSBY</td>
          <td></td><td></td><td></td>
          <td class="score">34.0</td>
          <td class="score">0 in 10.08</td>
          <td class="score">9*</td>
          <td></td>
          <td class="score">43</td>
          <td></td>
        </tr>
        <tr>
          <td>24</td>
          <td></td>
          <td>Isabelle Cook (GBR)</td>
          <td data-horse="CYMOON ''F'' Z" data-number="24"
              data-rider="Isabelle Cook (GBR)">CYMOON ''F'' Z</td>
          <td></td><td></td><td></td>
          <td class="score">33.7</td>
          <td class="score">11.2 in 10.36</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">44.9</td>
          <td></td>
        </tr>
        <tr>
          <td>23</td>
          <td></td>
          <td>Harry Dzenis (GBR)</td>
          <td data-horse="EMERALD ENDEAVOUR" data-number="23"
              data-rider="Harry Dzenis (GBR)">EMERALD ENDEAVOUR</td>
          <td></td><td></td><td></td>
          <td class="score">39.6</td>
          <td class="score">20.4 in 10.59</td>
          <td class="score">9</td>
          <td></td>
          <td class="score">69</td>
          <td></td>
        </tr>
        <tr>
          <td>16</td>
          <td></td>
          <td>Fiona Davidson (GBR)</td>
          <td data-horse="KARAVOLA" data-number="16"
              data-rider="Fiona Davidson (GBR)">KARAVOLA</td>
          <td></td><td></td><td></td>
          <td class="score">42.0</td>
          <td class="score">34 in 11.33</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">76</td>
          <td></td>
        </tr>
        <tr>
          <td>18</td>
          <td></td>
          <td>Joshua Levett (GBR)</td>
          <td data-horse="HUBERTHUS AC" data-number="18"
              data-rider="Joshua Levett (GBR)">HUBERTHUS AC</td>
          <td></td><td></td><td></td>
          <td class="score">39.2</td>
          <td class="score">22.8 in 11.05</td>
          <td class="score">20</td>
          <td></td>
          <td class="score">82</td>
          <td></td>
        </tr>
        <tr>
          <td>22</td>
          <td></td>
          <td>Jess Rimmer (GBR)</td>
          <td data-horse="THE SPICE MERCHANT" data-number="22"
              data-rider="Jess Rimmer (GBR)">THE SPICE MERCHANT</td>
          <td></td><td></td><td></td>
          <td class="score">39.4</td>
          <td class="score">44.4 in 11.59</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">83.8</td>
          <td></td>
        </tr>
        <tr>
          <td>19</td>
          <td></td>
          <td>Susie Berry (IRL)</td>
          <td data-horse="JOHN THE BULL" data-number="19"
              data-rider="Susie Berry (IRL)">JOHN THE BULL</td>
          <td></td><td></td><td></td>
          <td class="score">31.5</td>
          <td>Sat 13:31</td>
          <td></td>
          <td></td>
          <td class="score">31.5</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 19, 13, 4, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 8)
        waiting_leader = cci4_by_horse["SPEEDWELL"]
        self.assertEqual(waiting_leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(waiting_leader.cross_country_time_penalties, 0.0)
        self.assertEqual(waiting_leader.finishing_score, 26.2)
        inside_optimum = cci4_by_horse["SOMMERSBY"]
        self.assertEqual(inside_optimum.cross_country_jump_penalties, 9.0)
        self.assertEqual(inside_optimum.cross_country_time_penalties, 0.0)
        self.assertEqual(inside_optimum.finishing_score, 43.0)
        new_completer = cci4_by_horse["CYMOON ''F'' Z"]
        self.assertEqual(new_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(new_completer.cross_country_time_penalties, 11.2)
        self.assertEqual(new_completer.finishing_score, 44.9)
        jump_and_time = cci4_by_horse["EMERALD ENDEAVOUR"]
        self.assertEqual(jump_and_time.cross_country_jump_penalties, 9.0)
        self.assertEqual(jump_and_time.cross_country_time_penalties, 20.4)
        self.assertEqual(jump_and_time.finishing_score, 69.0)
        corrected_clear = cci4_by_horse["KARAVOLA"]
        self.assertEqual(corrected_clear.cross_country_jump_penalties, 0.0)
        self.assertEqual(corrected_clear.cross_country_time_penalties, 34.0)
        self.assertEqual(corrected_clear.finishing_score, 76.0)
        corrected_jump = cci4_by_horse["HUBERTHUS AC"]
        self.assertEqual(corrected_jump.cross_country_jump_penalties, 20.0)
        self.assertEqual(corrected_jump.cross_country_time_penalties, 22.8)
        self.assertEqual(corrected_jump.finishing_score, 82.0)
        late_completer = cci4_by_horse["THE SPICE MERCHANT"]
        self.assertEqual(late_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(late_completer.cross_country_time_penalties, 44.4)
        self.assertEqual(late_completer.finishing_score, 83.8)
        next_to_go = cci4_by_horse["JOHN THE BULL"]
        self.assertEqual(next_to_go.cross_country_jump_penalties, 0.0)
        self.assertEqual(next_to_go.cross_country_time_penalties, 0.0)
        self.assertEqual(next_to_go.finishing_score, 31.5)

    def test_saturday_14utc_cross_country_records_next_completers(self):
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
          <td></td><td></td><td></td>
          <td class="score">26.2</td>
          <td>Sat 15:16</td>
          <td></td>
          <td></td>
          <td class="score">26.2</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>36</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="THE FIELDMASTER" data-number="36"
              data-rider="Tom McEwen (GBR)">THE FIELDMASTER</td>
          <td></td><td></td><td></td>
          <td class="score">29.2</td>
          <td class="score">1.2 in 10.11</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">30.4</td>
          <td>5th</td>
        </tr>
        <tr>
          <td>28</td>
          <td></td>
          <td>Oliver Townend (GBR)</td>
          <td data-horse="SOMMERSBY" data-number="28"
              data-rider="Oliver Townend (GBR)">SOMMERSBY</td>
          <td></td><td></td><td></td>
          <td class="score">34.0</td>
          <td class="score">0 in 10.08</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">34</td>
          <td></td>
        </tr>
        <tr>
          <td>38</td>
          <td></td>
          <td>Sam Ecroyd (GBR)</td>
          <td data-horse="BLOOMFIELD MANUSCRIPT" data-number="38"
              data-rider="Sam Ecroyd (GBR)">BLOOMFIELD MANUSCRIPT</td>
          <td></td><td></td><td></td>
          <td class="score">32.1</td>
          <td class="score">3.6 in 10.17</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">35.7</td>
          <td></td>
        </tr>
        <tr>
          <td>46</td>
          <td></td>
          <td>Jack Pinkney (GBR)</td>
          <td data-horse="MONBEG STONE TOWN" data-number="46"
              data-rider="Jack Pinkney (GBR)">MONBEG STONE TOWN</td>
          <td></td><td></td><td></td>
          <td class="score">33.5</td>
          <td class="score">8.4 in 10.29</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">41.9</td>
          <td></td>
        </tr>
        <tr>
          <td>37</td>
          <td></td>
          <td>Tommy Greengard (USA)</td>
          <td data-horse="THAT'S ME Z" data-number="37"
              data-rider="Tommy Greengard (USA)">THAT'S ME Z</td>
          <td></td><td></td><td></td>
          <td class="score">32.1</td>
          <td class="score">17.6 in 10.52</td>
          <td class="score">9*</td>
          <td></td>
          <td class="score">58.7</td>
          <td></td>
        </tr>
        <tr>
          <td>40</td>
          <td></td>
          <td>Alexandre D’Orso (FRA)</td>
          <td data-horse="CANON ST MARTIN" data-number="40"
              data-rider="Alexandre D’Orso (FRA)">CANON ST MARTIN</td>
          <td></td><td></td><td></td>
          <td class="score">33.0</td>
          <td class="score">56 in 12.28</td>
          <td class="score">40</td>
          <td></td>
          <td class="score">129</td>
          <td></td>
        </tr>
        <tr>
          <td>29</td>
          <td></td>
          <td>Susie Berry (IRL)</td>
          <td data-horse="JOHN THE BULL" data-number="29"
              data-rider="Susie Berry (IRL)">JOHN THE BULL</td>
          <td></td><td></td><td></td>
          <td class="score">31.5</td>
          <td></td>
          <td>EL</td>
          <td></td>
          <td>EL (XC-FR)</td>
          <td></td>
        </tr>
        <tr>
          <td>52</td>
          <td></td>
          <td>George Bartlett (GBR)</td>
          <td data-horse="LUKAS" data-number="52"
              data-rider="George Bartlett (GBR)">LUKAS</td>
          <td></td><td></td><td></td>
          <td class="score">39.2</td>
          <td>Sat 14:46</td>
          <td></td>
          <td></td>
          <td class="score">39.2</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 19, 14, 4, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 9)
        waiting_leader = cci4_by_horse["SPEEDWELL"]
        self.assertEqual(waiting_leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(waiting_leader.cross_country_time_penalties, 0.0)
        self.assertEqual(waiting_leader.finishing_score, 26.2)
        best_completer = cci4_by_horse["THE FIELDMASTER"]
        self.assertEqual(best_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(best_completer.cross_country_time_penalties, 1.2)
        self.assertEqual(best_completer.finishing_score, 30.4)
        corrected_clear = cci4_by_horse["SOMMERSBY"]
        self.assertEqual(corrected_clear.cross_country_jump_penalties, 0.0)
        self.assertEqual(corrected_clear.cross_country_time_penalties, 0.0)
        self.assertEqual(corrected_clear.finishing_score, 34.0)
        inside_window = cci4_by_horse["BLOOMFIELD MANUSCRIPT"]
        self.assertEqual(inside_window.cross_country_jump_penalties, 0.0)
        self.assertEqual(inside_window.cross_country_time_penalties, 3.6)
        self.assertEqual(inside_window.finishing_score, 35.7)
        later_clear = cci4_by_horse["MONBEG STONE TOWN"]
        self.assertEqual(later_clear.cross_country_jump_penalties, 0.0)
        self.assertEqual(later_clear.cross_country_time_penalties, 8.4)
        self.assertEqual(later_clear.finishing_score, 41.9)
        flagged_jump = cci4_by_horse["THAT'S ME Z"]
        self.assertEqual(flagged_jump.cross_country_jump_penalties, 9.0)
        self.assertEqual(flagged_jump.cross_country_time_penalties, 17.6)
        self.assertEqual(flagged_jump.finishing_score, 58.7)
        heavy_penalties = cci4_by_horse["CANON ST MARTIN"]
        self.assertEqual(heavy_penalties.cross_country_jump_penalties, 40.0)
        self.assertEqual(heavy_penalties.cross_country_time_penalties, 56.0)
        self.assertEqual(heavy_penalties.finishing_score, 129.0)
        eliminated = cci4_by_horse["JOHN THE BULL"]
        self.assertEqual(eliminated.cross_country_jump_penalties, 0.0)
        self.assertEqual(eliminated.cross_country_time_penalties, 0.0)
        self.assertEqual(eliminated.finishing_score, 31.5)
        next_to_go = cci4_by_horse["LUKAS"]
        self.assertEqual(next_to_go.cross_country_jump_penalties, 0.0)
        self.assertEqual(next_to_go.cross_country_time_penalties, 0.0)
        self.assertEqual(next_to_go.finishing_score, 39.2)

    def test_saturday_15utc_cross_country_records_next_completers(self):
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
          <td>36</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="THE FIELDMASTER" data-number="36"
              data-rider="Tom McEwen (GBR)">THE FIELDMASTER</td>
          <td></td><td></td><td></td>
          <td class="score">29.2</td>
          <td class="score">1.2 in 10.11</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">30.4</td>
          <td></td>
        </tr>
        <tr>
          <td>61</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD QUALITY" data-number="61"
              data-rider="Tom McEwen (GBR)">BROOKFIELD QUALITY</td>
          <td></td><td></td><td></td>
          <td class="score">26.5</td>
          <td class="score">4 in 10.18</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">30.5</td>
          <td></td>
        </tr>
        <tr>
          <td>28</td>
          <td></td>
          <td>Oliver Townend (GBR)</td>
          <td data-horse="SOMMERSBY" data-number="28"
              data-rider="Oliver Townend (GBR)">SOMMERSBY</td>
          <td></td><td></td><td></td>
          <td class="score">34.0</td>
          <td class="score">0 in 10.08</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">34</td>
          <td></td>
        </tr>
        <tr>
          <td>60</td>
          <td></td>
          <td>Jesse Campbell (NZL)</td>
          <td data-horse="SPEEDWELL" data-number="60"
              data-rider="Jesse Campbell (NZL)">SPEEDWELL</td>
          <td></td><td></td><td></td>
          <td class="score">26.2</td>
          <td class="score">8.4 in 10.29</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">34.6</td>
          <td></td>
        </tr>
        <tr>
          <td>64</td>
          <td></td>
          <td>Zara Tindall (GBR)</td>
          <td data-horse="CLASSICALS EURO STAR" data-number="64"
              data-rider="Zara Tindall (GBR)">CLASSICALS EURO STAR</td>
          <td></td><td></td><td></td>
          <td class="score">31.5</td>
          <td class="score">8 in 10.28</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">39.5</td>
          <td></td>
        </tr>
        <tr>
          <td>62</td>
          <td></td>
          <td>Clarke Johnstone (NZL)</td>
          <td data-horse="SPARKY LAD" data-number="62"
              data-rider="Clarke Johnstone (NZL)">SPARKY LAD</td>
          <td></td><td></td><td></td>
          <td class="score">30.0</td>
          <td class="score">4.8 in 10.20</td>
          <td class="score">11</td>
          <td></td>
          <td class="score">45.8</td>
          <td></td>
        </tr>
        <tr>
          <td>37</td>
          <td></td>
          <td>Tommy Greengard (USA)</td>
          <td data-horse="THAT'S ME Z" data-number="37"
              data-rider="Tommy Greengard (USA)">THAT'S ME Z</td>
          <td></td><td></td><td></td>
          <td class="score">32.1</td>
          <td class="score">17.6 in 10.52</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">49.7</td>
          <td></td>
        </tr>
        <tr>
          <td>66</td>
          <td></td>
          <td>Jessica McKie (GBR)</td>
          <td data-horse="JUNGLE KING" data-number="66"
              data-rider="Jessica McKie (GBR)">JUNGLE KING</td>
          <td></td><td></td><td></td>
          <td class="score">40.6</td>
          <td class="score">36.4 in 11.39</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">77</td>
          <td></td>
        </tr>
        <tr>
          <td>67</td>
          <td></td>
          <td>Nicolai Aldinger (GER)</td>
          <td data-horse="BART 18" data-number="67"
              data-rider="Nicolai Aldinger (GER)">BART 18</td>
          <td></td><td></td><td></td>
          <td class="score">33.6</td>
          <td class="score">34.4 in 11.34</td>
          <td class="score">20</td>
          <td></td>
          <td class="score">88</td>
          <td></td>
        </tr>
        <tr>
          <td>73</td>
          <td></td>
          <td>Rupert Batting (GBR)</td>
          <td data-horse="COOMBELAND SEMILLY" data-number="73"
              data-rider="Rupert Batting (GBR)">COOMBELAND SEMILLY</td>
          <td></td><td></td><td></td>
          <td class="score">35.6</td>
          <td class="score">23.2 in 11.06</td>
          <td></td>
          <td></td>
          <td class="score">58.8</td>
          <td></td>
        </tr>
        <tr>
          <td>70</td>
          <td></td>
          <td>Alicia Wilkinson (GBR)</td>
          <td data-horse="CHILLI BILL" data-number="70"
              data-rider="Alicia Wilkinson (GBR)">CHILLI BILL</td>
          <td></td><td></td><td></td>
          <td class="score">42.9</td>
          <td class="score">32 in 11.28</td>
          <td class="score">31</td>
          <td></td>
          <td class="score">105.9</td>
          <td></td>
        </tr>
        <tr>
          <td>71</td>
          <td></td>
          <td>Sarah Ennis (IRL)</td>
          <td data-horse="ONCEUPONATIME" data-number="71"
              data-rider="Sarah Ennis (IRL)">ONCEUPONATIME</td>
          <td></td><td></td><td></td>
          <td class="score">32.6</td>
          <td class="score">42.4 in 11.54</td>
          <td class="score">40</td>
          <td></td>
          <td class="score">115</td>
          <td></td>
        </tr>
        <tr>
          <td>29</td>
          <td></td>
          <td>Susie Berry (IRL)</td>
          <td data-horse="JOHN THE BULL" data-number="29"
              data-rider="Susie Berry (IRL)">JOHN THE BULL</td>
          <td></td><td></td><td></td>
          <td class="score">31.5</td>
          <td></td>
          <td>EL</td>
          <td></td>
          <td>EL (XC-FR)</td>
          <td></td>
        </tr>
        <tr>
          <td>75</td>
          <td></td>
          <td>Rafael Losano (BRA)</td>
          <td data-horse="MASTER QUALITY IMP" data-number="75"
              data-rider="Rafael Losano (BRA)">MASTER QUALITY IMP</td>
          <td></td><td></td><td></td>
          <td class="score">36.5</td>
          <td>Sat 16:01</td>
          <td></td>
          <td></td>
          <td class="score">36.5</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 19, 15, 4, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 14)
        best_completer = cci4_by_horse["THE FIELDMASTER"]
        self.assertEqual(best_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(best_completer.cross_country_time_penalties, 1.2)
        self.assertEqual(best_completer.finishing_score, 30.4)
        second_completer = cci4_by_horse["BROOKFIELD QUALITY"]
        self.assertEqual(second_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(second_completer.cross_country_time_penalties, 4.0)
        self.assertEqual(second_completer.finishing_score, 30.5)
        still_clear = cci4_by_horse["SOMMERSBY"]
        self.assertEqual(still_clear.cross_country_jump_penalties, 0.0)
        self.assertEqual(still_clear.cross_country_time_penalties, 0.0)
        self.assertEqual(still_clear.finishing_score, 34.0)
        former_leader = cci4_by_horse["SPEEDWELL"]
        self.assertEqual(former_leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(former_leader.cross_country_time_penalties, 8.4)
        self.assertEqual(former_leader.finishing_score, 34.6)
        later_clear = cci4_by_horse["CLASSICALS EURO STAR"]
        self.assertEqual(later_clear.cross_country_jump_penalties, 0.0)
        self.assertEqual(later_clear.cross_country_time_penalties, 8.0)
        self.assertEqual(later_clear.finishing_score, 39.5)
        jump_faults = cci4_by_horse["SPARKY LAD"]
        self.assertEqual(jump_faults.cross_country_jump_penalties, 11.0)
        self.assertEqual(jump_faults.cross_country_time_penalties, 4.8)
        self.assertEqual(jump_faults.finishing_score, 45.8)
        corrected_jump = cci4_by_horse["THAT'S ME Z"]
        self.assertEqual(corrected_jump.cross_country_jump_penalties, 0.0)
        self.assertEqual(corrected_jump.cross_country_time_penalties, 17.6)
        self.assertEqual(corrected_jump.finishing_score, 49.7)
        later_time = cci4_by_horse["COOMBELAND SEMILLY"]
        self.assertEqual(later_time.cross_country_jump_penalties, 0.0)
        self.assertEqual(later_time.cross_country_time_penalties, 23.2)
        self.assertEqual(later_time.finishing_score, 58.8)
        heavy_time = cci4_by_horse["JUNGLE KING"]
        self.assertEqual(heavy_time.cross_country_jump_penalties, 0.0)
        self.assertEqual(heavy_time.cross_country_time_penalties, 36.4)
        self.assertEqual(heavy_time.finishing_score, 77.0)
        late_jump = cci4_by_horse["BART 18"]
        self.assertEqual(late_jump.cross_country_jump_penalties, 20.0)
        self.assertEqual(late_jump.cross_country_time_penalties, 34.4)
        self.assertEqual(late_jump.finishing_score, 88.0)
        heavy_combo = cci4_by_horse["CHILLI BILL"]
        self.assertEqual(heavy_combo.cross_country_jump_penalties, 31.0)
        self.assertEqual(heavy_combo.cross_country_time_penalties, 32.0)
        self.assertEqual(heavy_combo.finishing_score, 105.9)
        heaviest = cci4_by_horse["ONCEUPONATIME"]
        self.assertEqual(heaviest.cross_country_jump_penalties, 40.0)
        self.assertEqual(heaviest.cross_country_time_penalties, 42.4)
        self.assertEqual(heaviest.finishing_score, 115.0)
        eliminated = cci4_by_horse["JOHN THE BULL"]
        self.assertEqual(eliminated.cross_country_jump_penalties, 0.0)
        self.assertEqual(eliminated.cross_country_time_penalties, 0.0)
        self.assertEqual(eliminated.finishing_score, 31.5)
        next_to_go = cci4_by_horse["MASTER QUALITY IMP"]
        self.assertEqual(next_to_go.cross_country_jump_penalties, 0.0)
        self.assertEqual(next_to_go.cross_country_time_penalties, 0.0)
        self.assertEqual(next_to_go.finishing_score, 36.5)

    def test_saturday_16utc_cross_country_records_final_completers(self):
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
          <td>36</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="THE FIELDMASTER" data-number="36"
              data-rider="Tom McEwen (GBR)">THE FIELDMASTER</td>
          <td></td><td></td><td></td>
          <td class="score">29.2</td>
          <td class="score">1.2 in 10.11</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">30.4</td>
          <td></td>
        </tr>
        <tr>
          <td>66</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD QUALITY" data-number="66"
              data-rider="Tom McEwen (GBR)">BROOKFIELD QUALITY</td>
          <td></td><td></td><td></td>
          <td class="score">26.5</td>
          <td class="score">4 in 10.18</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">30.5</td>
          <td></td>
        </tr>
        <tr>
          <td>75</td>
          <td></td>
          <td>Sam Ecroyd (GBR)</td>
          <td data-horse="JACKPOT" data-number="75"
              data-rider="Sam Ecroyd (GBR)">JACKPOT</td>
          <td></td><td></td><td></td>
          <td class="score">32.4</td>
          <td class="score">5.2 in 10.21</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">37.6</td>
          <td></td>
        </tr>
        <tr>
          <td>80</td>
          <td></td>
          <td>Samuel Jeffree (AUS)</td>
          <td data-horse="SANTORO" data-number="80"
              data-rider="Samuel Jeffree (AUS)">SANTORO</td>
          <td></td><td></td><td></td>
          <td class="score">35.0</td>
          <td class="score">11.2 in 10.36</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">46.2</td>
          <td></td>
        </tr>
        <tr>
          <td>78</td>
          <td></td>
          <td>Alice Casburn (GBR)</td>
          <td data-horse="LSS ILE DE RE" data-number="78"
              data-rider="Alice Casburn (GBR)">LSS ILE DE RE</td>
          <td></td><td></td><td></td>
          <td class="score">36.0</td>
          <td class="score">11.2 in 10.36</td>
          <td class="score">0</td>
          <td></td>
          <td class="score">47.2</td>
          <td></td>
        </tr>
        <tr>
          <td>76</td>
          <td></td>
          <td>Dani Stewart-Richardson (GBR)</td>
          <td data-horse="LONDONLOOK TN" data-number="76"
              data-rider="Dani Stewart-Richardson (GBR)">LONDONLOOK TN</td>
          <td></td><td></td><td></td>
          <td class="score">30.8</td>
          <td class="score">22.8 in 11.05</td>
          <td class="score">20</td>
          <td></td>
          <td class="score">73.6</td>
          <td></td>
        </tr>
        <tr>
          <td>74</td>
          <td></td>
          <td>Alexander Bragg (GBR)</td>
          <td data-horse="SHANNONDALE ALDO" data-number="74"
              data-rider="Alexander Bragg (GBR)">SHANNONDALE ALDO</td>
          <td></td><td></td><td></td>
          <td class="score">36.7</td>
          <td class="score">22.4 in 11.04</td>
          <td class="score">20</td>
          <td></td>
          <td class="score">79.1</td>
          <td></td>
        </tr>
        <tr>
          <td>73</td>
          <td></td>
          <td>Rafael Losano (BRA)</td>
          <td data-horse="MASTER QUALITY IMP" data-number="73"
              data-rider="Rafael Losano (BRA)">MASTER QUALITY IMP</td>
          <td></td><td></td><td></td>
          <td class="score">36.5</td>
          <td class="score">27.6 in 11.17</td>
          <td class="score">20</td>
          <td></td>
          <td class="score">84.1</td>
          <td></td>
        </tr>
        <tr>
          <td>54</td>
          <td></td>
          <td>Alicia Wilkinson (GBR)</td>
          <td data-horse="CHILLI BILL" data-number="54"
              data-rider="Alicia Wilkinson (GBR)">CHILLI BILL</td>
          <td></td><td></td><td></td>
          <td class="score">42.9</td>
          <td class="score">32 in 11.28</td>
          <td class="score">20</td>
          <td></td>
          <td class="score">94.9</td>
          <td></td>
        </tr>
        <tr>
          <td>77</td>
          <td></td>
          <td>Sarah Hedges (GBR)</td>
          <td data-horse="IGNA" data-number="77"
              data-rider="Sarah Hedges (GBR)">IGNA</td>
          <td></td><td></td><td></td>
          <td class="score">30.1</td>
          <td class="score">44.8 in 12.00</td>
          <td class="score">20</td>
          <td></td>
          <td class="score">94.9</td>
          <td></td>
        </tr>
        <tr>
          <td>29</td>
          <td></td>
          <td>Susie Berry (IRL)</td>
          <td data-horse="JOHN THE BULL" data-number="29"
              data-rider="Susie Berry (IRL)">JOHN THE BULL</td>
          <td></td><td></td><td></td>
          <td class="score">31.5</td>
          <td></td>
          <td>EL</td>
          <td></td>
          <td>EL (XC-FR)</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        cci4_results = parse_leaderboard_results(
            cci4_html,
            board=cci4_board,
            collected_at=datetime(2026, 9, 19, 16, 9, tzinfo=timezone.utc),
        )
        cci4_by_horse = {result.horse_name: result for result in cci4_results}
        self.assertEqual(len(cci4_results), 11)
        best_completer = cci4_by_horse["THE FIELDMASTER"]
        self.assertEqual(best_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(best_completer.cross_country_time_penalties, 1.2)
        self.assertEqual(best_completer.finishing_score, 30.4)
        late_clear = cci4_by_horse["JACKPOT"]
        self.assertEqual(late_clear.cross_country_jump_penalties, 0.0)
        self.assertEqual(late_clear.cross_country_time_penalties, 5.2)
        self.assertEqual(late_clear.finishing_score, 37.6)
        later_clear = cci4_by_horse["SANTORO"]
        self.assertEqual(later_clear.cross_country_jump_penalties, 0.0)
        self.assertEqual(later_clear.cross_country_time_penalties, 11.2)
        self.assertEqual(later_clear.finishing_score, 46.2)
        matching_time = cci4_by_horse["LSS ILE DE RE"]
        self.assertEqual(matching_time.cross_country_jump_penalties, 0.0)
        self.assertEqual(matching_time.cross_country_time_penalties, 11.2)
        self.assertEqual(matching_time.finishing_score, 47.2)
        late_combo = cci4_by_horse["LONDONLOOK TN"]
        self.assertEqual(late_combo.cross_country_jump_penalties, 20.0)
        self.assertEqual(late_combo.cross_country_time_penalties, 22.8)
        self.assertEqual(late_combo.finishing_score, 73.6)
        later_combo = cci4_by_horse["SHANNONDALE ALDO"]
        self.assertEqual(later_combo.cross_country_jump_penalties, 20.0)
        self.assertEqual(later_combo.cross_country_time_penalties, 22.4)
        self.assertEqual(later_combo.finishing_score, 79.1)
        finished_pathfinder = cci4_by_horse["MASTER QUALITY IMP"]
        self.assertEqual(finished_pathfinder.cross_country_jump_penalties, 20.0)
        self.assertEqual(finished_pathfinder.cross_country_time_penalties, 27.6)
        self.assertEqual(finished_pathfinder.finishing_score, 84.1)
        corrected_jump = cci4_by_horse["CHILLI BILL"]
        self.assertEqual(corrected_jump.cross_country_jump_penalties, 20.0)
        self.assertEqual(corrected_jump.cross_country_time_penalties, 32.0)
        self.assertEqual(corrected_jump.finishing_score, 94.9)
        leftover_now_complete = cci4_by_horse["IGNA"]
        self.assertEqual(leftover_now_complete.cross_country_jump_penalties, 20.0)
        self.assertEqual(leftover_now_complete.cross_country_time_penalties, 44.8)
        self.assertEqual(leftover_now_complete.finishing_score, 94.9)
        eliminated = cci4_by_horse["JOHN THE BULL"]
        self.assertEqual(eliminated.cross_country_jump_penalties, 0.0)
        self.assertEqual(eliminated.cross_country_time_penalties, 0.0)
        self.assertEqual(eliminated.finishing_score, 31.5)

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

    def test_sunday_09utc_eight_nine_yo_cross_country_records_first_completers(self):
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
          <td>101</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD DANNY DE MUZE" data-number="101"
              data-rider="Tom McEwen (GBR)">BROOKFIELD DANNY DE MUZE</td>
          <td></td><td></td><td></td>
          <td class="score">27.2</td>
          <td class="score">0</td>
          <td>Sun 14:18</td>
          <td></td>
          <td class="score">27.2</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>108</td>
          <td></td>
          <td>Sammi Birch (AUS)</td>
          <td data-horse="MBF QUIDAMS TOUCH" data-number="108"
              data-rider="Sammi Birch (AUS)">MBF QUIDAMS TOUCH</td>
          <td></td><td></td><td></td>
          <td class="score">34.4</td>
          <td class="score">4 + 1.6</td>
          <td class="score">13.2 in 7.27</td>
          <td class="score">0</td>
          <td class="score">53.2</td>
          <td>86th</td>
        </tr>
        <tr>
          <td>105</td>
          <td></td>
          <td>Kirsty Chabert (GBR)</td>
          <td data-horse="CLIMATE CHANGE" data-number="105"
              data-rider="Kirsty Chabert (GBR)">CLIMATE CHANGE</td>
          <td></td><td></td><td></td>
          <td class="score">37.9</td>
          <td class="score">4 + 0.4</td>
          <td class="score">18 in 7.39</td>
          <td class="score">0</td>
          <td class="score">60.3</td>
          <td>88th</td>
        </tr>
        <tr>
          <td>109</td>
          <td></td>
          <td>Simon Grieve (GBR)</td>
          <td data-horse="BEST ESCAPADE" data-number="109"
              data-rider="Simon Grieve (GBR)">BEST ESCAPADE</td>
          <td></td><td></td><td></td>
          <td class="score">41.0</td>
          <td class="score">4 + 0.8</td>
          <td class="score">32.4 in 8.15</td>
          <td class="score">20</td>
          <td class="score">98.2</td>
          <td>93rd</td>
        </tr>
        <tr>
          <td>150</td>
          <td></td>
          <td>Padraig Mccarthy (IRL)</td>
          <td data-horse="KILROE TIGER" data-number="150"
              data-rider="Padraig Mccarthy (IRL)">KILROE TIGER</td>
          <td></td><td></td><td></td>
          <td class="score">31.1</td>
          <td class="score">0</td>
          <td>Sun 09:57</td>
          <td></td>
          <td class="score">31.1</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        eight_nine_results = parse_leaderboard_results(
            eight_nine_html,
            board=eight_nine_board,
            collected_at=datetime(2026, 9, 20, 9, 8, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 5)
        waiting_leader = eight_nine_by_horse["BROOKFIELD DANNY DE MUZE"]
        self.assertEqual(waiting_leader.show_jumping_penalties, 0.0)
        self.assertEqual(waiting_leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(waiting_leader.cross_country_time_penalties, 0.0)
        self.assertEqual(waiting_leader.finishing_score, 27.2)
        first_completer = eight_nine_by_horse["MBF QUIDAMS TOUCH"]
        self.assertEqual(first_completer.show_jumping_penalties, 5.6)
        self.assertEqual(first_completer.cross_country_jump_penalties, 0.0)
        self.assertEqual(first_completer.cross_country_time_penalties, 13.2)
        self.assertEqual(first_completer.finishing_score, 53.2)
        time_faults = eight_nine_by_horse["CLIMATE CHANGE"]
        self.assertEqual(time_faults.show_jumping_penalties, 4.4)
        self.assertEqual(time_faults.cross_country_jump_penalties, 0.0)
        self.assertEqual(time_faults.cross_country_time_penalties, 18.0)
        self.assertEqual(time_faults.finishing_score, 60.3)
        jump_and_time = eight_nine_by_horse["BEST ESCAPADE"]
        self.assertEqual(jump_and_time.show_jumping_penalties, 4.8)
        self.assertEqual(jump_and_time.cross_country_jump_penalties, 20.0)
        self.assertEqual(jump_and_time.cross_country_time_penalties, 32.4)
        self.assertEqual(jump_and_time.finishing_score, 98.2)
        still_waiting = eight_nine_by_horse["KILROE TIGER"]
        self.assertEqual(still_waiting.cross_country_jump_penalties, 0.0)
        self.assertEqual(still_waiting.cross_country_time_penalties, 0.0)
        self.assertEqual(still_waiting.finishing_score, 31.1)

    def test_sunday_10utc_eight_nine_yo_cross_country_records_later_completers(self):
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
          <th>Dressage</th><th>SJ</th><th>XCT</th><th>XCJ</th><th>Total</th><th>Place</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>101</td>
          <td></td>
          <td>Tom McEwen (GBR)</td>
          <td data-horse="BROOKFIELD DANNY DE MUZE" data-number="101"
              data-rider="Tom McEwen (GBR)">BROOKFIELD DANNY DE MUZE</td>
          <td class="score">27.2</td>
          <td class="score">0</td>
          <td>Sun 14:18</td>
          <td></td>
          <td class="score">27.2</td>
          <td>1st</td>
        </tr>
        <tr>
          <td>130</td>
          <td></td>
          <td>Finn Healy (GBR)</td>
          <td data-horse="GREANNANSTOWN MONBEG JOE" data-number="130"
              data-rider="Finn Healy (GBR)">GREANNANSTOWN MONBEG JOE</td>
          <td class="score">34.2</td>
          <td class="score">0</td>
          <td class="score">8.4 in 7.15</td>
          <td class="score">0</td>
          <td class="score">42.6</td>
          <td>49th</td>
        </tr>
        <tr>
          <td>126</td>
          <td></td>
          <td>Lara de Liedekerke-Meier (BEL)</td>
          <td data-horse="LA LA LAND D'ARVILLE" data-number="126"
              data-rider="Lara de Liedekerke-Meier (BEL)">LA LA LAND D'ARVILLE</td>
          <td class="score">34.2</td>
          <td class="score">8</td>
          <td class="score">11.6 in 7.23</td>
          <td class="score">0</td>
          <td class="score">53.8</td>
          <td>69th</td>
        </tr>
        <tr>
          <td>121</td>
          <td></td>
          <td>Jonelle Price (NZL)</td>
          <td data-horse="INDIAN TONIC" data-number="121"
              data-rider="Jonelle Price (NZL)">INDIAN TONIC</td>
          <td class="score">35.9</td>
          <td class="score">0</td>
          <td class="score">26.8 in 8.01</td>
          <td class="score">20</td>
          <td class="score">82.7</td>
          <td>86th</td>
        </tr>
        <tr>
          <td>207</td>
          <td></td>
          <td>Padraig Mccarthy (IRL)</td>
          <td data-horse="KILROE TIGER" data-number="207"
              data-rider="Padraig Mccarthy (IRL)">KILROE TIGER</td>
          <td class="score">31.1</td>
          <td class="score">4</td>
          <td>Sun 13:06</td>
          <td></td>
          <td class="score">35.1</td>
          <td>24th</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""
        eight_nine_results = parse_leaderboard_results(
            eight_nine_html,
            board=eight_nine_board,
            collected_at=datetime(2026, 9, 20, 10, 4, tzinfo=timezone.utc),
        )
        eight_nine_by_horse = {result.horse_name: result for result in eight_nine_results}
        self.assertEqual(len(eight_nine_results), 5)
        waiting_leader = eight_nine_by_horse["BROOKFIELD DANNY DE MUZE"]
        self.assertEqual(waiting_leader.show_jumping_penalties, 0.0)
        self.assertEqual(waiting_leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(waiting_leader.cross_country_time_penalties, 0.0)
        self.assertEqual(waiting_leader.finishing_score, 27.2)
        time_only = eight_nine_by_horse["GREANNANSTOWN MONBEG JOE"]
        self.assertEqual(time_only.show_jumping_penalties, 0.0)
        self.assertEqual(time_only.cross_country_jump_penalties, 0.0)
        self.assertEqual(time_only.cross_country_time_penalties, 8.4)
        self.assertEqual(time_only.finishing_score, 42.6)
        rails_and_time = eight_nine_by_horse["LA LA LAND D'ARVILLE"]
        self.assertEqual(rails_and_time.show_jumping_penalties, 8.0)
        self.assertEqual(rails_and_time.cross_country_jump_penalties, 0.0)
        self.assertEqual(rails_and_time.cross_country_time_penalties, 11.6)
        self.assertEqual(rails_and_time.finishing_score, 53.8)
        jump_and_time = eight_nine_by_horse["INDIAN TONIC"]
        self.assertEqual(jump_and_time.show_jumping_penalties, 0.0)
        self.assertEqual(jump_and_time.cross_country_jump_penalties, 20.0)
        self.assertEqual(jump_and_time.cross_country_time_penalties, 26.8)
        self.assertEqual(jump_and_time.finishing_score, 82.7)
        still_waiting = eight_nine_by_horse["KILROE TIGER"]
        self.assertEqual(still_waiting.show_jumping_penalties, 4.0)
        self.assertEqual(still_waiting.cross_country_jump_penalties, 0.0)
        self.assertEqual(still_waiting.cross_country_time_penalties, 0.0)
        self.assertEqual(still_waiting.finishing_score, 35.1)


if __name__ == "__main__":
    unittest.main()
