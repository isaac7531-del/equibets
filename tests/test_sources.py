import unittest

from equibets.sources import (
    NATIONAL_EVENT_LEVELS,
    load_event_sources,
    load_national_event_levels,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


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

    def test_global_national_source_covers_all_countries(self):
        source_ids = [source.id for source in sources_for_country("CAN")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_country_sources_include_exact_national_match(self):
        source_ids = [source.id for source in sources_for_country("GBR")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_national_sources_cover_all_configured_levels(self):
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertGreater(len(national_sources), 0)
        for source in national_sources:
            with self.subTest(source_id=source.id):
                self.assertEqual(source.event_levels, NATIONAL_EVENT_LEVELS)

    def test_national_level_taxonomy_is_loaded_from_registry(self):
        self.assertEqual(load_national_event_levels(), NATIONAL_EVENT_LEVELS)

    def test_sources_for_event_level_matches_canonical_level_names(self):
        source_ids = [source.id for source in sources_for_event_level("state-provincial")]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertIn("usea", source_ids)


if __name__ == "__main__":
    unittest.main()
