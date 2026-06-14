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
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertIn("starter", registry.coverage_targets.domestic_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.domestic_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.international_event_levels)
        self.assertIn("championship", registry.coverage_targets.international_event_levels)
        self.assertEqual(len(registry.sources), 14)

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
            "south_america": "south_america_national_federations",
            "asia": "asia_national_federations",
            "africa": "africa_national_federations",
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

    def test_country_lookup_includes_regional_and_global_backfill(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("south_america_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_priority_country_lookup_includes_specific_federation(self):
        source_ids = [source.id for source in sources_for_country("GBR")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("europe_national_federations", source_ids)
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_routes_domestic_and_fei_levels(self):
        starter_source_ids = [source.id for source in sources_for_event_level("starter")]
        fei_source_ids = [source.id for source in sources_for_event_level("CCI5*-L")]

        self.assertNotIn("data_fei", starter_source_ids)
        self.assertIn("global_national_federations", starter_source_ids)
        self.assertIn("british_eventing", starter_source_ids)
        self.assertEqual(fei_source_ids, ["data_fei"])

    def test_active_only_event_level_filter_keeps_current_fei_source(self):
        self.assertEqual(
            [source.id for source in sources_for_event_level("cci5_long", include_planned=False)],
            ["data_fei"],
        )
        self.assertEqual(
            [source.id for source in sources_for_event_level("starter", include_planned=False)],
            [],
        )


if __name__ == "__main__":
    unittest.main()
