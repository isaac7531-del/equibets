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
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
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

    def test_country_sources_cover_named_and_global_national_events(self):
        expected_named_sources = {
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
            "BRA": None,
            "JPN": None,
            "ZAF": None,
        }

        for country_code, named_source_id in expected_named_sources.items():
            with self.subTest(country_code=country_code):
                source_ids = [source.id for source in sources_for_country(country_code)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)
                if named_source_id is not None:
                    self.assertIn(named_source_id, source_ids)

    def test_national_sources_cover_all_national_event_levels(self):
        registry = load_event_source_registry()
        level_groups = registry["event_level_groups"]
        national_levels = tuple(level_groups["national_event_levels"])
        all_levels = set(level_groups["all_eventing_levels"])

        self.assertEqual(registry["country_scope"], "all_countries")
        self.assertEqual(registry["level_scope"], "all_eventing_levels")
        self.assertTrue(set(national_levels).issubset(all_levels))

        for source in load_event_sources():
            if source.scope != "national":
                continue
            with self.subTest(source_id=source.id):
                self.assertEqual(source.event_levels, national_levels)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_active_only_country_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_country("USA", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
