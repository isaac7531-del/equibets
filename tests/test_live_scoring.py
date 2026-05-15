import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from equibets.live_scoring import (
    build_live_score_snapshot,
    parse_startbox_archive,
    parse_startbox_leaders,
    write_live_score_snapshot,
)


ARCHIVE_TEXT = """
| May. 16, 2026 | [Times](http://eventingscores.com/eventsu/ramtap/sht0526) | Ram Tap May SHT Fresno, CA US |
| May. 10, 2026 | [Results](http://eventingscores.com/eventsu/huntersrun/db0526) | Hunters Run Derby Metamora, MI US |
| Apr. 26, 2026 | [Results](http://eventingscores.com/eventsu/feather/ht0426) | Feather Creek Farm Spring Horse Trial Norman, OK US |
| May. 23, 2026 | [Entries](http://eventingscores.com/eventsr/willowdraw/ht0526) | Sol Events at Willow Draw Weatherford, TX US |
"""

EVENT_TEXT = """
# Hunters Run Derby

## May 10, 2026 - Metamora, MI

| Division | Phase | Current Leader |
| --- | --- | --- |
| Rider | Horse | Score |
| Training | [Times](https://eventing.startboxscoring.com/eventsu/huntersrun/db0526/times.php?division=1) [Scores](https://eventing.startboxscoring.com/eventsu/huntersrun/db0526/phase2_select.php?division=1&order=place) Stadium: 2:00 PM Sun. | Reagan Richards | FE Sparkling Diamond | 28.5 |
| BNovice A | [Final Scores](https://eventing.startboxscoring.com/eventsu/huntersrun/db0526/final_select.php?division=3&order=place) | Katie Atkinson | Vortex Rising | 37.7 |
| Thoroughbred Incentive Program (TIP) |
"""

ARCHIVE_HTML = """
<table class="calendar">
<tr class="drawdata2">
<td class="caldate">May. 16, 2026</td>
<td class="calresults"><a href='http://eventingscores.com/eventsu/lynnleigh/sht0526'>Times</a></td>
<td><span class="calshowname">Lynnleigh Farm May 16, 2026 Schooling 2-Phase</span><br />
<span class="callocation">Sandy, UT US</span></td>
</tr>
<tr class="drawdata1">
<td class="caldate">May. 10, 2026</td>
<td class="calresults"><a href='http://eventingscores.com/eventsu/huntersrun/db0526'>Results</a></td>
<td><span class="calshowname">Hunters Run Derby</span><br /><span class="callocation">Metamora, MI US</span></td>
</tr>
</table>
"""

EVENT_HTML = """
<div id="shownamediv">
<h1 class="showname">Hunters Run Derby</h1>
<h2 class="">May 10, 2026 - Metamora, MI</h2>
</div>
<table id="leaderboard1">
<tr>
<td class="divisionldr" rowspan="2">Division</td>
<td class="phase" rowspan="2">Phase</td>
<td class="leaderinfo" colspan="3">Current Leader</td>
</tr>
<tr class="toprow"><td>Rider</td><td>Horse</td><td>Score</td></tr>
<tr class="drawdata1">
<td class="bold">Training</td>
<td><a href="times.php?division=1">Times</a> <a href="phase2_select.php?division=1&amp;order=place">Scores</a><br />
<span class="smaller">Stadium: 2:00 PM Sun.</span></td>
<td>Reagan Richards</td><td>FE Sparkling Diamond</td><td class="center place">28.5</td>
</tr>
<tr class="drawdata2">
<td class="bold">BNovice A</td>
<td><a href="final_select.php?division=3&amp;order=place">Final Scores</a></td>
<td>Katie Atkinson</td><td>Vortex Rising</td><td class="center place">37.7</td>
</tr>
</table>
"""


class LiveScoringTests(unittest.TestCase):
    def test_parse_archive_discovers_current_results_and_times(self):
        events = parse_startbox_archive(ARCHIVE_TEXT, as_of=date(2026, 5, 15))

        self.assertEqual([event.event_name for event in events], ["Hunters Run Derby Metamora, MI US", "Ram Tap May SHT Fresno, CA US"])
        self.assertEqual(events[0].status, "results")
        self.assertEqual(events[1].status, "times")

    def test_parse_archive_accepts_startbox_html(self):
        events = parse_startbox_archive(ARCHIVE_HTML, as_of=date(2026, 5, 15))

        self.assertEqual([event.event_name for event in events], ["Hunters Run Derby Metamora, MI US", "Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US"])
        self.assertEqual(events[0].source_url, "http://eventingscores.com/eventsu/huntersrun/db0526")
        self.assertEqual(events[1].status, "times")

    def test_parse_startbox_leaders_extracts_current_division_leaders(self):
        leaders = parse_startbox_leaders(
            EVENT_TEXT,
            source_url="http://eventingscores.com/eventsu/huntersrun/db0526",
            collected_at=datetime(2026, 5, 15, 20, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(len(leaders), 2)
        self.assertEqual(leaders[0].event_name, "Hunters Run Derby")
        self.assertEqual(leaders[0].event_date, date(2026, 5, 10))
        self.assertEqual(leaders[0].phase, "Final")
        self.assertEqual(leaders[0].rider_name, "Katie Atkinson")
        self.assertEqual(leaders[0].score, 37.7)
        self.assertEqual(leaders[1].phase, "Stadium")

    def test_parse_startbox_leaders_accepts_startbox_html(self):
        leaders = parse_startbox_leaders(
            EVENT_HTML,
            source_url="http://eventingscores.com/eventsu/huntersrun/db0526",
            collected_at=datetime(2026, 5, 15, 20, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(len(leaders), 2)
        self.assertEqual(leaders[0].event_name, "Hunters Run Derby")
        self.assertEqual(leaders[0].phase, "Final")
        self.assertEqual(leaders[0].horse_name, "Vortex Rising")
        self.assertEqual(leaders[1].phase, "Stadium")

    def test_snapshot_groups_leaders_by_event(self):
        leaders = parse_startbox_leaders(
            EVENT_TEXT,
            source_url="http://eventingscores.com/eventsu/huntersrun/db0526",
            collected_at=datetime(2026, 5, 15, 20, 1, tzinfo=timezone.utc),
        )

        snapshot = build_live_score_snapshot(
            leaders,
            generated_at=datetime(2026, 5, 15, 20, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(snapshot["generated_at"], "2026-05-15T20:01:00Z")
        self.assertEqual(snapshot["summary"], {"event_count": 1, "leader_count": 2})
        event = snapshot["events"][0]
        self.assertEqual(event["event_name"], "Hunters Run Derby")
        self.assertEqual(event["leaders"][0]["horse_name"], "FE Sparkling Diamond")

    def test_write_live_score_snapshot_creates_output_path(self):
        leaders = parse_startbox_leaders(
            EVENT_TEXT,
            source_url="http://eventingscores.com/eventsu/huntersrun/db0526",
            collected_at=datetime(2026, 5, 15, 20, 1, tzinfo=timezone.utc),
        )

        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "nested" / "live_scores.json"
            snapshot = write_live_score_snapshot(
                leaders,
                output_path,
                generated_at=datetime(2026, 5, 15, 20, 1, tzinfo=timezone.utc),
            )

            self.assertTrue(output_path.exists())
            self.assertEqual(snapshot["summary"]["leader_count"], 2)


if __name__ == "__main__":
    unittest.main()
