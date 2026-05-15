import unittest

from equibets.current_events import (
    events_with_live_scores,
    load_current_events,
    search_current_events,
)


class CurrentEventTests(unittest.TestCase):
    def test_loads_pulled_current_events(self):
        events = load_current_events()

        self.assertGreaterEqual(len(events), 3)
        self.assertEqual(events[0].id, "marbach-ccio4-nc-s-2026")
        self.assertEqual(events[0].leader.rider_name, "Michael JUNG")
        self.assertEqual(events[0].leader.live_score, 21.2)

    def test_filters_to_events_with_live_rows(self):
        events = events_with_live_scores()

        self.assertEqual(
            [event.id for event in events],
            ["marbach-ccio4-nc-s-2026", "belsay-international-cci4s-2026"],
        )

    def test_searches_by_rider_horse_and_event(self):
        horse_matches = search_current_events("gypsie")
        event_matches = search_current_events("millstreet")

        self.assertEqual([event.id for event in horse_matches], ["belsay-international-cci4s-2026"])
        self.assertEqual([event.id for event in event_matches], ["millstreet-international-2026"])


if __name__ == "__main__":
    unittest.main()
