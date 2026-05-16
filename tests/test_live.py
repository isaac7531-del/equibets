import unittest
from datetime import date, datetime, timezone

from equibets.live import (
    CalendarEvent,
    current_events,
    normalize_startbox_url,
    parse_calendar,
    parse_date_range,
    parse_live_event_page,
    refresh_live_scores,
)


CALENDAR_HTML = """
<table>
<tr>
  <td>May 16, 2026</td>
  <td><a href="http://eventingscores.com/eventsu/lynnleigh/sht0526">Results</a></td>
  <td>Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US</td>
</tr>
<tr>
  <td>May 16-17, 2026</td>
  <td><a href="http://eventingscores.com/eventsu/ramtap/sht0526">Results</a></td>
  <td>Ram Tap May SHT Fresno, CA US</td>
</tr>
<tr>
  <td>May 23, 2026</td>
  <td><a href="http://eventingscores.com/eventsr/willowdraw/ht0526">Entries</a></td>
  <td>Sol Events at Willow Draw Weatherford, TX US</td>
</tr>
</table>
"""

LEADERBOARD_HTML = """
<h1 class="showname">Ram Tap May SHT</h1>
<h2 class="">May 16-17, 2026 - Fresno, CA</h2>
<table id="leaderboard1">
  <tr>
    <td class="divisionldr">Division</td>
    <td class="phase">Phase</td>
    <td>Rider</td>
    <td>Horse</td>
    <td>Score</td>
  </tr>
  <tr class="drawdata1">
    <td class="bold">Open Training</td>
    <td><a href="times.php?division=5">Times</a> <a href="phase2_select.php?division=5&amp;order=place">Provisional Scores</a><br><span>Stadium: 11:45 AM Sun.</span></td>
    <td>Alexis Concolino</td>
    <td>Leo D</td>
    <td class="center place">30.3</td>
  </tr>
  <tr class="drawdata2">
    <td class="bold">Starter</td>
    <td><a href="draw.php?division=1">Entry Status</a> <a href="times.php?division=1">Times</a></td>
  </tr>
</table>
"""


class LiveScoringTests(unittest.TestCase):
    def test_parse_date_range_handles_one_and_two_day_events(self):
        self.assertEqual(parse_date_range("May 16, 2026"), (date(2026, 5, 16), date(2026, 5, 16)))
        self.assertEqual(parse_date_range("May 16-17, 2026"), (date(2026, 5, 16), date(2026, 5, 17)))

    def test_calendar_parses_current_result_links(self):
        events = parse_calendar(CALENDAR_HTML)

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].name, "Lynnleigh Farm May 16, 2026 Schooling 2-Phase")
        self.assertEqual(events[0].location, "Sandy, UT")
        self.assertEqual(events[0].country, "US")
        self.assertEqual(events[0].status, "Results")
        self.assertEqual(
            events[0].source_url,
            "https://eventing.startboxscoring.com/eventsu/lynnleigh/sht0526/",
        )

    def test_current_events_keep_active_result_pages(self):
        events = parse_calendar(CALENDAR_HTML)
        active = current_events(events, as_of=date(2026, 5, 16))

        self.assertEqual([event.name for event in active], ["Lynnleigh Farm May 16, 2026 Schooling 2-Phase", "Ram Tap May SHT"])

    def test_live_event_page_parses_leaders_and_pending_divisions(self):
        event = CalendarEvent(
            id="startbox-eventsu-ramtap-sht0526",
            name="Calendar Name",
            date_label="May 16-17, 2026",
            start_date=date(2026, 5, 16),
            end_date=date(2026, 5, 17),
            status="Results",
            source_url="https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/",
            location="Fresno, CA",
            country="US",
        )

        live_event = parse_live_event_page(LEADERBOARD_HTML, event)

        self.assertEqual(live_event.event.name, "Ram Tap May SHT")
        self.assertEqual(live_event.event.location, "Fresno, CA")
        self.assertEqual(len(live_event.divisions), 2)
        self.assertEqual(live_event.divisions[0].rider_name, "Alexis Concolino")
        self.assertEqual(live_event.divisions[0].horse_name, "Leo D")
        self.assertEqual(live_event.divisions[0].score, 30.3)
        self.assertIsNone(live_event.divisions[1].score)

    def test_refresh_live_scores_uses_fetcher_and_serializes_feed(self):
        def fake_fetcher(url):
            if url == "http://eventing.startboxscoring.com/":
                return CALENDAR_HTML
            return LEADERBOARD_HTML

        feed = refresh_live_scores(
            as_of=date(2026, 5, 16),
            generated_at=datetime(2026, 5, 16, 22, 0, tzinfo=timezone.utc),
            fetcher=fake_fetcher,
            max_events=1,
        )

        self.assertEqual(feed["as_of_date"], "2026-05-16")
        self.assertEqual(feed["generated_at"], "2026-05-16T22:00:00+00:00")
        self.assertEqual(len(feed["events"]), 1)
        self.assertEqual(feed["events"][0]["divisions"][0]["leader"]["score"], 30.3)

    def test_normalizes_legacy_eventingscores_links(self):
        self.assertEqual(
            normalize_startbox_url("http://eventingscores.com/eventsu/ramtap/sht0526"),
            "https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/",
        )


if __name__ == "__main__":
    unittest.main()
