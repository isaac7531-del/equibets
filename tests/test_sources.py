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

    def test_national_sources_cover_all_eventing_levels(self):
        national_sources = [
            source
            for source in load_event_sources()
            if source.scope == "national"
        ]

        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertIn("all_eventing_levels", source.event_levels)

    def test_country_lookup_includes_priority_country_source_at_any_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="grassroots")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_lookup_backfills_any_country_at_any_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="local")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_lookup_keeps_fei_primary_for_international_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="fei_international")
        ]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
