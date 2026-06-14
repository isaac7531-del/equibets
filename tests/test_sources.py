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

    def test_registry_targets_all_countries_and_all_levels(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertIn("starter", registry.coverage_targets.national_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.national_event_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_international_event_levels)

        national_levels = registry.coverage_targets.national_event_levels
        for source in registry.sources:
            if source.scope == "national":
                with self.subTest(source_id=source.id):
                    self.assertEqual(source.event_levels, national_levels)

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

    def test_country_sources_cover_priority_and_backfill_countries(self):
        country_sources = {
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
        }

        for country, national_source_id in country_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

        source_ids = [source.id for source in sources_for_country("CAN")]
        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_level_sources_distinguish_national_and_fei_levels(self):
        national_source_ids = [source.id for source in sources_for_event_level("training")]
        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)

        fei_source_ids = [source.id for source in sources_for_event_level("cci4_long")]
        self.assertEqual(fei_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
