import unittest
from datetime import date, datetime, timezone

from equibets.current_events import (
    build_current_event_feed,
    parse_startbox_calendar,
    select_live_scoring_events,
)


COLLECTED_AT = datetime(2026, 5, 15, 8, 2, tzinfo=timezone.utc)
SAMPLE_MARKDOWN = """
| May 16, 2026 | [Times](http://eventingscores.com/eventsu/lynnleigh/sht0526) | Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US |
| May 10, 2026 | [Results](http://eventingscores.com/eventsu/huntersrun/db0526) | Hunters Run Derby Metamora, MI US |
| Jun 13-14, 2026 | [Entries](http://eventingscores.com/eventsr/goldenspike/ht0626) | Golden Spike Horse Trials Ogden, UT US |
"""
SAMPLE_HTML = """
<table>
  <tr>
    <td>May 16-17, 2026</td>
    <td><a href="http://eventingscores.com/eventsu/ramtap/sht0526">Times</a></td>
    <td>Ram Tap May SHT Fresno, CA US</td>
  </tr>
</table>
"""


class CurrentEventTests(unittest.TestCase):
    def test_parse_startbox_markdown_calendar_rows(self):
        events = parse_startbox_calendar(SAMPLE_MARKDOWN, collected_at=COLLECTED_AT)

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].source_event_id, "startbox-eventsu-lynnleigh-sht0526")
        self.assertEqual(events[0].start_date, date(2026, 5, 16))
        self.assertEqual(events[0].end_date, date(2026, 5, 16))
        self.assertEqual(events[0].country, "US")
        self.assertEqual(events[0].status, "ride_times")
        self.assertEqual(events[1].status, "results")

    def test_parse_startbox_html_calendar_rows(self):
        events = parse_startbox_calendar(SAMPLE_HTML, collected_at=COLLECTED_AT)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_name, "Ram Tap May SHT Fresno, CA US")
        self.assertEqual(events[0].start_date, date(2026, 5, 16))
        self.assertEqual(events[0].end_date, date(2026, 5, 17))

    def test_select_live_scoring_events_keeps_current_window_sorted_by_status(self):
        events = parse_startbox_calendar(SAMPLE_MARKDOWN, collected_at=COLLECTED_AT)

        selected = select_live_scoring_events(
            events,
            today=date(2026, 5, 15),
            lookback_days=7,
            lookahead_days=21,
        )

        self.assertEqual([event.status for event in selected], ["ride_times", "results"])
        self.assertEqual(selected[0].event_name, "Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US")

    def test_build_current_event_feed_serializes_events(self):
        feed = build_current_event_feed(
            SAMPLE_MARKDOWN,
            collected_at=COLLECTED_AT,
            today=date(2026, 5, 15),
            lookback_days=7,
            lookahead_days=21,
        )

        self.assertEqual(feed["source_id"], "startbox_eventing")
        self.assertEqual(len(feed["events"]), 2)
        self.assertEqual(feed["events"][0]["status"], "ride_times")


if __name__ == "__main__":
    unittest.main()
