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

    def test_global_national_source_covers_all_countries_and_levels(self):
        sources = {source.id: source for source in load_event_sources()}
        global_national_source = sources["global_national_federations"]

        self.assertIn("all_countries", global_national_source.countries)
        self.assertIn("all_eventing_levels", global_national_source.event_levels)

    def test_country_sources_include_specific_and_global_national_coverage(self):
        source_ids = [source.id for source in sources_for_country("USA", level="national")]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_sources_support_any_country_and_level(self):
        source_ids = [source.id for source in sources_for_country("CAN", level="starter")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
