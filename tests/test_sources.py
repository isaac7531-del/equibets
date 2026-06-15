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
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertEqual(
            registry.coverage_targets.domestic_event_levels,
            (
                "starter",
                "beginner_novice",
                "novice",
                "training",
                "modified",
                "preliminary",
                "intermediate",
                "advanced",
                "regional",
                "national",
                "national_one_star",
                "national_two_star",
                "national_three_star",
                "national_four_star",
                "national_five_star",
            ),
        )
        self.assertIn("cci5_long", registry.coverage_targets.international_event_levels)
        self.assertIn("championship", registry.coverage_targets.all_event_levels)

    def test_data_fei_is_primary_source_for_all_international_targets(self):
        registry = load_event_source_registry()
        sources = load_event_sources()

        self.assertEqual(sources[0].id, registry.primary_source_id)
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(
            set(sources[0].event_levels),
            set(registry.coverage_targets.international_event_levels),
        )

    def test_planned_national_sources_cover_all_domestic_targets(self):
        registry = load_event_source_registry()
        domestic_levels = set(registry.coverage_targets.domestic_event_levels)

        for source in registry.sources:
            if source.scope != "national":
                continue

            with self.subTest(source_id=source.id):
                self.assertEqual(set(source.event_levels), domestic_levels)

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

    def test_country_queries_include_global_backfill_for_any_fei_nation(self):
        usa_source_ids = [source.id for source in sources_for_country("usa")]
        other_source_ids = [source.id for source in sources_for_country("KEN")]

        self.assertEqual(usa_source_ids[0], "data_fei")
        self.assertIn("usea", usa_source_ids)
        self.assertIn("global_national_federations", usa_source_ids)
        self.assertEqual(other_source_ids, ["data_fei", "global_national_federations"])

    def test_event_level_queries_return_matching_sources(self):
        advanced_source_ids = [source.id for source in sources_for_event_level("Advanced")]
        cci5_source_ids = [source.id for source in sources_for_event_level("CCI5-Long")]

        self.assertNotIn("data_fei", advanced_source_ids)
        self.assertIn("global_national_federations", advanced_source_ids)
        self.assertEqual(cci5_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
