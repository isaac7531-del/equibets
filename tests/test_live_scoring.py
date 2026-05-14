import unittest
from datetime import datetime, timezone

from equibets.live_scoring import (
    current_event_leaders,
    load_live_events,
    parse_usea_results_markdown,
)


USEA_SAMPLE = """
###### [TEST] Starter, START (Starters: 2)

Competitors

D-S

XC-J

XC-T

SJ-J

SJ-T

S

P

Pts

U-Pts

[Weekapaug Groove](https://useventing.com/events-competitions/profile?id=250195)/ [KAREN TAYLOR](https://useventing.com/events-competitions/profile?id=237105)

18.5

0

0

0

0

18.5

1

7.0

1-7.0

[Blue Oyster](https://useventing.com/events-competitions/profile?id=250831)/ [RORY CASHMAN](https://useventing.com/events-competitions/profile?id=219382)

39.7

--

--

12

E

E

E

0.0

--
"""


class LiveScoringTests(unittest.TestCase):
    def test_loads_seeded_current_event_scores(self):
        events = load_live_events()

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].source_id, "usea")
        self.assertEqual(events[0].leader.horse_name, "Weekapaug Groove")

    def test_current_event_leaders_sort_by_lowest_score(self):
        leaders = current_event_leaders(load_live_events(), limit=3)

        self.assertEqual([leader.horse_name for leader in leaders], ["Weekapaug Groove", "Lost at Sea", "Hacker"])
        self.assertEqual(leaders[0].total_penalties, 18.5)

    def test_parse_usea_results_markdown_skips_non_final_scores(self):
        event = parse_usea_results_markdown(
            USEA_SAMPLE,
            event_id="usea-sample",
            event_name="Sample H.T.",
            date_label="May 2026",
            source_url="https://useventing.com/events-competitions/resources/results/item?event=sample",
            collected_at=datetime(2026, 5, 14, 21, tzinfo=timezone.utc),
        )

        self.assertEqual(len(event.scores), 1)
        self.assertEqual(event.scores[0].horse_name, "Weekapaug Groove")
        self.assertEqual(event.scores[0].rider_name, "Karen Taylor")
        self.assertEqual(event.scores[0].phase_total, 18.5)


if __name__ == "__main__":
    unittest.main()
