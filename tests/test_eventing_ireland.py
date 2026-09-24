"""Tests for public Eventing Ireland class-result parsing."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from equibets.eventing_ireland import (
    EventingIrelandClass,
    event_class_ids,
    parse_class_results,
    results_url,
)


SAMPLE = {
    "error": False,
    "total": 4,
    "records": [
        {
            "classname": "NutriScience Equine CCI4*-L",
            "eventdate": "2026-09-23T00:00:00.000Z",
            "eventname": "Ballindenisk Intl 2",
            "horsename": "Jarson (KWPN)",
            "ridername": "Louisa Lockwood",
            "ridernationality": "GB",
            "resultid": 358074,
            "drstatus": "OK",
            "drscore": 34.6,
            "drpen": 0.0,
            "sjjumppen": "-",
            "sjtimepen": "-",
            "xcjumppen": "-",
            "xctimepen": "-",
            "HC": False,
        },
        {
            "classname": "NutriScience Equine CCI4*-L",
            "eventdate": "2026-09-23T00:00:00.000Z",
            "horsename": "Not Yet",
            "ridername": "Waiting Rider",
            "ridernationality": "IE",
            "resultid": 2,
            "drstatus": "",
            "drscore": 0.0,
            "drpen": 0.0,
            "sjjumppen": "-",
            "sjtimepen": "-",
            "xcjumppen": "-",
            "xctimepen": "-",
        },
        {
            "classname": "Aloga CCI2*-S",
            "eventdate": "2026-09-23T00:00:00.000Z",
            "horsename": "Withdrawn Horse",
            "ridername": "Withdrawn Rider",
            "ridernationality": "NZ",
            "resultid": 3,
            "drstatus": "WD",
            "drscore": 31.2,
            "drpen": 0.0,
            "sjjumppen": "-",
            "sjtimepen": "-",
            "xcjumppen": "-",
            "xctimepen": "-",
        },
        {
            "classname": "CCIP2-S",
            "eventdate": "2026-09-23T00:00:00.000Z",
            "horsename": "Pony Horse",
            "ridername": "Pony Rider",
            "ridernationality": "IE",
            "resultid": 4,
            "drstatus": "OK",
            "drscore": 30.0,
            "drpen": 0.0,
            "sjjumppen": "-",
            "sjtimepen": "-",
            "xcjumppen": "-",
            "xctimepen": "-",
        },
        {
            "classname": "CCI3*-S",
            "eventdate": "2026-09-23T00:00:00.000Z",
            "horsename": "Eliminated",
            "ridername": "Elim Rider",
            "ridernationality": "FR",
            "resultid": 5,
            "drstatus": "OK",
            "drscore": 33.4,
            "drpen": 0.0,
            "sjjumppen": 4,
            "sjtimepen": 0,
            "xcjumppen": "E",
            "xctimepen": "-",
        },
        {
            "classname": "CCI2*-L",
            "eventdate": "2026-09-23T00:00:00.000Z",
            "horsename": "GHS Diamanta (ISH)",
            "ridername": "Tom McEwen",
            "ridernationality": "GB",
            "resultid": 6,
            "drstatus": "OK",
            "drscore": "24.6",
            "drpen": 0,
            "sjjumppen": "4",
            "sjtimepen": "1.2",
            "xcjumppen": 20,
            "xctimepen": 3.6,
        },
    ],
}


class EventingIrelandTests(unittest.TestCase):
    def test_results_url_uses_the_public_class_api(self) -> None:
        self.assertEqual(
            results_url(28578),
            "https://api.eventingireland.com/public/event/class/results/28578",
        )
        self.assertEqual(event_class_ids(), (28578, 28581, 28579, 28582, 28580, 28583, 28584))

    def test_parse_keeps_positive_dressage_and_skips_unscored_status_and_pony(self) -> None:
        event = EventingIrelandClass(class_id=28578, event_title="Ballindenisk", country="IRL")
        collected_at = datetime(2026, 9, 24, 19, 20, tzinfo=timezone.utc)
        results = parse_class_results(SAMPLE, event=event, collected_at=collected_at)

        self.assertEqual(
            [(result.level, result.rider_name, result.horse_name, result.finishing_score) for result in results],
            [
                ("CCI4*-L", "Louisa Lockwood (GBR)", "Jarson (KWPN)", 34.6),
                ("CCI2*-L", "Tom McEwen (GBR)", "GHS Diamanta (ISH)", 53.4),
            ],
        )
        jumping = results[1]
        self.assertEqual(jumping.dressage_score, 24.6)
        self.assertEqual(jumping.show_jumping_penalties, 5.2)
        self.assertEqual(jumping.cross_country_jump_penalties, 20)
        self.assertEqual(jumping.cross_country_time_penalties, 3.6)
        scored = results[0]
        self.assertEqual(scored.dressage_score, 34.6)
        self.assertEqual(scored.show_jumping_penalties, 0)
        self.assertEqual(scored.cross_country_jump_penalties, 0)
        self.assertEqual(scored.cross_country_time_penalties, 0)
        self.assertEqual(scored.event_name, "Ballindenisk · CCI4*-L")
        self.assertEqual(scored.event_date.isoformat(), "2026-09-23")
        self.assertEqual(scored.country, "IRL")
        self.assertEqual(scored.source_id, "eventing_ireland")
        self.assertEqual(scored.source_priority, 9)
        self.assertTrue(scored.source_record_id.startswith("eventing_ireland:"))


if __name__ == "__main__":
    unittest.main()
