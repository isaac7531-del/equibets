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
        registry = load_event_source_registry()
        sources = load_event_sources()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source.id, "data_fei")
        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_all_national_sources_cover_every_domestic_level(self):
        registry = load_event_source_registry()
        domestic_levels = set(registry.coverage_targets.domestic_event_levels)

        for source in load_event_sources():
            if source.scope != "national":
                continue

            with self.subTest(source_id=source.id):
                self.assertTrue(domestic_levels.issubset(source.event_levels))

    def test_data_fei_covers_every_international_level(self):
        registry = load_event_source_registry()
        international_levels = set(registry.coverage_targets.international_event_levels)

        self.assertTrue(international_levels.issubset(registry.primary_source.event_levels))

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

    def test_country_lookup_uses_specific_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_any_fei_country_can_use_global_national_backfill(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_splits_domestic_and_international_sources(self):
        domestic_source_ids = [
            source.id for source in sources_for_event_level("beginner novice")
        ]
        international_source_ids = [
            source.id for source in sources_for_event_level("cci4-short")
        ]

        self.assertIn("global_national_federations", domestic_source_ids)
        self.assertNotIn("data_fei", domestic_source_ids)
        self.assertEqual(international_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
