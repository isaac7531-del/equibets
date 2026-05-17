import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].countries, ("all_countries",))
        self.assertEqual(sources[0].event_levels, ("all_eventing_levels",))

    def test_national_sources_cover_all_eventing_levels(self):
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

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
                source_ids = [
                    source.id for source in sources_for_region(region, level="starter")
                ]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_sources_include_all_country_backfill(self):
        expected_national_sources = {
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
        }

        for country, national_source_id in expected_national_sources.items():
            with self.subTest(country=country):
                source_ids = [
                    source.id for source in sources_for_country(country, level="CCI4-L")
                ]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_unprioritized_country_keeps_global_coverage(self):
        source_ids = [source.id for source in sources_for_country("CAN", level="training")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("british_eventing", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region(
                "usa", level="preliminary", include_planned=False
            )
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
