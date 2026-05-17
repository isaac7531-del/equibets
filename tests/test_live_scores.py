import unittest

from equibets.live_scores import (
    ArchiveEvent,
    parse_event_date_range,
    parse_startbox_archive,
    parse_startbox_event_page,
)


ARCHIVE_MARKDOWN = """
| ### Open/Currently Running |
| --- |
| May.. 16-17, 2026 | [Results](http://eventingscores.com/eventsu/ramtap/sht0526) | Ram Tap May SHT[![Image 1: Website](https://example.test/icon.png)](http://example.test/) Fresno, CA US |
| May. 23, 2026 | [Entries](http://eventingscores.com/eventsr/willowdraw/ht0526) | Sol Events at Willow Draw Weatherford, TX US |
| ### Completed Events |
| May. 16, 2026 | [Results](http://eventingscores.com/eventsu/lynnleigh/sht0526) | Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US |
"""


PIPE_EVENT_MARKDOWN = """
Title: Results for Queeny Park Horse Trials

Markdown Content:
# Queeny Park Horse Trials

## May 9-10, 2026 - St. Louis, MO

| Division | Phase | Current Leader |
| --- | --- | --- |
| Rider | Horse | Score |
| Training by Academy Air | [Final Scores](http://eventingscores.com/eventsr/queeny/final_select.php?division=3&order=place) | Sophia Lieberman | Tazmanian Pegasus | 30.3 |
"""


COLLAPSED_EVENT_MARKDOWN = """
Title: Results for Ram Tap May SHT

Markdown Content:
## May 16-17, 2026 - Fresno, CA

Division Phase Current Leader
Rider Horse Score
Open Training[Times](https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/times.php?division=5)[Scores](https://eventing.startboxscoring.com/eventsu/ramtap/sht0526/phase2_select.php?division=5&order=place)

Stadium: 11:45 AM Sun.Alexis Concolino Leo D 30.3
"""


class LiveScoreParsingTests(unittest.TestCase):
    def test_parses_archive_rows_with_date_ranges_and_links(self):
        events = parse_startbox_archive(ARCHIVE_MARKDOWN)

        self.assertEqual(len(events), 3)
        self.assertEqual(events[0].name, "Ram Tap May SHT")
        self.assertEqual(events[0].status, "current")
        self.assertEqual(events[0].start_date.isoformat(), "2026-05-16")
        self.assertEqual(events[0].end_date.isoformat(), "2026-05-17")
        self.assertEqual(events[0].link_label, "Results")

    def test_parses_date_range_labels(self):
        start_date, end_date = parse_event_date_range("May.. 16-17, 2026")

        self.assertEqual(start_date.isoformat(), "2026-05-16")
        self.assertEqual(end_date.isoformat(), "2026-05-17")

    def test_parses_pipe_style_event_leader_rows(self):
        archive_event = ArchiveEvent(
            name="Queeny Park Horse Trials",
            date_label="May 9-10, 2026",
            start_date=parse_event_date_range("May 9-10, 2026")[0],
            end_date=parse_event_date_range("May 9-10, 2026")[1],
            status="completed",
            source_url="http://eventingscores.com/eventsr/queeny/ht0526",
            link_label="Results",
        )

        live_event = parse_startbox_event_page(PIPE_EVENT_MARKDOWN, archive_event)

        self.assertEqual(live_event.event_name, "Queeny Park Horse Trials")
        self.assertEqual(live_event.location, "St. Louis, MO")
        self.assertEqual(live_event.leaders[0].rider_name, "Sophia Lieberman")
        self.assertEqual(live_event.leaders[0].horse_name, "Tazmanian Pegasus")
        self.assertEqual(live_event.leaders[0].score, 30.3)

    def test_parses_collapsed_reader_event_leader_rows(self):
        archive_event = ArchiveEvent(
            name="Ram Tap May SHT",
            date_label="May 16-17, 2026",
            start_date=parse_event_date_range("May 16-17, 2026")[0],
            end_date=parse_event_date_range("May 16-17, 2026")[1],
            status="current",
            source_url="http://eventingscores.com/eventsu/ramtap/sht0526",
            link_label="Results",
        )

        live_event = parse_startbox_event_page(COLLAPSED_EVENT_MARKDOWN, archive_event)

        self.assertEqual(live_event.date_label, "May 16-17, 2026")
        self.assertEqual(live_event.leaders[0].division, "Open Training")
        self.assertEqual(live_event.leaders[0].phase, "Scores")
        self.assertEqual(live_event.leaders[0].leader_name, "Alexis Concolino Leo D")
        self.assertEqual(live_event.leaders[0].score_text, "30.3")


if __name__ == "__main__":
    unittest.main()
