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


if __name__ == "__main__":
    unittest.main()
