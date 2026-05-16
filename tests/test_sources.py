import unittest

from equibets.sources import (
    load_event_sources,
    national_event_sources,
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
        source_ids = [
            source.id
            for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_sources_include_all_country_national_backfill(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", event_level="grassroots")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_priority_country_sources_cover_all_national_levels(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", event_level="local")
        ]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_international_level_still_uses_fei_source(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", event_level="fei_international")
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_national_event_sources_can_query_any_member_country_and_level(self):
        sources = national_event_sources("JPN", event_level="introductory")

        self.assertEqual(
            [source.id for source in sources],
            ["global_national_federations"],
        )
        self.assertTrue(all(source.scope == "national" for source in sources))


if __name__ == "__main__":
    unittest.main()
