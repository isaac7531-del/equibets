import unittest

from equibets.sources import (
    load_country_scopes,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_national_events,
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_scopes_include_global_and_european_coverage(self):
        scopes = load_country_scopes()

        self.assertTrue(scopes["all_fei_member_nations"].covers("JPN"))
        self.assertTrue(scopes["all_fei_europe_member_nations"].covers("GBR"))
        self.assertFalse(scopes["all_fei_europe_member_nations"].covers("BRA"))

    def test_sources_for_country_expands_symbolic_country_scopes(self):
        source_ids = [source.id for source in sources_for_country("GBR")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("europe_national_federations", source_ids)
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("usea", source_ids)

    def test_sources_for_country_uses_global_backfill_for_any_fei_country(self):
        source_ids = [source.id for source in sources_for_country("jpn")]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_sources_for_event_level_selects_all_matching_levels(self):
        regional_source_ids = [
            source.id for source in sources_for_event_level("Regional")
        ]
        international_source_ids = [
            source.id for source in sources_for_event_level("fei international")
        ]

        self.assertIn("british_eventing", regional_source_ids)
        self.assertIn("global_national_federations", regional_source_ids)
        self.assertNotIn("data_fei", regional_source_ids)
        self.assertEqual(international_source_ids, ["data_fei"])

    def test_sources_for_national_events_filters_country_and_level(self):
        source_ids = [
            source.id
            for source in sources_for_national_events(country="AUS", event_level="national")
        ]

        self.assertEqual(
            source_ids,
            ["equestrian_australia", "global_national_federations"],
        )

    def test_active_only_national_events_are_empty_until_crawlers_are_enabled(self):
        source_ids = [
            source.id
            for source in sources_for_national_events(
                country="USA",
                event_level="regional",
                include_planned=False,
            )
        ]

        self.assertEqual(source_ids, [])


if __name__ == "__main__":
    unittest.main()
