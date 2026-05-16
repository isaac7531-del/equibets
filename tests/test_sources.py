import unittest

from equibets.sources import load_event_sources, sources_for_region


EXPECTED_NATIONAL_EVENT_LEVELS = {
    "national_championship",
    "national",
    "regional",
    "state_provincial",
    "local",
    "club",
    "grassroots",
    "youth_pony",
    "schooling_training",
}


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "uk": "british_eventing",
            "australia": "equestrian_australia",
            "new_zealand": "equestrian_sports_new_zealand",
            "usa": "usea",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_primary_and_global_sources_cover_all_fei_member_nations(self):
        sources = {source.id: source for source in load_event_sources()}

        for source_id in ("data_fei", "global_national_federations"):
            with self.subTest(source_id=source_id):
                countries = sources[source_id].countries
                self.assertEqual(len(countries), 135)
                self.assertEqual(len(set(countries)), 135)
                self.assertNotIn("all_fei_member_nations", countries)
                self.assertTrue(all(code.isupper() and len(code) == 3 for code in countries))

        global_countries = sources["global_national_federations"].countries
        for priority_country in ("GBR", "AUS", "NZL", "USA"):
            self.assertIn(priority_country, global_countries)

    def test_national_sources_cover_all_domestic_levels(self):
        for source in load_event_sources():
            if source.scope != "national":
                continue

            with self.subTest(source_id=source.id):
                self.assertEqual(set(source.event_levels), EXPECTED_NATIONAL_EVENT_LEVELS)


if __name__ == "__main__":
    unittest.main()
