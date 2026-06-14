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
        self.assertIn("starter", registry.coverage_targets.domestic_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.domestic_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_event_levels)
        self.assertIn("championship", registry.coverage_targets.fei_event_levels)

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "uk": "british_eventing",
            "australia": "equestrian_australia",
            "new_zealand": "equestrian_sports_new_zealand",
            "usa": "usea",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "asia": "asia_national_federations",
            "africa": "africa_national_federations",
            "middle_east": "middle_east_national_federations",
            "central_america_caribbean": "central_america_caribbean_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_global_and_regional_national_sources(self):
        expectations = {
            "GBR": "british_eventing",
            "CAN": "north_america_national_federations",
            "BRA": "south_america_national_federations",
            "JPN": "asia_national_federations",
            "RSA": "africa_national_federations",
            "UAE": "middle_east_national_federations",
            "JAM": "central_america_caribbean_national_federations",
            "FIJ": "oceania_national_federations",
        }

        for country_code, national_source_id in expectations.items():
            with self.subTest(country_code=country_code):
                source_ids = [source.id for source in sources_for_country(country_code)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_keeps_country_specific_sources_ahead_of_backfill(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertLess(source_ids.index("usea"), source_ids.index("global_national_federations"))

    def test_event_level_lookup_resolves_broad_level_targets(self):
        domestic_source_ids = [source.id for source in sources_for_event_level("advanced")]
        fei_source_ids = [source.id for source in sources_for_event_level("CCI5-LONG")]

        self.assertNotIn("data_fei", domestic_source_ids)
        self.assertIn("global_national_federations", domestic_source_ids)
        self.assertEqual(fei_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
