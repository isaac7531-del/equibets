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
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertEqual(len(registry.coverage_targets.national_event_levels), 14)
        self.assertEqual(registry.coverage_targets.national_event_levels[0], "starter")
        self.assertEqual(
            registry.coverage_targets.national_event_levels[-1],
            "national_five_star",
        )
        self.assertEqual(len(registry.coverage_targets.international_event_levels), 10)
        self.assertIn("championship", registry.coverage_targets.international_event_levels)

    def test_data_fei_is_primary_source(self):
        registry = load_event_source_registry()
        sources = list(registry.sources)

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].event_levels, registry.coverage_targets.international_event_levels)

    def test_each_national_source_covers_all_national_levels(self):
        registry = load_event_source_registry()

        for source in registry.sources:
            if source.scope == "national":
                with self.subTest(source_id=source.id):
                    self.assertEqual(
                        source.event_levels,
                        registry.coverage_targets.national_event_levels,
                    )

    def test_priority_regions_include_fei_global_and_national_sources(self):
        expected_regional_sources = {
            "europe": "europe_national_federations",
            "asia": "asia_national_federations",
            "africa": "africa_national_federations",
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

        for region, national_source_id in expected_regional_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_sources_include_global_and_country_specific_sources(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_level_sources_split_national_and_international_coverage(self):
        national_source_ids = [source.id for source in sources_for_event_level("starter")]
        international_source_ids = [source.id for source in sources_for_event_level("CCI2*-S")]

        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)
        self.assertEqual(international_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
