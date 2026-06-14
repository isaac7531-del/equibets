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

    def test_registry_targets_every_fei_country_and_event_level(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertEqual(
            set(registry.coverage_targets.domestic_event_levels),
            {
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
            },
        )
        self.assertEqual(
            set(registry.coverage_targets.international_event_levels),
            {
                "fei_international",
                "cci_intro",
                "cci1_short",
                "cci2_short",
                "cci2_long",
                "cci3_short",
                "cci3_long",
                "cci4_short",
                "cci4_long",
                "cci5_long",
                "championship",
            },
        )

    def test_sources_cover_declared_domestic_and_international_levels(self):
        registry = load_event_source_registry()
        sources_by_id = {source.id: source for source in registry.sources}

        self.assertEqual(
            set(sources_by_id["data_fei"].event_levels),
            set(registry.coverage_targets.international_event_levels),
        )

        domestic_source_ids = {
            "europe_national_federations",
            "africa_national_federations",
            "middle_east_national_federations",
            "asia_national_federations",
            "oceania_national_federations",
            "north_america_national_federations",
            "central_america_caribbean_national_federations",
            "south_america_national_federations",
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
            "global_national_federations",
        }
        for source_id in domestic_source_ids:
            with self.subTest(source_id=source_id):
                self.assertEqual(
                    set(sources_by_id[source_id].event_levels),
                    set(registry.coverage_targets.domestic_event_levels),
                )

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "africa": "africa_national_federations",
            "middle_east": "middle_east_national_federations",
            "asia": "asia_national_federations",
            "oceania": "oceania_national_federations",
            "north_america": "north_america_national_federations",
            "central_america_caribbean": (
                "central_america_caribbean_national_federations"
            ),
            "south_america": "south_america_national_federations",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_priority_countries_include_dedicated_and_global_sources(self):
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

    def test_any_fei_country_uses_primary_and_global_backfill_sources(self):
        source_ids = [source.id for source in sources_for_country("FRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_event_level_selects_matching_level_group(self):
        domestic_source_ids = [
            source.id for source in sources_for_event_level("national_five_star")
        ]
        international_source_ids = [
            source.id for source in sources_for_event_level("cci5_long")
        ]

        self.assertNotIn("data_fei", domestic_source_ids)
        self.assertIn("global_national_federations", domestic_source_ids)
        self.assertEqual(international_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
