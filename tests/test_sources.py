import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_tracks_all_country_all_level_coverage(self):
        registry = load_event_source_registry()

        expected_levels = {
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
            "cci1_intro",
            "cci2_short",
            "cci2_long",
            "cci3_short",
            "cci3_long",
            "cci4_short",
            "cci4_long",
            "cci5_long",
            "championship",
        }

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_countries",))
        self.assertEqual(
            set(registry.coverage_targets.event_levels),
            expected_levels,
        )
        self.assertEqual(
            registry.coverage_goal,
            "Collect eventing results from national and international sources "
            "for every country and every configured eventing level.",
        )

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].countries, ("all_countries",))

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "central_america_caribbean": (
                "central_america_caribbean_national_federations"
            ),
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

    def test_national_sources_cover_all_eventing_levels(self):
        registry_source_ids = {
            "africa_national_federations",
            "asia_national_federations",
            "europe_national_federations",
            "middle_east_national_federations",
            "north_america_national_federations",
            "central_america_caribbean_national_federations",
            "south_america_national_federations",
            "oceania_national_federations",
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
            "global_national_federations",
        }
        sources = {
            source.id: source
            for source in load_event_sources()
            if source.scope == "national"
        }

        self.assertEqual(set(sources), registry_source_ids)
        for source in sources.values():
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_sources_for_country_includes_exact_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_backfills_unlisted_countries_by_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="national-three-star")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_sources_for_country_filters_by_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="starter")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_sources_for_country_normalizes_fei_level_spelling(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="cci4-long")
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_region_filters_by_level(self):
        source_ids = [
            source.id
            for source in sources_for_region("north america", level="starter")
        ]

        self.assertEqual(
            source_ids,
            [
                "north_america_national_federations",
                "usea",
                "global_national_federations",
            ],
        )

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
