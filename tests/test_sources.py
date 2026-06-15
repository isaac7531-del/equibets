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
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertIn(
            "beginner_novice",
            registry.coverage_targets.domestic_event_levels,
        )
        self.assertIn(
            "national_five_star",
            registry.coverage_targets.domestic_event_levels,
        )
        self.assertIn("cci5_long", registry.coverage_targets.international_event_levels)
        self.assertEqual(
            len(registry.coverage_targets.all_event_levels),
            len(set(registry.coverage_targets.all_event_levels)),
        )

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn("cci5_long", sources[0].event_levels)

    def test_priority_regions_include_fei_regional_and_global_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "uk": "british_eventing",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
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

    def test_country_lookup_includes_all_country_backfill(self):
        source_ids = [source.id for source in sources_for_country("FRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_specific_priority_sources(self):
        expected_country_sources = {
            "AUS": "equestrian_australia",
            "GBR": "british_eventing",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
        }

        for country, expected_source_id in expected_country_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(expected_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_all_domestic_levels_have_national_backfill(self):
        registry = load_event_source_registry()

        for event_level in registry.coverage_targets.domestic_event_levels:
            with self.subTest(event_level=event_level):
                source_ids = [
                    source.id
                    for source in sources_for_event_level(event_level)
                    if source.scope == "national"
                ]
                self.assertIn("global_national_federations", source_ids)

    def test_all_international_levels_have_fei_source(self):
        registry = load_event_source_registry()

        for event_level in registry.coverage_targets.international_event_levels:
            with self.subTest(event_level=event_level):
                source_ids = [
                    source.id
                    for source in sources_for_event_level(event_level)
                ]
                self.assertEqual(source_ids[0], "data_fei")

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
