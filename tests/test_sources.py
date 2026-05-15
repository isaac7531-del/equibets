import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
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
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_registry_tracks_all_configured_country_codes(self):
        registry = load_event_source_registry()

        self.assertGreaterEqual(len(registry.country_codes), 190)
        self.assertEqual(tuple(sorted(registry.country_codes)), registry.country_codes)
        for placeholder in ("---", "AHO", "FEI", "NI1", "NI2"):
            self.assertNotIn(placeholder, registry.country_codes)
        for country_code in ("AUS", "FRA", "GBR", "IND", "NZL", "USA", "ZIM"):
            self.assertIn(country_code, registry.country_codes)

    def test_global_national_source_covers_all_levels(self):
        registry = load_event_source_registry()
        global_source = next(
            source
            for source in registry.sources
            if source.id == "global_national_federations"
        )

        self.assertIn("all_configured_country_codes", global_source.countries)
        self.assertEqual(global_source.event_levels, registry.national_event_levels)

    def test_country_lookup_returns_global_backfill_for_any_configured_country(self):
        source_ids = [source.id for source in sources_for_country("zim")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)


if __name__ == "__main__":
    unittest.main()
