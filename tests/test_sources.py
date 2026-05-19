import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


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

    def test_registry_declares_all_country_all_level_national_backfill(self):
        sources = {source.id: source for source in load_event_sources()}

        self.assertIn("all_countries", sources["data_fei"].countries)
        self.assertIn("all_countries", sources["global_national_federations"].countries)
        self.assertIn("all_eventing_levels", sources["global_national_federations"].event_levels)

    def test_sources_for_country_includes_priority_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_uses_global_backfill_for_non_priority_countries(self):
        source_ids = [source.id for source in sources_for_country("bra")]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_sources_for_country_includes_european_registry(self):
        source_ids = [source.id for source in sources_for_country("FRA", level="training")]

        self.assertIn("europe_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_level_filter_matches_all_eventing_levels_wildcard(self):
        source_ids = [source.id for source in sources_for_region("usa", level="training")]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
