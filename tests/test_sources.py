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

    def test_coverage_targets_include_all_countries_and_levels(self):
        registry = load_event_source_registry()

        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertIn("starter", registry.coverage_targets.domestic_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.domestic_event_levels)
        self.assertIn("cci1_short", registry.coverage_targets.fei_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_event_levels)

    def test_priority_regions_include_fei_and_national_sources(self):
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

    def test_country_lookup_includes_global_backfill_and_priority_country_sources(self):
        usa_source_ids = [source.id for source in sources_for_country("usa")]
        brazil_source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(usa_source_ids[0], "data_fei")
        self.assertIn("usea", usa_source_ids)
        self.assertIn("global_national_federations", usa_source_ids)
        self.assertEqual(brazil_source_ids, ["data_fei", "global_national_federations"])

    def test_level_lookup_covers_fei_and_every_domestic_level(self):
        registry = load_event_source_registry()

        for level in registry.coverage_targets.domestic_event_levels:
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_event_level(level)]
                self.assertIn("global_national_federations", source_ids)

        cci5_source_ids = [source.id for source in sources_for_event_level("cci5_long")]
        self.assertIn("data_fei", cci5_source_ids)
        display_level_source_ids = [source.id for source in sources_for_event_level("CCI5*-L")]
        self.assertEqual(display_level_source_ids, cci5_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
