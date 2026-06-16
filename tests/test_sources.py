import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_registry_defines_all_country_and_level_coverage_targets(self):
        registry = load_event_source_registry()
        all_countries = set(registry.all_countries())

        self.assertEqual(registry.version, 2)
        self.assertGreaterEqual(len(all_countries), 100)
        self.assertIn("GBR", all_countries)
        self.assertIn("USA", all_countries)
        self.assertIn("ZAF", all_countries)
        self.assertIn("national_five_star", registry.all_national_event_levels())

        for name, country_set in registry.coverage_targets.country_sets.items():
            if name == "all_fei_member_nations":
                continue
            with self.subTest(country_set=name):
                self.assertLessEqual(set(country_set), all_countries)

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "central_america_caribbean": "central_america_caribbean_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "oceania": "oceania_national_federations",
            "south_america": "south_america_national_federations",
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

    def test_country_lookup_routes_to_regional_and_priority_sources(self):
        country_expectations = {
            "GBR": ("europe_national_federations", "british_eventing"),
            "USA": ("north_america_national_federations", "usea"),
            "AUS": ("oceania_national_federations", "equestrian_australia"),
            "NZL": ("oceania_national_federations", "equestrian_sports_new_zealand"),
            "ZAF": ("africa_national_federations",),
            "RSA": ("africa_national_federations",),
            "JPN": ("asia_national_federations",),
            "BRN": ("middle_east_national_federations",),
            "BRA": ("south_america_national_federations",),
            "MEX": ("central_america_caribbean_national_federations",),
        }

        for country, expected_source_ids in country_expectations.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)
                for expected_source_id in expected_source_ids:
                    self.assertIn(expected_source_id, source_ids)

    def test_country_specific_sources_do_not_match_other_countries(self):
        canada_source_ids = [source.id for source in sources_for_country("CAN")]

        self.assertIn("north_america_national_federations", canada_source_ids)
        self.assertIn("global_national_federations", canada_source_ids)
        self.assertNotIn("usea", canada_source_ids)
        self.assertNotIn("british_eventing", canada_source_ids)

    def test_level_lookup_covers_fei_and_domestic_labels(self):
        fei_source_ids = [source.id for source in sources_for_event_level("CCI5*-L")]
        cci_source_ids = [source.id for source in sources_for_event_level("CCI2")]
        domestic_source_ids = [source.id for source in sources_for_event_level("Beginner Novice")]
        national_star_source_ids = [source.id for source in sources_for_event_level("CCN3*")]

        self.assertEqual(fei_source_ids, ["data_fei"])
        self.assertEqual(cci_source_ids, ["data_fei"])
        self.assertNotIn("data_fei", domestic_source_ids)
        self.assertIn("global_national_federations", domestic_source_ids)
        self.assertIn("british_eventing", domestic_source_ids)
        self.assertEqual(domestic_source_ids, national_star_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]
        country_source_ids = [
            source.id for source in sources_for_country("USA", include_planned=False)
        ]
        domestic_source_ids = [
            source.id for source in sources_for_event_level("novice", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])
        self.assertEqual(country_source_ids, ["data_fei"])
        self.assertEqual(domestic_source_ids, [])


if __name__ == "__main__":
    unittest.main()
