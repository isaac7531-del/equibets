"""Tests for ShowConnect scoringLive parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.showconnect import (
    ShowConnectEvent,
    parse_scoring_live,
    scoring_live_url,
    spokane_fall_2026_event,
    twin_rivers_fall_2026_event,
)


SAMPLE_TWIN_RIVERS_PAYLOAD = {
    "EventDetails": {
        "ShowConnectId": 1193,
        "USEAEventId": "19089",
        "EventName": "Twin Rivers Fall International",
        "EventDate": "Sep 17 - Sep 20, 2026",
    },
    "DivisionsList": [
        {"DivisionId": 4064, "DivisionName": "CCI4*-Short"},
        {"DivisionId": 4076, "DivisionName": "CCI3*-Short"},
        {"DivisionId": 4124, "DivisionName": "Young Event Horse 5 Year-Old"},
        {"DivisionId": 4160, "DivisionName": "Non-Compete"},
        {"DivisionId": 4103, "DivisionName": "Open Intermediate"},
    ],
    "ScoringList": [
        {
            "CRID": 39119,
            "DivisionId": 4064,
            "Pinny": 1,
            "HorseName": "Danito",
            "RiderName": "Tamra Smith",
            "RiderIso2": "us",
            "DressageScore": "26.3",
            "SJJumpPenalty": "8",
            "SJTimePenalty": "0.8",
            "XCJumpPenalty": "0",
            "XCTimePenalty": "11.20",
        },
        {
            "CRID": 39121,
            "DivisionId": 4064,
            "Pinny": 3,
            "HorseName": "Jump To Day D",
            "RiderName": "Tamra Smith",
            "RiderIso2": "us",
            "DressageScore": "32.9",
            "SJJumpPenalty": "0",
            "SJTimePenalty": "0.8",
            "XCJumpPenalty": "60",
            "XCTimePenalty": "E",
        },
        {
            "CRID": 39122,
            "DivisionId": 4064,
            "Pinny": 5,
            "HorseName": "Camarillo",
            "RiderName": "Brennan Kappes",
            "RiderIso2": "us",
            "DressageScore": "47.4",
            "SJJumpPenalty": "--",
            "SJTimePenalty": "W",
            "XCJumpPenalty": "--",
            "XCTimePenalty": "--",
        },
        {
            "CRID": 40001,
            "DivisionId": 4076,
            "Pinny": 10,
            "HorseName": "Made by Leontine EB",
            "RiderName": "James Alliston",
            "RiderIso2": "us",
            "DressageScore": "30.8",
            "SJJumpPenalty": "0",
            "SJTimePenalty": "0",
            "XCJumpPenalty": "0",
            "XCTimePenalty": "0",
        },
        {
            "CRID": 41001,
            "DivisionId": 4103,
            "Pinny": 20,
            "HorseName": "Justiz-ESH",
            "RiderName": "India McEvoy-Chisholm",
            "RiderIso2": "us",
            "DressageScore": "20.7",
            "SJJumpPenalty": "4",
            "SJTimePenalty": "0",
            "XCJumpPenalty": "0",
            "XCTimePenalty": "13.2",
        },
        {
            "CRID": 42001,
            "DivisionId": 4124,
            "Pinny": 101,
            "HorseName": "YEH Prospect",
            "RiderName": "Example Rider",
            "RiderIso2": "us",
            "DressageScore": "27.0",
            "SJJumpPenalty": "--",
            "SJTimePenalty": "--",
            "XCJumpPenalty": "--",
            "XCTimePenalty": "--",
        },
        {
            "CRID": 43001,
            "DivisionId": 4160,
            "Pinny": 200,
            "HorseName": "Schooling Horse",
            "RiderName": "Example Rider",
            "RiderIso2": "us",
            "DressageScore": "33.0",
            "SJJumpPenalty": "--",
            "SJTimePenalty": "--",
            "XCJumpPenalty": "--",
            "XCTimePenalty": "--",
        },
        {
            "CRID": 44001,
            "DivisionId": 4064,
            "Pinny": 9,
            "HorseName": "No Dressage Yet",
            "RiderName": "Later Starter",
            "RiderIso2": "us",
            "DressageScore": "--",
            "SJJumpPenalty": "--",
            "SJTimePenalty": "--",
            "XCJumpPenalty": "--",
            "XCTimePenalty": "--",
        },
    ],
}


class ShowConnectParseTests(unittest.TestCase):
    def test_twin_rivers_event_uses_showconnect_1193(self):
        event = twin_rivers_fall_2026_event()
        self.assertEqual(event.show_connect_id, 1193)
        self.assertEqual(event.event_title, "Twin Rivers")
        self.assertEqual(event.event_date, date(2026, 9, 17))
        self.assertEqual(event.country, "USA")
        self.assertIn("/event/1193/scoringLive", scoring_live_url(event.show_connect_id))

    def test_spokane_event_uses_showconnect_1194(self):
        event = spokane_fall_2026_event()
        self.assertEqual(event.show_connect_id, 1194)
        self.assertEqual(event.event_title, "Spokane")
        self.assertEqual(event.event_date, date(2026, 9, 24))
        self.assertEqual(event.country, "USA")
        self.assertIn("/event/1194/scoringLive", scoring_live_url(event.show_connect_id))

    def test_numeric_phase_cells_are_ingested_and_placeholders_skipped(self):
        event = ShowConnectEvent(
            show_connect_id=1193,
            event_title="Twin Rivers",
            event_date=date(2026, 9, 17),
            country="USA",
        )
        results = parse_scoring_live(
            SAMPLE_TWIN_RIVERS_PAYLOAD,
            event=event,
            collected_at=datetime(2026, 9, 19, 21, 10, tzinfo=timezone.utc),
        )

        by_horse = {result.horse_name: result for result in results}
        self.assertEqual(set(by_horse), {"Danito", "Jump To Day D", "Camarillo", "Made by Leontine EB"})

        leader = by_horse["Danito"]
        self.assertEqual(leader.rider_name, "Tamra Smith")
        self.assertEqual(leader.event_name, "Twin Rivers · CCI4*-S")
        self.assertEqual(leader.level, "CCI4*-S")
        self.assertEqual(leader.dressage_score, 26.3)
        self.assertEqual(leader.show_jumping_penalties, 8.8)
        self.assertEqual(leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(leader.cross_country_time_penalties, 11.2)
        self.assertEqual(leader.finishing_score, 46.3)
        self.assertEqual(leader.source_id, "showconnect")
        self.assertTrue(leader.source_record_id.startswith("showconnect:"))

        eliminated = by_horse["Jump To Day D"]
        self.assertEqual(eliminated.show_jumping_penalties, 0.8)
        self.assertEqual(eliminated.cross_country_jump_penalties, 60.0)
        self.assertEqual(eliminated.cross_country_time_penalties, 0.0)
        self.assertEqual(eliminated.finishing_score, 93.7)

        withdrawn = by_horse["Camarillo"]
        self.assertEqual(withdrawn.show_jumping_penalties, 0.0)
        self.assertEqual(withdrawn.cross_country_jump_penalties, 0.0)
        self.assertEqual(withdrawn.finishing_score, 47.4)

        clear = by_horse["Made by Leontine EB"]
        self.assertEqual(clear.event_name, "Twin Rivers · CCI3*-S")
        self.assertEqual(clear.finishing_score, 30.8)
