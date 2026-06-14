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

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertIn(
            "national_five_star",
            registry.coverage_targets.event_levels["all_national_and_regional_levels"],
        )
        self.assertIn(
            "cci5_long",
            registry.coverage_targets.event_levels["all_fei_international_levels"],
        )

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

    def test_country_lookup_includes_global_backfill_and_exact_priority_sources(self):
        brazil_source_ids = [source.id for source in sources_for_country("BRA")]
        self.assertEqual(brazil_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", brazil_source_ids)

        uk_source_ids = [source.id for source in sources_for_country("gbr")]
        self.assertIn("british_eventing", uk_source_ids)
        self.assertIn("global_national_federations", uk_source_ids)

    def test_event_level_lookup_expands_coverage_targets(self):
        starter_source_ids = [source.id for source in sources_for_event_level("Starter")]
        self.assertNotIn("data_fei", starter_source_ids)
        self.assertIn("global_national_federations", starter_source_ids)
        self.assertIn("usea", starter_source_ids)

        cci_source_ids = [source.id for source in sources_for_event_level("CCI5*-L")]
        self.assertEqual(cci_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_active_only_level_filter_excludes_planned_national_sources(self):
        self.assertEqual(sources_for_event_level("starter", include_planned=False), [])


if __name__ == "__main__":
    unittest.main()
