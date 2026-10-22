"""Tests for public USEA results-page parsing."""

from __future__ import annotations

import json
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.results import EventingResult, load_results
from equibets.usea import (
    UseaEvent,
    fork_tryon_sep_2026_event,
    merge_published_finals,
    parse_results_html,
    plantation_sep_2026_event,
    results_url,
    hagyard_midsouth_oct_2026_event,
    maryland_oct_2026_event,
    stable_view_sep_2026_event,
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
        fork = fork_tryon_sep_2026_event()
        self.assertEqual(fork.event_id, "19081")
        self.assertEqual(fork.event_title, "The Fork at Tryon")
        self.assertEqual(fork.event_date, date(2026, 9, 10))
        self.assertEqual(fork.country, "USA")
        self.assertEqual(
            fork.url,
            "https://useventing.com/events-competitions/resources/results/item?event=19081",
        )

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

    def test_hagyard_midsouth_event_uses_the_october_results_page(self) -> None:
        event = hagyard_midsouth_oct_2026_event()
        self.assertEqual(event.event_id, "19108")
        self.assertEqual(event.event_title, "Hagyard Midsouth")
        self.assertEqual(event.event_date, date(2026, 10, 14))
        self.assertEqual(event.country, "USA")
        self.assertEqual(
            event.url,
            "https://useventing.com/events-competitions/resources/results/item?event=19108",
        )

    def test_maryland_event_uses_the_fair_hill_results_page(self) -> None:
        event = maryland_oct_2026_event()
        self.assertEqual(event.event_id, "19110")
        self.assertEqual(event.event_title, "Maryland")
        self.assertEqual(event.event_date, date(2026, 10, 15))
        self.assertEqual(event.country, "USA")
        self.assertEqual(
            event.url,
            "https://useventing.com/events-competitions/resources/results/item?event=19110",
        )

    def test_stable_view_event_uses_the_oktoberfest_results_page(self) -> None:
        event = stable_view_sep_2026_event()
        self.assertEqual(event.event_id, "19093")
        self.assertEqual(event.event_title, "Stable View")
        self.assertEqual(event.event_date, date(2026, 9, 25))
        self.assertEqual(event.country, "USA")
        self.assertEqual(
            event.url,
            "https://useventing.com/events-competitions/resources/results/item?event=19093",
        )

    def test_published_finals_replace_provisional_rows_for_the_same_class(self) -> None:
        collected_at = datetime(2026, 9, 30, 8, 0, tzinfo=timezone.utc)
        provisional = EventingResult(
            source_id="evententries",
            source_record_id="evententries:provisional",
            source_priority=55,
            rider_name="Candace Elizabeth Bell (USA)",
            horse_name="Oscar",
            event_name="Stable View · CCI1*-S",
            event_date=date(2026, 9, 25),
            level="CCI1*-S",
            country="USA",
            dressage_score=26.7,
            show_jumping_penalties=0,
            cross_country_jump_penalties=0,
            cross_country_time_penalties=0,
            collected_at=collected_at,
        )
        other = EventingResult(
            source_id="evententries",
            source_record_id="evententries:other",
            source_priority=55,
            rider_name="Anna Zakrevska (CAN)",
            horse_name="Lakeside Park",
            event_name="Eventing at the Parks · CCI2*-S",
            event_date=date(2026, 9, 25),
            level="CCI2*-S",
            country="CAN",
            dressage_score=25.7,
            show_jumping_penalties=4,
            cross_country_jump_penalties=0,
            cross_country_time_penalties=0,
            collected_at=collected_at,
        )
        final = EventingResult(
            source_id="usea",
            source_record_id="usea:final",
            source_priority=50,
            rider_name="Candace Elizabeth Bell",
            horse_name="Oscar",
            event_name="Stable View · CCI1*-S",
            event_date=date(2026, 9, 25),
            level="CCI1*-S",
            country="USA",
            dressage_score=26.7,
            show_jumping_penalties=0,
            cross_country_jump_penalties=0,
            cross_country_time_penalties=2.8,
            collected_at=collected_at,
        )
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp) / "fei_results.json"
            store.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "source_id": "mixed",
                        "updated_at": "2026-09-27T19:07:16+00:00",
                        "results": [],
                    }
                ),
                encoding="utf-8",
            )
            from equibets.rechenstelle import merge_into_store

            merge_into_store(store, [provisional, other])
            merge_published_finals(store, [final])
            stored = load_results(store)

        self.assertEqual(
            [(result.source_id, result.event_name, result.rider_name, result.finishing_score) for result in stored],
            [
                ("evententries", "Eventing at the Parks · CCI2*-S", "Anna Zakrevska (CAN)", 29.7),
                ("usea", "Stable View · CCI1*-S", "Candace Elizabeth Bell", 29.5),
            ],
        )


if __name__ == "__main__":
    unittest.main()
