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

    def test_registry_targets_all_countries_regions_and_levels(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertEqual(
            registry.coverage_targets.regions,
            (
                "africa",
                "asia",
                "europe",
                "middle_east",
                "north_america",
                "south_america",
                "oceania",
            ),
        )
        self.assertIn("starter", registry.coverage_targets.national_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.national_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_event_levels)
        self.assertIn("championship", registry.coverage_targets.event_levels)

    def test_all_target_regions_include_fei_regional_and_global_sources(self):
        expected_regional_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, regional_source_id in expected_regional_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(regional_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_priority_country_alias_regions_include_country_sources(self):
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

    def test_country_lookup_includes_primary_exact_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("gbr")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_backfills_unprioritized_fei_nations(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_event_level_lookup_separates_fei_and_domestic_levels(self):
        fei_source_ids = [source.id for source in sources_for_event_level("CCI5 Long")]
        domestic_source_ids = [
            source.id for source in sources_for_event_level("beginner-novice")
        ]

        self.assertEqual(fei_source_ids, ["data_fei"])
        self.assertNotIn("data_fei", domestic_source_ids)
        self.assertIn("global_national_federations", domestic_source_ids)
        self.assertIn("north_america_national_federations", domestic_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
