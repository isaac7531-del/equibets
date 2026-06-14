import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


NATIONAL_EVENT_LEVELS = (
    "starter",
    "beginner_novice",
    "novice",
    "training",
    "modified",
    "preliminary",
    "intermediate",
    "advanced",
    "national_one_star",
    "national_two_star",
    "national_three_star",
    "national_four_star",
    "national_five_star",
)

FEI_INTERNATIONAL_EVENT_LEVELS = (
    "cci1_intro",
    "cci2_short",
    "cci2_long",
    "cci3_short",
    "cci3_long",
    "cci4_short",
    "cci4_long",
    "cci5_long",
    "ccio",
    "championship",
)

REGIONAL_NATIONAL_SOURCES = {
    "africa": "africa_national_federations",
    "asia": "asia_national_federations",
    "europe": "europe_national_federations",
    "middle_east": "middle_east_national_federations",
    "north_america": "north_america_national_federations",
    "central_america_caribbean": "central_america_caribbean_national_federations",
    "south_america": "south_america_national_federations",
    "oceania": "oceania_national_federations",
    "uk": "british_eventing",
    "australia": "equestrian_australia",
    "new_zealand": "equestrian_sports_new_zealand",
    "usa": "usea",
}


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_countries",))
        self.assertEqual(
            registry.coverage_targets.national_event_levels,
            NATIONAL_EVENT_LEVELS,
        )
        self.assertEqual(
            registry.coverage_targets.fei_international_event_levels,
            FEI_INTERNATIONAL_EVENT_LEVELS,
        )
        self.assertEqual(
            registry.coverage_targets.event_levels,
            NATIONAL_EVENT_LEVELS + FEI_INTERNATIONAL_EVENT_LEVELS,
        )

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].event_levels, FEI_INTERNATIONAL_EVENT_LEVELS)

    def test_priority_regions_include_fei_and_national_sources(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.priority_regions, tuple(REGIONAL_NATIONAL_SOURCES))
        for region, national_source_id in REGIONAL_NATIONAL_SOURCES.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_global_national_source_covers_all_countries_and_levels(self):
        global_source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )

        self.assertEqual(global_source.countries, ("all_countries",))
        self.assertEqual(
            global_source.event_levels,
            NATIONAL_EVENT_LEVELS + FEI_INTERNATIONAL_EVENT_LEVELS,
        )

    def test_every_target_level_has_a_configured_source(self):
        registry = load_event_source_registry()

        for event_level in registry.coverage_targets.event_levels:
            with self.subTest(event_level=event_level):
                source_ids = [
                    source.id for source in sources_for_event_level(event_level)
                ]
                self.assertIn("global_national_federations", source_ids)
                if event_level in FEI_INTERNATIONAL_EVENT_LEVELS:
                    self.assertEqual(source_ids[0], "data_fei")

    def test_event_level_lookup_accepts_display_level_labels(self):
        cci4_short_source_ids = [
            source.id for source in sources_for_event_level("CCI4*-S")
        ]
        cci5_long_source_ids = [
            source.id for source in sources_for_event_level("CCI5-L")
        ]
        beginner_novice_source_ids = [
            source.id for source in sources_for_event_level("beginner novice")
        ]

        self.assertEqual(cci4_short_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", cci4_short_source_ids)
        self.assertEqual(cci5_long_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", cci5_long_source_ids)
        self.assertIn("global_national_federations", beginner_novice_source_ids)

    def test_country_lookup_uses_explicit_and_global_fallback_sources(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_level_lookup_uses_national_sources_for_national_levels(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="starter")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_level_lookup_backfills_unlisted_countries(self):
        source_ids = [
            source.id for source in sources_for_country("BRA", level="novice")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_level_lookup_normalizes_international_display_labels(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="CCI4*-S")
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("usea", source_ids)

    def test_region_level_lookup_filters_by_configured_event_level(self):
        starter_source_ids = [
            source.id for source in sources_for_region("uk", level="starter")
        ]
        cci_source_ids = [
            source.id for source in sources_for_region("uk", level="CCI4*-S")
        ]

        self.assertEqual(
            starter_source_ids,
            ["british_eventing", "global_national_federations"],
        )
        self.assertEqual(cci_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", cci_source_ids)
        self.assertNotIn("british_eventing", cci_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_country("USA", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
