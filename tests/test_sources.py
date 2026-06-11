import unittest

from equibets.sources import (
    expand_country_codes,
    expand_event_levels,
    load_country_groups,
    load_event_level_groups,
    load_event_sources,
    sources_for_country,
    sources_for_country_and_event_level,
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
        source_ids = [
            source.id
            for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_groups_expand_all_fei_country_codes(self):
        countries = load_country_groups()["all_fei_member_nations"]

        self.assertGreaterEqual(len(countries), 135)
        self.assertEqual(len(countries), len(set(countries)))
        for country in ("GBR", "USA", "AUS", "NZL", "BRA", "JPN", "RSA", "UAE"):
            self.assertIn(country, countries)

    def test_sources_for_country_resolves_global_and_priority_coverage(self):
        self.assertEqual(
            [source.id for source in sources_for_country("BRA")],
            ["data_fei", "global_national_federations"],
        )
        self.assertEqual(
            [source.id for source in sources_for_country("FRA")],
            ["data_fei", "europe_national_federations", "global_national_federations"],
        )
        self.assertEqual(
            [source.id for source in sources_for_country("GBR")],
            [
                "data_fei",
                "europe_national_federations",
                "british_eventing",
                "global_national_federations",
            ],
        )

    def test_national_event_coverage_includes_every_fei_country_and_level(self):
        countries = expand_country_codes(("all_fei_member_nations",))
        national_levels = load_event_level_groups()["national_event_levels"]

        self.assertIn("starter", national_levels)
        self.assertIn("advanced", national_levels)
        self.assertIn("national_five_star", national_levels)
        for country in countries:
            for level in national_levels:
                with self.subTest(country=country, level=level):
                    source_ids = [
                        source.id
                        for source in sources_for_country_and_event_level(country, level)
                    ]
                    self.assertIn("global_national_federations", source_ids)

    def test_all_eventing_levels_have_country_coverage(self):
        countries = expand_country_codes(("all_fei_member_nations",))
        level_groups = load_event_level_groups()
        all_levels = level_groups["all_eventing_levels"]
        national_levels = set(level_groups["national_event_levels"])

        for country in countries:
            for level in all_levels:
                with self.subTest(country=country, level=level):
                    source_ids = [
                        source.id
                        for source in sources_for_country_and_event_level(country, level)
                    ]
                    if level in national_levels:
                        self.assertIn("global_national_federations", source_ids)
                    else:
                        self.assertIn("data_fei", source_ids)

    def test_source_level_groups_can_expand_for_callers(self):
        self.assertEqual(
            expand_event_levels(("national_event_levels",))[:4],
            ("national", "regional", "starter", "introductory"),
        )

    def test_event_level_filter_keeps_international_and_national_scopes_separate(self):
        self.assertEqual(
            [source.id for source in sources_for_event_level("FEI International")],
            ["data_fei"],
        )
        self.assertEqual(
            [
                source.id
                for source in sources_for_country_and_event_level("USA", "national")
            ],
            ["usea", "global_national_federations"],
        )

    def test_event_level_filter_normalizes_common_source_labels(self):
        self.assertEqual(
            [
                source.id
                for source in sources_for_country_and_event_level(
                    "USA",
                    "Beginner Novice",
                )
            ],
            ["usea", "global_national_federations"],
        )
        self.assertEqual(
            [
                source.id
                for source in sources_for_country_and_event_level("BRA", "CCI5*-L")
            ],
            ["data_fei"],
        )


if __name__ == "__main__":
    unittest.main()
