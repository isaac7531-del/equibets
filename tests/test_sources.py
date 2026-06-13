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
        national_source_ids = {
            "europe_national_federations",
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
            "global_national_federations",
        }
        sources = {source.id: source for source in load_event_sources()}

        for source_id in national_source_ids:
            with self.subTest(source_id=source_id):
                self.assertEqual(sources[source_id].event_levels, ("all_eventing_levels",))

    def test_global_national_source_covers_every_country(self):
        sources = {source.id: source for source in load_event_sources()}

        self.assertEqual(sources["global_national_federations"].countries, ("all_countries",))

    def test_country_lookup_includes_priority_and_global_national_sources(self):
        expected_country_sources = {
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
        }

        for country, national_source_id in expected_country_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country, level="Starter")]
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)
                self.assertNotIn("data_fei", source_ids)

    def test_country_lookup_backfills_any_country_and_level(self):
        for country, level in (("BRA", "novice"), ("JPN", "advanced"), ("RSA", "regional")):
            with self.subTest(country=country, level=level):
                source_ids = [source.id for source in sources_for_country(country, level=level)]
                self.assertEqual(source_ids, ["global_national_federations"])

    def test_level_filter_keeps_fei_for_international_results(self):
        source_ids = [source.id for source in sources_for_country("CAN", level="fei-international")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
