"""Tests for Rechenstelle live leaderboard parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.rechenstelle import RechenstelleBoard, parse_leaderboard_results


SAMPLE_HTML = """
<html>
  <head><title>LeaderBoard · Millstreet 2026 · CH-M-U25-C</title></head>
  <body>
    <p class="lastupdate">Last Update: Jul 23 2026 5:01PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>302</td>
          <td class="riderCell"><span class="riderName">Calvin B&Ouml;CKMANN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Altair de la Cense</span></td>
          <td>456,0</td>
          <td>72,38</td>
          <td>27,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>332</td>
          <td class="riderCell"><span class="riderName">Jennifer KUEHNLE</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Sammy Davis Junior</span></td>
          <td>446,0</td>
          <td>70,79</td>
          <td>29,2</td>
          <td>2.</td>
          <td>20,0</td>
          <td>1,6</td>
          <td>50,8</td>
          <td>2.</td>
          <td>4,0</td>
          <td></td>
          <td>54,8</td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>340</td>
          <td class="riderCell"><span class="riderName">Maddison PERIES</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Vivero DH Z</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>111</td>
          <td class="riderCell"><span class="riderName">Kaylawna SMITH-COOK</span></td>
          <td><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Calling Cooley</span></td>
          <td>538,5</td>
          <td>71,80</td>
          <td>28,2</td>
          <td>1.</td>
          <td></td>
          <td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SHORT_FORMAT_HTML = """
<html>
  <head><title>LeaderBoard · Millstreet 2026 · CCI3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Jul 25 2026 10:23AM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Jumping</th><th>Rank after Jumping</th>
          <th>Cross-Country</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>601</td>
          <td class="riderCell"><span class="riderName">Ian CASSELLS</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Cooley Capri Sun</span></td>
          <td>526,0</td>
          <td>70,13</td>
          <td>29,9</td>
          <td>2.</td>
          <td>0,0</td>
          <td class="good">73,22</td>
          <td>29,9</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>8.</strong></td>
          <td>608</td>
          <td class="riderCell"><span class="riderName">Kevin MCNAB</span></td>
          <td><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Newmarket Amy</span></td>
          <td>525,0</td>
          <td>70,00</td>
          <td>30,0</td>
          <td>3.</td>
          <td>4,0</td>
          <td>70,31</td>
          <td>34,0</td>
          <td>8.</td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

LONG_FORMAT_CLOCK_TIME_HTML = """
<html>
  <head><title>LeaderBoard · Millstreet 2026 · CCI3*-L</title></head>
  <body>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>102</td>
          <td class="riderCell"><span class="riderName">Hallie COON</span></td>
          <td><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Boleybawn Oliva</span></td>
          <td>493,0</td>
          <td>65,73</td>
          <td>34,3</td>
          <td>9.</td>
          <td>2,8</td>
          <td>08:35</td>
          <td>37,1</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


class RechenstelleTests(unittest.TestCase):
    def test_parse_leaderboard_results_normalizes_scores_and_skips_status_rows(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/millstreet_07/leaderboard52.html",
            event_name="Millstreet · CH-M-U25-C",
            level="CH-M-U25-C",
            event_date=date(2026, 7, 21),
            country="IRL",
        )
        collected_at = datetime(2026, 7, 24, 2, 0, tzinfo=timezone.utc)
        results = parse_leaderboard_results(
            SAMPLE_HTML,
            board=board,
            collected_at=collected_at,
        )

        self.assertEqual(len(results), 2)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Calvin BÖCKMANN (GER)")
        self.assertEqual(leader.horse_name, "Altair de la Cense")
        self.assertEqual(leader.dressage_score, 27.6)
        self.assertEqual(leader.finishing_score, 27.6)
        self.assertEqual(leader.source_id, "rechenstelle")
        self.assertEqual(leader.event_name, "Millstreet · CH-M-U25-C")

        second = results[1]
        self.assertEqual(second.cross_country_jump_penalties, 20.0)
        self.assertEqual(second.cross_country_time_penalties, 1.6)
        self.assertEqual(second.show_jumping_penalties, 4.0)
        self.assertEqual(second.finishing_score, 54.8)

    def test_parse_short_format_uses_jumping_faults_not_clock_time(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/millstreet_07/leaderboard05.html",
            event_name="Millstreet · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 7, 21),
            country="IRL",
        )
        results = parse_leaderboard_results(SHORT_FORMAT_HTML, board=board)

        self.assertEqual(len(results), 2)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Ian CASSELLS (IRL)")
        self.assertEqual(leader.dressage_score, 29.9)
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.cross_country_time_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 29.9)

        eighth = results[1]
        self.assertEqual(eighth.rider_name, "Kevin MCNAB (AUS)")
        self.assertEqual(eighth.show_jumping_penalties, 4.0)
        self.assertEqual(eighth.finishing_score, 34.0)

    def test_parse_long_format_ignores_mmss_clock_times(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/millstreet_07/leaderboard02.html",
            event_name="Millstreet · CCI3*-L",
            level="CCI3*-L",
            event_date=date(2026, 7, 21),
            country="IRL",
        )
        results = parse_leaderboard_results(LONG_FORMAT_CLOCK_TIME_HTML, board=board)

        self.assertEqual(len(results), 1)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Hallie COON (USA)")
        self.assertEqual(leader.cross_country_jump_penalties, 2.8)
        self.assertEqual(leader.cross_country_time_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 37.1)


if __name__ == "__main__":
    unittest.main()
