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
        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)

        domestic_levels = registry.coverage_targets.domestic_event_levels
        self.assertIn("starter", domestic_levels)
        self.assertIn("advanced", domestic_levels)
        self.assertIn("national_five_star", domestic_levels)

        fei_levels = registry.coverage_targets.fei_event_levels
        self.assertIn("cci1_introductory", fei_levels)
        self.assertIn("cci3_short", fei_levels)
        self.assertIn("cci5_long", fei_levels)
        self.assertIn("championship", fei_levels)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_all_priority_regions_include_fei_and_national_sources(self):
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

    def test_country_sources_include_global_and_priority_country_feeds(self):
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

        source_ids = [source.id for source in sources_for_country("BRA")]
        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

        source_ids = [
            source.id
            for source in sources_for_country("all_fei_south_america_member_nations")
        ]
        self.assertIn("south_america_national_federations", source_ids)

    def test_every_declared_domestic_level_has_national_backfill(self):
        registry = load_event_source_registry()

        for level in registry.coverage_targets.domestic_event_levels:
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_event_level(level)]
                self.assertIn("global_national_federations", source_ids)

    def test_every_declared_fei_level_uses_data_fei(self):
        registry = load_event_source_registry()

        for level in registry.coverage_targets.fei_event_levels:
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_event_level(level)]
                self.assertEqual(source_ids[0], "data_fei")

    def test_common_event_level_labels_normalize_to_registry_tokens(self):
        self.assertEqual(
            [source.id for source in sources_for_event_level("CCI5*-L")],
            ["data_fei"],
        )
        self.assertEqual(
            [source.id for source in sources_for_event_level("CCI3*-S")],
            ["data_fei"],
        )
        self.assertIn(
            "global_national_federations",
            [source.id for source in sources_for_event_level("National 3*")],
        )

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

        source_ids = [
            source.id
            for source in sources_for_event_level("CCI5*-L", include_planned=False)
        ]
        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
