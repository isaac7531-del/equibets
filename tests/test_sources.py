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
        global_source = next(
            source for source in load_event_sources() if source.id == "global_national_federations"
        )

        self.assertEqual(global_source.countries, ("all_countries",))
        self.assertEqual(global_source.source_type, "federation_and_organizer_registry")
        for event_level in (
            "fei_international",
            "national_championship",
            "national",
            "regional",
            "local",
            "schooling",
            "training",
            "unaffiliated",
        ):
            with self.subTest(event_level=event_level):
                self.assertIn(event_level, global_source.event_levels)

    def test_sources_for_country_include_global_coverage_for_any_country(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_can_filter_lower_event_levels(self):
        source_ids = [source.id for source in sources_for_country("BRA", event_level="schooling")]

        self.assertNotIn("data_fei", source_ids)
        self.assertEqual(source_ids, ["global_national_federations"])

    def test_sources_for_country_include_specific_national_source(self):
        source_ids = [source.id for source in sources_for_country("GBR", event_level="national")]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
