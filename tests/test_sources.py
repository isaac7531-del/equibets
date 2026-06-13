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

        self.assertEqual(registry.version, 2)
        self.assertIn("all_fei_member_nations", registry.coverage_targets.countries)
        self.assertEqual(
            set(registry.coverage_targets.regions),
            {
                "africa",
                "asia",
                "central_america_caribbean",
                "europe",
                "middle_east",
                "north_america",
                "oceania",
                "south_america",
            },
        )
        self.assertIn("starter", registry.coverage_targets.national_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.national_event_levels)
        self.assertIn("cci1_intro", registry.coverage_targets.fei_international_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_international_event_levels)

    def test_regional_sources_cover_all_national_event_levels(self):
        registry = load_event_source_registry()
        national_levels = set(registry.coverage_targets.national_event_levels)
        regional_source_ids = {
            "africa_national_federations",
            "asia_national_federations",
            "central_america_caribbean_national_federations",
            "europe_national_federations",
            "middle_east_national_federations",
            "north_america_national_federations",
            "oceania_national_federations",
            "south_america_national_federations",
            "global_national_federations",
        }

        for source in registry.sources:
            if source.id in regional_source_ids:
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

    def test_non_priority_regions_have_national_and_global_backfill(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "central america/caribbean": (
                "central_america_caribbean_national_federations"
            ),
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "oceania": "oceania_national_federations",
            "south_america": "south_america_national_federations",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_uses_specific_and_global_national_sources(self):
        source_ids = [
            source.id
            for source in sources_for_country("gbr", level="national_two_star")
        ]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_unknown_fei_country_uses_global_national_backfill(self):
        source_ids = [source.id for source in sources_for_country("BRA", level="starter")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_event_level_lookup_separates_national_and_fei_levels(self):
        national_source_ids = [
            source.id for source in sources_for_event_level("national")
        ]
        international_source_ids = [
            source.id for source in sources_for_event_level("CCI5*-L")
        ]

        self.assertIn("global_national_federations", national_source_ids)
        self.assertNotIn("data_fei", national_source_ids)
        self.assertEqual(international_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
