import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


NATIONAL_LEVELS = (
    "starter",
    "introductory",
    "beginner_novice",
    "novice",
    "training",
    "modified",
    "preliminary",
    "intermediate",
    "advanced",
    "national_one_star",
    "national_two_star",
    "national_three_star",
    "national_four_star",
    "national_five_star",
)

INTERNATIONAL_LEVELS = (
    "cci1_intro",
    "cci1",
    "cci2_s",
    "cci2_l",
    "cci3_s",
    "cci3_l",
    "cci4_s",
    "cci4_l",
    "cci5_l",
    "championship",
)


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertEqual(registry.coverage_targets.national_event_levels, NATIONAL_LEVELS)
        self.assertEqual(
            registry.coverage_targets.international_event_levels,
            INTERNATIONAL_LEVELS,
        )

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].event_levels, INTERNATIONAL_LEVELS)

    def test_national_sources_cover_all_domestic_levels(self):
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertGreaterEqual(len(national_sources), 1)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, NATIONAL_LEVELS)

    def test_priority_regions_include_fei_and_national_sources(self):
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

    def test_all_global_regions_include_national_backfill(self):
        expected_regional_sources = {
            "north_america": "north_america_national_federations",
            "central_america_caribbean": "central_america_caribbean_national_federations",
            "south_america": "south_america_national_federations",
            "africa": "africa_national_federations",
            "middle_east": "middle_east_national_federations",
            "asia": "asia_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, regional_source_id in expected_regional_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(regional_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_keeps_global_backfill_for_any_country(self):
        source_ids = [source.id for source in sources_for_country("FRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_direct_priority_source(self):
        source_ids = [source.id for source in sources_for_country("gbr")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_level_lookup_returns_sources_for_domestic_and_fei_levels(self):
        national_source_ids = [
            source.id for source in sources_for_event_level("Beginner Novice")
        ]
        international_source_ids = [
            source.id for source in sources_for_event_level("CCI4-S")
        ]

        self.assertIn("global_national_federations", national_source_ids)
        self.assertIn("data_fei", international_source_ids)
        self.assertNotIn("data_fei", national_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
