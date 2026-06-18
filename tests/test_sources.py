import unittest

from equibets.sources import (
    expand_country_tokens,
    expand_event_level_tokens,
    load_country_sets,
    load_event_levels,
    load_event_sources,
    national_event_coverage,
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
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_fei_country_sets_expand_to_concrete_codes(self):
        country_sets = load_country_sets()
        member_countries = expand_country_tokens(("all_fei_member_nations",))
        full_member_countries = expand_country_tokens(("all_fei_full_member_nations",))

        self.assertEqual(len(member_countries), 135)
        self.assertEqual(len(full_member_countries), 134)
        self.assertEqual(member_countries, country_sets["all_fei_member_nations"])
        self.assertIn("USA", member_countries)
        self.assertIn("GBR", member_countries)
        self.assertIn("AUS", member_countries)
        self.assertIn("NZL", member_countries)
        self.assertIn("NEP", member_countries)
        self.assertNotIn("NEP", full_member_countries)

    def test_europe_country_set_is_expanded_for_priority_source(self):
        european_countries = expand_country_tokens(("all_fei_europe_member_nations",))
        europe_source = next(
            source for source in load_event_sources() if source.id == "europe_national_federations"
        )

        self.assertEqual(len(european_countries), 41)
        self.assertIn("GBR", european_countries)
        self.assertIn("UKR", european_countries)
        self.assertNotIn("USA", european_countries)
        self.assertEqual(europe_source.resolved_countries(), european_countries)

    def test_level_groups_expand_to_all_concrete_eventing_levels(self):
        national_levels = expand_event_level_tokens(("national", "regional"))
        fei_levels = expand_event_level_tokens(("fei_international",))

        self.assertEqual(
            national_levels,
            (
                "starter",
                "beginner_novice",
                "novice",
                "training",
                "modified",
                "preliminary",
                "intermediate",
                "advanced",
                "introductory",
                "schooling",
                "regional_championship",
            ),
        )
        self.assertEqual(fei_levels[0], "cci1_intro")
        self.assertEqual(fei_levels[-1], "cci5_l")
        self.assertEqual(len(load_event_levels()), len(set(level.id for level in load_event_levels())))

    def test_sources_for_country_filters_country_and_level(self):
        usa_national_source_ids = [
            source.id for source in sources_for_country("usa", event_level="Preliminary")
        ]
        usa_fei_source_ids = [
            source.id for source in sources_for_country("USA", event_level="CCI3*-S")
        ]
        nepal_source_ids = [source.id for source in sources_for_country("NEP")]

        self.assertEqual(usa_national_source_ids[0], "usea")
        self.assertIn("global_national_federations", usa_national_source_ids)
        self.assertNotIn("data_fei", usa_national_source_ids)
        self.assertEqual(usa_fei_source_ids, ["data_fei"])
        self.assertIn("data_fei", nepal_source_ids)
        self.assertIn("global_national_federations", nepal_source_ids)

    def test_national_coverage_matrix_includes_all_countries_and_levels(self):
        countries = expand_country_tokens(("all_fei_member_nations",))
        levels = expand_event_level_tokens(("national", "regional"))
        covered_pairs = {
            (target.country, target.event_level) for target in national_event_coverage()
        }

        for country in countries:
            for level in levels:
                with self.subTest(country=country, level=level):
                    self.assertIn((country, level), covered_pairs)

    def test_active_only_national_coverage_waits_for_collectors(self):
        self.assertEqual(national_event_coverage(include_planned=False), [])


if __name__ == "__main__":
    unittest.main()
