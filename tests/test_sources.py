import unittest

from equibets.sources import (
    load_country_groups,
    load_event_level_groups,
    load_event_sources,
    source_country_codes,
    source_event_levels,
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

    def test_all_fei_member_countries_have_national_backfill(self):
        country_groups = load_country_groups()
        fei_countries = country_groups["all_fei_member_nations"]

        self.assertEqual(len(fei_countries), 135)

        for country_code in fei_countries:
            with self.subTest(country_code=country_code):
                source_ids = [source.id for source in sources_for_country(country_code)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)

    def test_fei_regional_groups_partition_all_member_countries(self):
        country_groups = load_country_groups()
        regional_group_codes = {
            country_code
            for group_id, country_codes in country_groups.items()
            if group_id.startswith("fei_group_")
            for country_code in country_codes
        }

        self.assertEqual(regional_group_codes, set(country_groups["all_fei_member_nations"]))

    def test_national_sources_cover_every_declared_national_level(self):
        event_level_groups = load_event_level_groups()
        national_levels = event_level_groups["all_national_eventing_levels"]

        for level in national_levels:
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_event_level(level)]
                self.assertIn("global_national_federations", source_ids)

    def test_source_group_tokens_expand_to_codes_and_levels(self):
        global_source = next(source for source in load_event_sources() if source.id == "global_national_federations")

        self.assertIn("USA", source_country_codes(global_source))
        self.assertIn("training_schooling", source_event_levels(global_source))

    def test_fei_international_level_uses_primary_database(self):
        source_ids = [source.id for source in sources_for_event_level("FEI international", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
