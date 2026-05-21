import unittest

from equibets.sources import (
    load_event_sources,
    sources_for_country,
    sources_for_country_and_level,
    sources_for_event_level,
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

    def test_sources_for_country_expands_global_country_scope(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_expands_european_scope(self):
        source_ids = [source.id for source in sources_for_country("FRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("europe_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_keeps_priority_national_source(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_event_level_filters_source_scopes(self):
        international_source_ids = [
            source.id for source in sources_for_event_level("fei international")
        ]
        national_source_ids = [source.id for source in sources_for_event_level("national")]

        self.assertEqual(international_source_ids, ["data_fei"])
        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)

    def test_sources_for_country_and_level_returns_national_backfill(self):
        source_ids = [
            source.id for source in sources_for_country_and_level("BRA", "regional")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_filters_respect_active_only_status(self):
        source_ids = [
            source.id for source in sources_for_country("USA", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_filter_requires_three_letter_code(self):
        with self.assertRaisesRegex(ValueError, "three-letter country code"):
            sources_for_country("United States")


if __name__ == "__main__":
    unittest.main()
