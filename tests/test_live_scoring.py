import unittest
from datetime import date, datetime, timezone

from equibets.live_scoring import (
    live_scores_feed,
    parse_startbox_calendar,
    parse_startbox_leaders,
)


CALENDAR_HTML = """
<table>
  <tr>
    <td>May 16-17, 2026</td>
    <td><a href="http://eventingscores.com/eventsu/ramtap/sht0526">Times</a></td>
    <td>Ram Tap May SHT Fresno, CA US</td>
  </tr>
  <tr>
    <td>May 9-10, 2026</td>
    <td><a href="http://eventingscores.com/eventsr/queeny/ht0526">Results</a></td>
    <td>Queeny Park Horse Trials St. Louis, MO US</td>
  </tr>
  <tr>
    <td>Apr 1, 2026</td>
    <td><a href="http://example.com/old">Results</a></td>
    <td>Old Horse Trials Lexington, KY US</td>
  </tr>
</table>
"""


LEADERS_HTML = """
<table>
  <tr>
    <th>Division</th>
    <th>Phase</th>
    <th>Current Leader</th>
  </tr>
  <tr>
    <th>Rider</th>
    <th>Horse</th>
    <th>Score</th>
  </tr>
  <tr>
    <td>Novice A by Straatman</td>
    <td><a href="final_select.php?division=2&amp;order=place">Final Scores</a></td>
    <td>Isabell Pezold</td>
    <td>Hard Pass</td>
    <td>23.9</td>
  </tr>
  <tr>
    <td>Non-Compete</td>
    <td><a href="draw.php?division=11">Entry Status</a> Dressage: Ring 1</td>
  </tr>
</table>
"""


class LiveScoringTests(unittest.TestCase):
    def test_parse_startbox_calendar_finds_current_and_recent_events(self):
        events = parse_startbox_calendar(
            CALENDAR_HTML,
            today=date(2026, 5, 14),
            lookback_days=7,
            lookahead_days=7,
        )

        self.assertEqual([event.name for event in events], ["Queeny Park Horse Trials", "Ram Tap May SHT"])
        self.assertEqual(events[0].status, "results")
        self.assertEqual(events[0].country, "USA")
        self.assertEqual(events[0].location, "St. Louis, MO")
        self.assertEqual(events[1].status, "times_posted")

    def test_parse_startbox_leaders_returns_division_scores(self):
        event = parse_startbox_calendar(
            CALENDAR_HTML,
            today=date(2026, 5, 14),
            lookback_days=7,
            lookahead_days=7,
        )[0]

        leaders = parse_startbox_leaders(
            LEADERS_HTML,
            event=event,
            collected_at=datetime(2026, 5, 14, 20, 3, tzinfo=timezone.utc),
        )

        self.assertEqual(len(leaders), 1)
        self.assertEqual(leaders[0].division, "Novice A by Straatman")
        self.assertEqual(leaders[0].rider_name, "Isabell Pezold")
        self.assertEqual(leaders[0].horse_name, "Hard Pass")
        self.assertEqual(leaders[0].score, 23.9)
        self.assertEqual(
            leaders[0].source_url,
            "http://eventingscores.com/eventsr/queeny/ht0526/final_select.php?division=2&order=place",
        )

    def test_live_scores_feed_serializes_dates_for_the_app(self):
        event = parse_startbox_calendar(
            CALENDAR_HTML,
            today=date(2026, 5, 14),
            lookback_days=7,
            lookahead_days=7,
        )[0]
        collected_at = datetime(2026, 5, 14, 20, 3, tzinfo=timezone.utc)
        leader = parse_startbox_leaders(LEADERS_HTML, event=event, collected_at=collected_at)[0]

        feed = live_scores_feed([event], [leader], collected_at=collected_at)

        self.assertEqual(feed["generated_at"], "2026-05-14T20:03:00Z")
        self.assertEqual(feed["events"][0]["start_date"], "2026-05-09")
        self.assertEqual(feed["scores"][0]["score"], 23.9)


if __name__ == "__main__":
    unittest.main()
