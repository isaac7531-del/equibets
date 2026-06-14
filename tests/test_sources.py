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
        self.assertIn("starter", registry.coverage_targets.national_event_levels)
        self.assertIn(
            "national_five_star",
            registry.coverage_targets.national_event_levels,
        )
        self.assertIn("cci1_intro", registry.coverage_targets.international_event_levels)
        self.assertIn("cci5_star", registry.coverage_targets.international_event_levels)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_national_sources_cover_every_national_level(self):
        registry = load_event_source_registry()
        national_levels = set(registry.coverage_targets.national_event_levels)

        for source in registry.sources:
            if source.scope == "national":
                with self.subTest(source=source.id):
                    self.assertTrue(national_levels.issubset(source.event_levels))

    def test_priority_regions_include_fei_regional_and_global_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "central_america_caribbean": (
                "central_america_caribbean_national_federations"
            ),
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "oceania": "oceania_national_federations",
            "south_america": "south_america_national_federations",
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

    def test_region_lookup_can_filter_to_national_level_sources(self):
        source_ids = [source.id for source in sources_for_region("north america", level="advanced")]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("north_america_national_federations", source_ids)
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_separates_national_and_international_sources(self):
        national_source_ids = [source.id for source in sources_for_event_level("starter")]
        international_source_ids = [
            source.id for source in sources_for_event_level("cci4-star")
        ]

        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)
        self.assertEqual(international_source_ids, ["data_fei"])

    def test_country_lookup_uses_exact_and_all_country_sources(self):
        usa_source_ids = [
            source.id for source in sources_for_country("usa", level="advanced")
        ]
        backfill_source_ids = [
            source.id for source in sources_for_country("ARG", level="starter")
        ]

        self.assertNotIn("data_fei", usa_source_ids)
        self.assertIn("usea", usa_source_ids)
        self.assertIn("global_national_federations", usa_source_ids)
        self.assertEqual(backfill_source_ids, ["global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_active_only_filter_excludes_planned_national_sources(self):
        source_ids = [
            source.id
            for source in sources_for_country(
                "USA",
                level="advanced",
                include_planned=False,
            )
        ]

        self.assertEqual(source_ids, [])


if __name__ == "__main__":
    unittest.main()
