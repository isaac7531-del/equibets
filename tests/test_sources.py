import unittest

from equibets.sources import (
    GLOBAL_COUNTRY_TOKEN,
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_and_all_level_targets(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertEqual(registry.coverage_targets.countries, GLOBAL_COUNTRY_TOKEN)
        self.assertIn("regional", registry.coverage_targets.domestic_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.domestic_event_levels)
        self.assertIn("fei_international", registry.coverage_targets.fei_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_event_levels)

    def test_source_ids_are_unique_and_primary_source_exists(self):
        registry = load_event_source_registry()
        source_ids = [source.id for source in registry.sources]

        self.assertEqual(len(source_ids), len(set(source_ids)))
        self.assertIn(registry.primary_source_id, source_ids)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn("cci5_long", sources[0].event_levels)

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

    def test_global_region_coverage_includes_every_regional_registry(self):
        expected_regional_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "central_america_caribbean": (
                "central_america_caribbean_national_federations"
            ),
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, national_source_id in expected_regional_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_global_and_regional_coverage(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("south_america_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_priority_country_source(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("north_america_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_separates_domestic_and_fei_levels(self):
        national_source_ids = [
            source.id for source in sources_for_event_level("beginner novice")
        ]
        fei_source_ids = [source.id for source in sources_for_event_level("CCI5 Long")]

        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)
        self.assertEqual(fei_source_ids[0], "data_fei")
        self.assertNotIn("global_national_federations", fei_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
