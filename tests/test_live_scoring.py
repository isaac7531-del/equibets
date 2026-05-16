import unittest
from datetime import UTC, datetime

from equibets.live_scoring import build_feed, parse_startbox_calendar


CALENDAR_SAMPLE = """
| May. 16, 2026 | [Results](http://eventingscores.com/eventsu/lynnleigh/sht0526) | Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US |
| --- | --- | --- |
| May.. 16-17, 2026 | [Results](http://eventingscores.com/eventsu/ramtap/sht0526) | Ram Tap May SHT Fresno, CA US |
| May. 17, 2026 | [Times](http://eventingscores.com/eventsu/bucks/sht0526) | Bucks County Horse Park May Schooling Horse Trial Revere, PA US |
| May. 23, 2026 | [Entries](http://eventingscores.com/eventsr/willowdraw/ht0526) | Sol Events at Willow Draw Weatherford, TX US |
| Apr. 25, 2026 | [Results](http://eventingscores.com/eventsu/lynnleigh/sht0426) | Lynnleigh Farm April 25, 2026 Schooling 2-Phase Sandy, UT US |
"""

HTML_CALENDAR_SAMPLE = """
<table>
  <tr>
    <td>May. 16, 2026</td>
    <td><a href="http://eventingscores.com/eventsu/lynnleigh/sht0526">Results</a></td>
    <td>Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US</td>
  </tr>
  <tr>
    <td>May. 17, 2026</td>
    <td><a href="/eventsu/bucks/sht0526">Times</a></td>
    <td>Bucks County Horse Park May Schooling Horse Trial Revere, PA US</td>
  </tr>
  <tr>
    <td>May. 17, 2026</td>
    <td><a href="http://eventingscores.com/eventsr/queeny/ht0526">Results</a></td>
    <td><span class="calshowname">Queeny Park Horse Trials</span><br /><span class="callocation">St. Louis, MO US</span></td>
  </tr>
</table>
"""


class LiveScoringFeedTests(unittest.TestCase):
    def test_parse_startbox_calendar_keeps_current_window(self):
        observed_at = datetime(2026, 5, 16, 11, 0, tzinfo=UTC)

        events = parse_startbox_calendar(CALENDAR_SAMPLE, observed_at=observed_at)

        self.assertEqual(
            [event.event_name for event in events],
            [
                "Lynnleigh Farm May 16, 2026 Schooling 2-Phase",
                "Ram Tap May SHT",
                "Bucks County Horse Park May Schooling Horse Trial",
                "Sol Events at Willow Draw",
            ],
        )
        self.assertEqual(events[0].status, "live_results")
        self.assertEqual(events[1].end_date.isoformat(), "2026-05-17")
        self.assertEqual(events[2].status, "ride_times")
        self.assertEqual(events[3].status, "entries")
        self.assertEqual(events[0].location, "Sandy, UT")
        self.assertEqual(events[0].country, "USA")

    def test_parse_startbox_calendar_supports_html_rows(self):
        observed_at = datetime(2026, 5, 16, 11, 0, tzinfo=UTC)

        events = parse_startbox_calendar(HTML_CALENDAR_SAMPLE, observed_at=observed_at)

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].status, "live_results")
        self.assertEqual(events[1].status, "ride_times")
        self.assertEqual(events[2].event_name, "Queeny Park Horse Trials")
        self.assertEqual(events[2].location, "St. Louis, MO")
        self.assertEqual(
            events[1].scoring_url,
            "https://eventing.startboxscoring.com/eventsu/bucks/sht0526",
        )

    def test_build_feed_serializes_events_for_browser(self):
        observed_at = datetime(2026, 5, 16, 11, 0, tzinfo=UTC)
        events = parse_startbox_calendar(CALENDAR_SAMPLE, observed_at=observed_at)

        feed = build_feed(
            events,
            generated_at=observed_at,
            source_url="https://eventing.startboxscoring.com/archives.php?Year=2026",
        )

        self.assertEqual(feed["coverage_window"]["from"], "2026-05-16")
        self.assertEqual(feed["coverage_window"]["through"], "2026-05-23")
        self.assertEqual(feed["events"][0]["last_observed_at"], "2026-05-16T11:00:00Z")


if __name__ == "__main__":
    unittest.main()
