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

    def test_coverage_targets_include_all_countries_and_levels(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertIn("starter", registry.coverage_targets.national_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.national_event_levels)
        self.assertIn("cci1_intro", registry.coverage_targets.international_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.international_event_levels)

        national_levels = set(registry.coverage_targets.national_event_levels)
        national_sources = [
            source for source in registry.sources if source.scope == "national"
        ]
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertEqual(set(source.event_levels), national_levels)

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "north_america": "north_america_national_federations",
            "latin_america": "latin_america_national_federations",
            "asia_pacific": "asia_pacific_national_federations",
            "middle_east": "middle_east_national_federations",
            "africa": "africa_national_federations",
            "central_asia": "central_asia_national_federations",
            "caribbean": "caribbean_national_federations",
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

    def test_country_lookup_includes_country_source_and_global_backfill(self):
        usa_source_ids = [source.id for source in sources_for_country("usa")]
        brazil_source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(usa_source_ids[0], "data_fei")
        self.assertIn("usea", usa_source_ids)
        self.assertIn("global_national_federations", usa_source_ids)
        self.assertEqual(brazil_source_ids, ["data_fei", "global_national_federations"])

    def test_event_level_lookup_splits_fei_and_national_coverage(self):
        international_source_ids = [
            source.id for source in sources_for_event_level("CCI5-LONG")
        ]
        national_source_ids = [
            source.id for source in sources_for_event_level("national five star")
        ]

        self.assertEqual(international_source_ids, ["data_fei"])
        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
