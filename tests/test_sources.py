import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source.id, "data_fei")
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertIn("starter", registry.coverage_targets.domestic_event_levels)
        self.assertIn("advanced", registry.coverage_targets.domestic_event_levels)
        self.assertIn(
            "national_five_star",
            registry.coverage_targets.domestic_event_levels,
        )
        self.assertIn("cci1_short", registry.coverage_targets.international_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.international_event_levels)
        self.assertIn("championship", registry.coverage_targets.international_event_levels)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn("cci5_long", sources[0].event_levels)

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "middle_east": "middle_east_national_federations",
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
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

    def test_country_lookup_includes_primary_specific_and_global_sources(self):
        expected_country_sources = {
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
        }

        for country, national_source_id in expected_country_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_includes_international_and_domestic_scopes(self):
        cci_sources = [source.id for source in sources_for_event_level("CCI5*-L")]
        starter_sources = [source.id for source in sources_for_event_level("Starter")]

        self.assertEqual(cci_sources[0], "data_fei")
        self.assertIn("british_eventing", starter_sources)
        self.assertIn("global_national_federations", starter_sources)
        self.assertNotIn("data_fei", starter_sources)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
