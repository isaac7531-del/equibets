import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


DOMESTIC_LEVELS = {
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
}

FEI_LEVELS = {
    "fei_international",
    "cci_introductory",
    "cci1_introductory",
    "cci1_short",
    "cci2_short",
    "cci2_long",
    "cci3_short",
    "cci3_long",
    "cci4_short",
    "cci4_long",
    "cci5_short",
    "cci5_long",
    "championship",
}


class EventSourceTests(unittest.TestCase):
    def test_coverage_targets_include_all_countries_and_event_levels(self):
        registry = load_event_source_registry()

        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertEqual(set(registry.coverage_targets.domestic_event_levels), DOMESTIC_LEVELS)
        self.assertEqual(set(registry.coverage_targets.fei_event_levels), FEI_LEVELS)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(set(sources[0].event_levels), FEI_LEVELS)

    def test_all_regions_include_fei_regional_registry_and_global_backfill(self):
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
                sources = sources_for_region(region)
                source_ids = [source.id for source in sources]
                regional_source = next(source for source in sources if source.id == regional_source_id)

                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(regional_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)
                self.assertEqual(set(regional_source.event_levels), DOMESTIC_LEVELS)

    def test_priority_countries_include_fei_specific_source_and_global_backfill(self):
        expected_national_sources = {
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
        }

        for country, national_source_id in expected_national_sources.items():
            with self.subTest(country=country):
                sources = sources_for_country(country)
                source_ids = [source.id for source in sources]
                national_source = next(source for source in sources if source.id == national_source_id)

                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)
                self.assertEqual(set(national_source.event_levels), DOMESTIC_LEVELS)

    def test_non_priority_country_keeps_global_all_country_backfill(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_separates_domestic_and_fei_coverage(self):
        starter_source_ids = [source.id for source in sources_for_event_level("Beginner Novice")]
        cci_source_ids = [source.id for source in sources_for_event_level("CCI4-LONG")]

        self.assertIn("global_national_federations", starter_source_ids)
        self.assertNotIn("data_fei", starter_source_ids)
        self.assertEqual(cci_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
