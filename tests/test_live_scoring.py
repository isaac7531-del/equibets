import unittest
from datetime import date, datetime, timezone

from equibets.live_scoring import (
    build_live_snapshot,
    parse_startbox_calendar,
    parse_startbox_event_leaders,
    parse_startbox_event_page,
    parse_startbox_scores_page,
)


STARTBOX_CALENDAR = """
| May 16, 2026 | [Results](http://eventingscores.com/eventsu/lynnleigh/sht0526) | Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US |
| --- | --- | --- |
| May 16-17, 2026 | [Results](http://eventingscores.com/eventsu/ramtap/sht0526) | Ram Tap May SHT Fresno, CA US |
| May 17, 2026 | [Times](http://eventingscores.com/eventsu/bucks/sht0526) | Bucks County Horse Park May Schooling Horse Trial Revere, PA US |
| May 23, 2026 | [Entries](http://eventingscores.com/eventsr/willowdraw/ht0526) | Sol Events at Willow Draw Weatherford, TX US |
"""


RAM_TAP_EVENT_PAGE = """
| Division | Phase |
| --- | --- |
| Open Training | [Entry Status](https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/draw.php?division=5) [Times](https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/times.php?division=5) Dressage: 7:30 AM Sat. Ring 1 |
| Open Novice | [Entry Status](https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/draw.php?division=4) [Times](https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/times.php?division=4) Dressage: 8:18 AM Sat. Ring 1 |
"""


STARTBOX_HTML_CALENDAR = """
<table>
<tr class="drawdata1">
<td class="caldate">May 16-17, 2026</td>
<td class="calresults"><a class="img bold" href='http://eventingscores.com/eventsu/ramtap/sht0526'>Results</a></td>
<td><span class="calshowname">Ram Tap May SHT</span><br /><span class="callocation">Fresno, CA US</span></td>
</tr>
</table>
"""


STARTBOX_HTML_EVENT_PAGE = """
<table id="leaderboard1">
<tr><td class="divisionldr" rowspan="2">Division</td><td class="phase" rowspan="2">Phase</td><td colspan="3">Current Leader</td></tr>
<tr class="toprow"><td>Rider</td><td>Horse</td><td>Score</td></tr>
<tr class="drawdata1">
<td class="bold">Open Training</td>
<td><a href="times.php?division=5">Times</a> &nbsp;<a href="dressResultsEventing.php?division=5&order=place">Scores</a> &nbsp;<br /><span class="smaller padding-t">XC: 2:00 PM Sat.</span></td>
<td>Alexis Concolino</td>
<td>Leo D</td>
<td class="center place">30.3</td>
</tr>
</table>
"""

STARTBOX_SCORE_PAGE = """
<table id="draw">
<tr><td colspan="13" class="division"><h1>Modified 2026</h1></td></tr>
<tr class="toprow">
<td rowspan="2">No.</td><td rowspan="2">Rider</td><td rowspan="2">Horse & Owner</td>
<td colspan="2">Dressage</td><td colspan="4">Show Jumping</td><td rowspan="2">DR</td>
</tr>
<tr class="toprow"><td>Score</td><td>Place</td><td>Jump</td><td>Time Pen.</td><td>Total</td><td>Place</td></tr>
<tr class="drawdata1">
<td>867</td><td>Jennifer Haglin</td><td>Jaxi<br /><span class="owner">Jennifer Haglin</span></td>
<td class="center">36.8</td><td class="center place">2</td><td class="center">0</td><td class="center">0</td>
<td class="center">36.8</td><td class="center place">1</td><td class="center dress">&nbsp;</td>
</tr>
<tr class="drawdata2">
<td>895</td><td>Emmalee Tanner</td><td>Brazen Bugatti<br /><span class="owner">Emmalee Tanner</span></td>
<td class="center">36.5</td><td class="center place">1</td><td class="center">0</td><td class="center">---</td>
<td class="center">---</td><td class="center place">E</td><td class="center dress">&nbsp;</td>
</tr>
</table>
"""


class LiveScoringTests(unittest.TestCase):
    def test_parse_startbox_calendar_marks_current_events(self):
        events = parse_startbox_calendar(STARTBOX_CALENDAR, as_of=date(2026, 5, 16))

        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].name, "Lynnleigh Farm May 16, 2026 Schooling 2-Phase")
        self.assertEqual(events[0].location, "Sandy, UT US")
        self.assertEqual(events[0].status, "live")
        self.assertEqual(events[1].starts_on, date(2026, 5, 16))
        self.assertEqual(events[1].ends_on, date(2026, 5, 17))
        self.assertEqual(events[2].score_status, "times")
        self.assertEqual(events[2].status, "upcoming")

    def test_parse_startbox_event_page_extracts_division_links(self):
        divisions = parse_startbox_event_page(RAM_TAP_EVENT_PAGE)

        self.assertEqual(len(divisions), 2)
        self.assertEqual(divisions[0].name, "Open Training")
        self.assertEqual(divisions[0].phase_status, "Dressage: 7:30 AM Sat. Ring 1")
        self.assertIn("draw.php?division=5", divisions[0].entry_status_url)
        self.assertIn("times.php?division=5", divisions[0].times_url)

    def test_parse_startbox_html_preserves_show_names_and_links(self):
        events = parse_startbox_calendar(STARTBOX_HTML_CALENDAR, as_of=date(2026, 5, 16))
        divisions = parse_startbox_event_page(
            STARTBOX_HTML_EVENT_PAGE,
            base_url="https://eventing.startboxscoring.com/eventsu/ramtap/sht0526",
        )

        self.assertEqual(events[0].name, "Ram Tap May SHT")
        self.assertEqual(events[0].location, "Fresno, CA US")
        self.assertEqual(divisions[0].phase_status, "XC: 2:00 PM Sat.")
        self.assertEqual(divisions[0].times_url, "https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/times.php?division=5")
        self.assertEqual(
            divisions[0].scores_url,
            "https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/dressResultsEventing.php?division=5&order=place",
        )

    def test_parse_startbox_event_leaders_extracts_current_scores(self):
        entries = parse_startbox_event_leaders(
            STARTBOX_HTML_EVENT_PAGE,
            base_url="https://eventing.startboxscoring.com/eventsu/ramtap/sht0526",
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].rider_name, "Alexis Concolino")
        self.assertEqual(entries[0].horse_name, "Leo D")
        self.assertEqual(entries[0].score["totalPenalties"], 30.3)

    def test_parse_startbox_scores_page_extracts_scored_rows(self):
        entries = parse_startbox_scores_page(STARTBOX_SCORE_PAGE, division="Modified", status="final")

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].horse_name, "Jaxi")
        self.assertEqual(entries[0].score["dressagePenalties"], 36.8)
        self.assertEqual(entries[0].score["totalPenalties"], 36.8)
        self.assertEqual(entries[1].horse_name, "Brazen Bugatti")
        self.assertIsNone(entries[1].score["totalPenalties"])

    def test_build_live_snapshot_serializes_events(self):
        events = parse_startbox_calendar(STARTBOX_CALENDAR, as_of=date(2026, 5, 16))[:1]
        snapshot = build_live_snapshot(
            events,
            generated_at=datetime(2026, 5, 16, 14, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(snapshot["generated_at"], "2026-05-16T14:01:00Z")
        self.assertEqual(snapshot["events"][0]["source_id"], "startbox_scoring")
        self.assertEqual(snapshot["events"][0]["entries"], [])


if __name__ == "__main__":
    unittest.main()
