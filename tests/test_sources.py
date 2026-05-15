import unittest

from equibets.sources import load_event_sources, sources_for_region


NATIONAL_EVENT_LEVELS = {"national", "regional", "local"}


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
            "north_america": "north_america_national_federations",
            "central_america": "central_america_national_federations",
            "south_america": "south_america_national_federations",
            "middle_east": "middle_east_national_federations",
            "asia_oceania": "asia_oceania_national_federations",
            "africa": "africa_national_federations",
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

    def test_global_national_source_has_explicit_country_coverage(self):
        sources = load_event_sources()
        global_source = next(
            source for source in sources if source.id == "global_national_federations"
        )

        self.assertEqual(len(global_source.countries), 134)
        self.assertEqual(len(global_source.countries), len(set(global_source.countries)))
        self.assertFalse(any(country.startswith("all_") for country in global_source.countries))
        self.assertTrue(
            {"GBR", "AUS", "NZL", "USA", "BRA", "JPN", "RSA", "CIV"}.issubset(
                global_source.countries
            )
        )

    def test_national_sources_cover_all_national_event_levels(self):
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertTrue(NATIONAL_EVENT_LEVELS.issubset(source.event_levels))


if __name__ == "__main__":
    unittest.main()
