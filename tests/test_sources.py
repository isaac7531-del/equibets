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
        self.assertIn("GBR", registry.coverage_targets.countries["all_fei_member_nations"])
        self.assertIn("USA", registry.coverage_targets.countries["all_fei_member_nations"])
        self.assertIn("ZIM", registry.coverage_targets.countries["all_fei_member_nations"])
        self.assertIn(
            "national_five_star",
            registry.coverage_targets.event_levels["all_national_and_regional_levels"],
        )
        self.assertIn(
            "cci5_long",
            registry.coverage_targets.event_levels["all_fei_international_levels"],
        )

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn("GBR", sources[0].countries)
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_sources_can_be_filtered_by_country(self):
        source_ids = [source.id for source in sources_for_country("GBR")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("europe_national_federations", source_ids)
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_can_be_filtered_by_national_event_level(self):
        source_ids = [source.id for source in sources_for_event_level("national_five_star")]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_can_be_filtered_by_fei_event_level_alias(self):
        source_ids = [source.id for source in sources_for_event_level("CCI4-L")]

        self.assertEqual(source_ids, ["data_fei"])

    def test_global_national_source_covers_every_country_and_domestic_level(self):
        registry = load_event_source_registry()
        global_source = next(
            source for source in registry.sources if source.id == "global_national_federations"
        )

        self.assertEqual(
            set(global_source.countries),
            set(registry.coverage_targets.countries["all_fei_member_nations"]),
        )
        self.assertEqual(
            set(global_source.event_levels),
            set(
                registry.coverage_targets.event_levels[
                    "all_national_and_regional_levels"
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
