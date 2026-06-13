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
        self.assertIn("cci4", sources[0].event_levels)

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "uk": "british_eventing",
            "australia": "equestrian_australia",
            "new_zealand": "equestrian_sports_new_zealand",
            "usa": "usea",
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "central_america_caribbean": "central_america_caribbean_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_coverage_targets_expand_all_country_groups(self):
        registry = load_event_source_registry()
        all_countries = registry.coverage_targets.expand_countries(("all_countries",))

        self.assertGreaterEqual(len(all_countries), 190)
        self.assertIn("GBR", all_countries)
        self.assertIn("USA", all_countries)
        self.assertIn("AUS", all_countries)
        self.assertIn("NZL", all_countries)
        self.assertEqual(len(all_countries), len(set(all_countries)))

    def test_country_lookup_returns_priority_and_backfill_sources(self):
        source_ids = [
            source.id
            for source in sources_for_country("GBR", level="Beginner Novice")
        ]

        self.assertNotIn("data_fei", source_ids)
        self.assertEqual(source_ids[0], "europe_national_federations")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_international_level_lookup_prefers_fei_only(self):
        source_ids = [source.id for source in sources_for_country("USA", level="CCI4")]

        self.assertEqual(source_ids, ["data_fei"])

    def test_event_level_lookup_covers_all_national_levels(self):
        national_sources = sources_for_event_level("national_five_star")
        source_ids = [source.id for source in national_sources]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertTrue(
            all("national_five_star" in source.event_levels for source in national_sources)
        )


if __name__ == "__main__":
    unittest.main()
