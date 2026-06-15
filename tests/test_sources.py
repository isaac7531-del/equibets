import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_targets_all_countries_and_levels(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertIn("starter", registry.coverage_targets.national_and_regional_levels)
        self.assertIn("advanced", registry.coverage_targets.national_and_regional_levels)
        self.assertIn(
            "national_five_star",
            registry.coverage_targets.national_and_regional_levels,
        )
        self.assertIn("cci5_long", registry.coverage_targets.fei_levels)
        self.assertIn("championship", registry.coverage_targets.fei_levels)

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
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
            "asia": "asia_national_federations",
            "middle_east": "middle_east_national_federations",
            "africa": "africa_national_federations",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_includes_regional_and_global_backfills(self):
        expected_country_sources = {
            "GBR": {"europe_national_federations", "british_eventing"},
            "USA": {"north_america_national_federations", "usea"},
            "BRA": {"south_america_national_federations"},
            "ZAF": {"africa_national_federations"},
            "UAE": {"middle_east_national_federations", "asia_national_federations"},
        }

        for country, expected_sources in expected_country_sources.items():
            with self.subTest(country=country):
                source_ids = {source.id for source in sources_for_country(country)}
                self.assertIn("data_fei", source_ids)
                self.assertIn("global_national_federations", source_ids)
                self.assertGreaterEqual(source_ids, expected_sources)

    def test_sources_for_event_level_expands_level_groups(self):
        starter_source_ids = {
            source.id for source in sources_for_event_level("Starter")
        }
        cci_source_ids = {
            source.id for source in sources_for_event_level("CCI5*-L")
        }

        self.assertIn("global_national_federations", starter_source_ids)
        self.assertIn("usea", starter_source_ids)
        self.assertNotIn("data_fei", starter_source_ids)
        self.assertEqual(cci_source_ids, {"data_fei"})

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_active_only_level_filter_keeps_only_current_fei_source(self):
        domestic_source_ids = [
            source.id
            for source in sources_for_event_level("Starter", include_planned=False)
        ]
        international_source_ids = [
            source.id
            for source in sources_for_event_level("CCI5*-L", include_planned=False)
        ]

        self.assertEqual(domestic_source_ids, [])
        self.assertEqual(international_source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
