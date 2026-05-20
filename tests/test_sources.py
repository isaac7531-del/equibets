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

    def test_national_sources_include_all_national_event_levels(self):
        national_levels = {"national", "regional", "local", "grassroots"}

        for source in load_event_sources():
            if source.scope != "national":
                continue
            with self.subTest(source=source.id):
                self.assertTrue(national_levels.issubset(set(source.event_levels)))

    def test_country_lookup_uses_global_backfill_for_all_countries(self):
        expected_sources = {
            "FRA": "europe_national_federations",
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
            "BRA": "global_national_federations",
            "JPN": "global_national_federations",
        }

        for country, national_source_id in expected_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_can_filter_by_event_level(self):
        national_source_ids = [
            source.id for source in sources_for_country("usa", event_levels=["grassroots"])
        ]
        international_source_ids = [
            source.id for source in sources_for_country("USA", event_levels=["fei international"])
        ]

        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("usea", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)
        self.assertEqual(international_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
