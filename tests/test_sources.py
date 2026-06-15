import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
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

    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()
        source_by_id = {source.id: source for source in registry.sources}

        self.assertEqual(registry.version, 2)
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertIn("starter", registry.coverage_targets.domestic_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.domestic_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.international_event_levels)
        self.assertIn("championship", registry.coverage_targets.international_event_levels)

        self.assertTrue(
            set(registry.coverage_targets.domestic_event_levels).issubset(
                source_by_id["global_national_federations"].event_levels
            )
        )
        self.assertTrue(
            set(registry.coverage_targets.international_event_levels).issubset(
                source_by_id["data_fei"].event_levels
            )
        )

    def test_priority_regions_include_fei_regional_and_global_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
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

    def test_country_lookup_includes_country_specific_and_global_sources(self):
        usa_source_ids = [source.id for source in sources_for_country("usa")]
        brazil_source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(usa_source_ids[0], "data_fei")
        self.assertIn("usea", usa_source_ids)
        self.assertIn("global_national_federations", usa_source_ids)
        self.assertEqual(brazil_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", brazil_source_ids)

    def test_event_level_lookup_separates_domestic_and_fei_levels(self):
        starter_source_ids = [source.id for source in sources_for_event_level("starter")]
        cci5_source_ids = [source.id for source in sources_for_event_level("cci5_long")]

        self.assertNotIn("data_fei", starter_source_ids)
        self.assertIn("africa_national_federations", starter_source_ids)
        self.assertIn("global_national_federations", starter_source_ids)
        self.assertEqual(cci5_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
