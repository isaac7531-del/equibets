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
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertEqual(len(registry.sources), 13)
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
        self.assertEqual(
            registry.coverage_targets.fei_event_levels,
            (
                "fei_international",
                "cci_intro",
                "cci1_intro",
                "cci1_short",
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

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn("cci5_long", sources[0].event_levels)

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

    def test_country_sources_include_all_country_backfill(self):
        expected_country_sources = {
            "USA": "usea",
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
        }

        for country, national_source_id in expected_country_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

        self.assertEqual(
            [source.id for source in sources_for_country("BRA")],
            ["data_fei", "global_national_federations"],
        )

    def test_all_declared_event_levels_have_a_source_path(self):
        registry = load_event_source_registry()

        for level in registry.coverage_targets.domestic_event_levels:
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_event_level(level)]
                self.assertIn("global_national_federations", source_ids)

        for level in registry.coverage_targets.fei_event_levels:
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_event_level(level)]
                self.assertEqual(source_ids, ["data_fei"])

        self.assertIn(
            "global_national_federations",
            [source.id for source in sources_for_event_level("Beginner Novice")],
        )

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])
        self.assertEqual(
            [source.id for source in sources_for_event_level("cci5-long", include_planned=False)],
            ["data_fei"],
        )
        self.assertEqual(sources_for_event_level("starter", include_planned=False), [])


if __name__ == "__main__":
    unittest.main()
