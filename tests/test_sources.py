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

    def test_registry_targets_all_countries_and_levels(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_countries",))
        self.assertEqual(
            registry.coverage_targets.national_event_levels,
            (
                "starter",
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
            ),
        )
        self.assertEqual(
            registry.coverage_targets.fei_international_event_levels,
            (
                "cci1_intro",
                "cci1_star",
                "cci2_short",
                "cci2_long",
                "cci3_short",
                "cci3_long",
                "cci4_short",
                "cci4_long",
                "cci5_long",
                "championship",
            ),
        )

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "uk": "british_eventing",
            "australia": "equestrian_australia",
            "new_zealand": "equestrian_sports_new_zealand",
            "usa": "usea",
            "north_america": "north_america_national_federations",
            "latin_america": "latin_america_national_federations",
            "oceania": "oceania_national_federations",
            "asia": "asia_national_federations",
            "middle_east": "middle_east_national_federations",
            "africa": "africa_national_federations",
            "caribbean": "caribbean_national_federations",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_national_sources_cover_all_target_national_levels(self):
        registry = load_event_source_registry()
        target_levels = registry.coverage_targets.national_event_levels

        for source in registry.sources:
            if source.scope == "national":
                with self.subTest(source=source.id):
                    self.assertEqual(source.event_levels, target_levels)

    def test_sources_for_country_include_primary_specific_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_event_level_match_national_and_fei_levels(self):
        national_source_ids = [source.id for source in sources_for_event_level("starter")]
        fei_source_ids = [source.id for source in sources_for_event_level("CCI3 Long")]

        self.assertIn("global_national_federations", national_source_ids)
        self.assertIn("usea", national_source_ids)
        self.assertNotIn("data_fei", national_source_ids)
        self.assertEqual(fei_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
