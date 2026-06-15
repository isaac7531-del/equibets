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
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertIn("starter", registry.coverage_targets.domestic_event_levels)
        self.assertIn("advanced", registry.coverage_targets.domestic_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.domestic_event_levels)
        self.assertIn("cci1_short", registry.coverage_targets.international_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.international_event_levels)
        self.assertIn("championship", registry.coverage_targets.international_event_levels)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_sources_match_declared_level_targets(self):
        registry = load_event_source_registry()

        for source in registry.sources:
            with self.subTest(source=source.id):
                if source.id == registry.primary_source_id:
                    self.assertEqual(
                        set(source.event_levels),
                        set(registry.coverage_targets.international_event_levels),
                    )
                else:
                    self.assertEqual(
                        set(source.event_levels),
                        set(registry.coverage_targets.domestic_event_levels),
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

    def test_country_lookup_includes_primary_specific_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_backfills_any_fei_member_nation(self):
        source_ids = [source.id for source in sources_for_country("bra")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_covers_domestic_and_international_levels(self):
        domestic_source_ids = [source.id for source in sources_for_event_level("national five star")]
        international_source_ids = [source.id for source in sources_for_event_level("CCI5-LONG")]
        live_fei_long_ids = [source.id for source in sources_for_event_level("CCI5*-L")]
        live_fei_short_ids = [source.id for source in sources_for_event_level("CCI3*-S")]

        self.assertIn("global_national_federations", domestic_source_ids)
        self.assertIn("data_fei", international_source_ids)
        self.assertIn("data_fei", live_fei_long_ids)
        self.assertIn("data_fei", live_fei_short_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
