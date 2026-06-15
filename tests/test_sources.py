import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_and_level_coverage(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertIn("starter", registry.coverage_targets.domestic_event_levels)
        self.assertIn("advanced", registry.coverage_targets.domestic_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.domestic_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_event_levels)
        self.assertIn("championship", registry.coverage_targets.fei_event_levels)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_national_sources_cover_all_domestic_levels(self):
        registry = load_event_source_registry()
        domestic_levels = set(registry.coverage_targets.domestic_event_levels)

        for source in registry.sources:
            if source.scope == "national":
                with self.subTest(source=source.id):
                    self.assertTrue(domestic_levels.issubset(source.event_levels))

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

    def test_country_lookup_includes_priority_regional_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("GBR")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("europe_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_covers_non_priority_fei_member_nations(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("south_america_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_level_lookup_distinguishes_domestic_and_fei_levels(self):
        domestic_source_ids = [source.id for source in sources_for_event_level("Beginner Novice")]
        fei_source_ids = [source.id for source in sources_for_event_level("CCI4*-L")]

        self.assertIn("usea", domestic_source_ids)
        self.assertIn("global_national_federations", domestic_source_ids)
        self.assertNotIn("data_fei", domestic_source_ids)
        self.assertEqual(fei_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
