"""Tests for public USEA results-page parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.usea import (
    UseaEvent,
    parse_results_html,
    plantation_sep_2026_event,
    results_url,
)


SAMPLE_HTML = """
<div class="event__results__list">
  <h6 class="results_heading">[HT] HT 4-Star, CCI4-S <span>(Starters: 2)</span></h6>
  <div class="other_row full_width">
    <div class="fleft first_col">
      <a href="/events-competitions/profile?id=1">Lovedance</a> /
      <a href="/events-competitions/profile?id=2">LAINE E. ASHKER </a>
    </div>
    <div class="fleft other_col">29.9</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">16</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">2.8</div>
    <div class="fleft other_col">48.7</div>
    <div class="fleft other_col">2</div>
    <div class="fleft other_col">29.0</div>
    <div class="fleft last_col">--</div>
  </div>
  <div class="other_row full_width">
    <div class="fleft first_col">
      <a href="/events-competitions/profile?id=3">Aviator</a> /
      <a href="/events-competitions/profile?id=4">MONICA SPENCER</a>
    </div>
    <div class="fleft other_col">33</div>
    <div class="fleft other_col">11</div>
    <div class="fleft other_col">RF</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">RF</div>
    <div class="fleft other_col">--</div>
    <div class="fleft other_col">--</div>
    <div class="fleft last_col">--</div>
  </div>
  <h6 class="results_heading">Open Preliminary <span>(Starters: 1)</span></h6>
  <div class="other_row full_width">
    <div class="fleft first_col">
      <a href="/events-competitions/profile?id=5">National Horse</a> /
      <a href="/events-competitions/profile?id=6">NATIONAL RIDER</a>
    </div>
    <div class="fleft other_col">30.0</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">30.0</div>
    <div class="fleft other_col">1</div>
    <div class="fleft other_col">0</div>
    <div class="fleft last_col">--</div>
  </div>
  <h6 class="results_heading">[HT] HT 3-Star, CCI3-S</h6>
  <div class="other_row full_width">
    <div class="fleft first_col">
      <a href="/events-competitions/profile?id=7">KC&#x27;s Heart Of Gold</a> /
      <a href="/events-competitions/profile?id=8">KIMBERLEY BÉGIN</a>
    </div>
    <div class="fleft other_col">28.3</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">0</div>
    <div class="fleft other_col">4</div>
    <div class="fleft other_col">0.4</div>
    <div class="fleft other_col">32.7</div>
    <div class="fleft other_col">1</div>
    <div class="fleft other_col">10</div>
    <div class="fleft last_col">--</div>
  </div>
</div>
<script>self.__next_f.push(["other_row full_width Lovedance"])</script>
"""


class UseaResultsTests(unittest.TestCase):
    def test_results_url_uses_the_public_results_board(self) -> None:
        self.assertEqual(
            results_url("19088"),
            "https://useventing.com/events-competitions/resources/results/item?event=19088",
        )
        self.assertEqual(plantation_sep_2026_event().event_id, "19088")

    def test_parse_keeps_numeric_cci_rows_and_skips_status_and_national(self) -> None:
        event = UseaEvent(
            event_id="19088",
            event_title="Plantation Field",
            event_date=date(2026, 9, 17),
            country="USA",
        )
        collected_at = datetime(2026, 9, 22, 3, 10, tzinfo=timezone.utc)
        results = parse_results_html(SAMPLE_HTML, event=event, collected_at=collected_at)

        self.assertEqual(
            [(result.level, result.horse_name, result.rider_name, result.finishing_score) for result in results],
            [
                ("CCI4*-S", "Lovedance", "Laine E. Ashker", 48.7),
                ("CCI3*-S", "KC's Heart Of Gold", "Kimberley Bégin", 32.7),
            ],
        )
        lovedance = results[0]
        self.assertEqual(lovedance.dressage_score, 29.9)
        self.assertEqual(lovedance.show_jumping_penalties, 2.8)
        self.assertEqual(lovedance.cross_country_jump_penalties, 0)
        self.assertEqual(lovedance.cross_country_time_penalties, 16)
        self.assertEqual(lovedance.event_name, "Plantation Field · CCI4*-S")
        self.assertEqual(lovedance.country, "USA")
        self.assertEqual(lovedance.source_id, "usea")
        self.assertTrue(lovedance.source_record_id.startswith("usea:"))


if __name__ == "__main__":
    unittest.main()
