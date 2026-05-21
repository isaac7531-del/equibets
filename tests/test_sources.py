import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    national_event_country_scope,
    national_event_level_scope,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

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

    def test_registry_declares_all_country_and_all_level_scope(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertEqual(national_event_country_scope(), ("all_fei_member_nations",))
        self.assertIn("every country", registry.coverage.notes)
        self.assertIn("fei_international", national_event_level_scope())
        self.assertIn("CCI5*-L", national_event_level_scope())
        self.assertIn("national_championship", national_event_level_scope())
        self.assertIn("grassroots", national_event_level_scope())
        self.assertIn("pony", national_event_level_scope())
        self.assertIn("young_horse", national_event_level_scope())

    def test_global_regions_have_national_federation_sources(self):
        expected_region_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, source_id in expected_region_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)
                self.assertIn(source_id, source_ids)

    def test_global_national_source_covers_declared_levels(self):
        registry = load_event_source_registry()
        global_source = next(
            source for source in registry.sources if source.id == "global_national_federations"
        )

        self.assertEqual(global_source.countries, ("all_fei_member_nations",))
        self.assertTrue(set(registry.coverage.event_levels).issubset(global_source.event_levels))

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
