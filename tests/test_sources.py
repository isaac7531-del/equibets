import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    source_priority,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertIn("starter", registry.coverage_targets.national_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.national_event_levels)
        self.assertIn("cci1_intro", registry.coverage_targets.fei_international_levels)
        self.assertIn("championship", registry.coverage_targets.fei_international_levels)
        self.assertIn("africa", registry.coverage_targets.coverage_regions)
        self.assertIn("south_america", registry.coverage_targets.coverage_regions)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn("cci5_long", sources[0].event_levels)

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

    def test_every_national_source_covers_all_declared_national_levels(self):
        registry = load_event_source_registry()
        national_levels = registry.coverage_targets.national_event_levels

        for source in registry.sources:
            if source.scope != "national":
                continue
            with self.subTest(source_id=source.id):
                self.assertEqual(source.event_levels, national_levels)

    def test_every_coverage_region_has_national_registry_backfill(self):
        registry = load_event_source_registry()

        for region in registry.coverage_targets.coverage_regions:
            with self.subTest(region=region):
                regional_sources = sources_for_region(region, level="preliminary")
                regional_registry_ids = [
                    source.id
                    for source in regional_sources
                    if source.source_type == "federation_registry"
                    and region in source.regions
                ]

                self.assertTrue(regional_registry_ids)
                self.assertIn("global_national_federations", [source.id for source in regional_sources])

    def test_country_lookup_returns_priority_and_backfill_national_sources(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="training")
        ]

        self.assertEqual(source_ids[0], "usea")
        self.assertIn("north_america_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_fei_level_lookup_returns_primary_source_for_all_countries(self):
        source_ids = [
            source.id for source in sources_for_country("FRA", level="cci4_short")
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_event_level_lookup_splits_fei_and_national_levels(self):
        fei_source_ids = [
            source.id for source in sources_for_event_level("CCI5*-L")
        ]
        national_source_ids = [
            source.id for source in sources_for_event_level("national_five_star")
        ]

        self.assertEqual(fei_source_ids, ["data_fei"])
        self.assertIn("global_national_federations", national_source_ids)
        self.assertNotIn("data_fei", national_source_ids)

    def test_source_priority_comes_from_registry(self):
        self.assertEqual(source_priority("data_fei"), 0)
        self.assertEqual(source_priority("usea"), 50)
        self.assertEqual(source_priority("global_national_federations"), 90)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
