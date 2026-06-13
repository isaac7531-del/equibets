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

    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()
        targets = registry.coverage_targets

        self.assertEqual(registry.version, 2)
        self.assertEqual(targets.countries, ("all_fei_member_nations",))
        self.assertEqual(targets.national_event_levels[0], "starter")
        self.assertEqual(targets.national_event_levels[-1], "national_five_star")
        self.assertIn("cci5_long", targets.international_event_levels)
        self.assertNotIn("national", targets.national_event_levels)
        self.assertNotIn("regional", targets.national_event_levels)

    def test_national_sources_cover_all_configured_national_levels(self):
        registry = load_event_source_registry()
        national_levels = set(registry.coverage_targets.national_event_levels)

        for source in registry.sources:
            if source.scope == "national":
                with self.subTest(source=source.id):
                    self.assertEqual(set(source.event_levels), national_levels)

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

    def test_every_region_has_national_level_coverage(self):
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
                source_ids = [
                    source.id for source in sources_for_region(region, level="starter")
                ]
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)
                self.assertNotIn("data_fei", source_ids)

    def test_sources_can_be_filtered_by_country_and_level(self):
        usa_starter_source_ids = [
            source.id for source in sources_for_country("USA", level="starter")
        ]
        usa_international_source_ids = [
            source.id for source in sources_for_country("usa", level="cci5_long")
        ]
        gbr_advanced_source_ids = [
            source.id for source in sources_for_country("GBR", level="Advanced")
        ]

        self.assertEqual(
            usa_starter_source_ids,
            ["usea", "global_national_federations"],
        )
        self.assertEqual(usa_international_source_ids, ["data_fei"])
        self.assertEqual(
            gbr_advanced_source_ids,
            ["british_eventing", "global_national_federations"],
        )

    def test_sources_can_be_filtered_by_event_level(self):
        starter_source_ids = [
            source.id for source in sources_for_event_level("starter")
        ]
        cci4_source_ids = [
            source.id for source in sources_for_event_level("CCI4 Long")
        ]

        self.assertNotIn("data_fei", starter_source_ids)
        self.assertIn("global_national_federations", starter_source_ids)
        self.assertEqual(cci4_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
