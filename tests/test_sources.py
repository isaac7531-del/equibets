import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


EXPECTED_NATIONAL_LEVELS = {
    "national_championship",
    "national",
    "state_provincial",
    "regional",
    "area",
    "local",
    "club",
    "schooling",
    "grassroots",
    "youth",
    "pony_club",
}


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "central_america_caribbean": "central_america_caribbean_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
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

    def test_global_national_source_covers_every_country_and_level(self):
        sources = load_event_sources()
        global_source = next(
            source for source in sources if source.id == "global_national_federations"
        )

        self.assertEqual(global_source.countries, ("all_countries",))
        self.assertEqual(set(global_source.event_levels), EXPECTED_NATIONAL_LEVELS)

    def test_sources_for_country_filters_by_country_and_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="grassroots")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_sources_for_country_keeps_country_specific_national_sources(self):
        source_ids = [source.id for source in sources_for_country("GBR", level="club")]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)


if __name__ == "__main__":
    unittest.main()
