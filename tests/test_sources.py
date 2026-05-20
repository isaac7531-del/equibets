import unittest

from equibets.sources import (
    expand_country_codes,
    expand_event_levels,
    load_event_sources,
    sources_for_country,
    sources_for_level,
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

    def test_scope_expands_all_countries(self):
        country_codes = expand_country_codes(("all_countries",))

        self.assertIn("GBR", country_codes)
        self.assertIn("USA", country_codes)
        self.assertIn("ZAF", country_codes)
        self.assertIn("ZWE", country_codes)
        self.assertEqual(len(country_codes), len(set(country_codes)))

    def test_scope_expands_all_eventing_levels(self):
        levels = expand_event_levels(("all_eventing_levels",))

        self.assertEqual(
            levels,
            (
                "fei_international",
                "national",
                "regional",
                "local",
                "schooling",
            ),
        )

    def test_country_filter_includes_priority_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_filter_uses_global_backfill_for_non_priority_country(self):
        source_ids = [source.id for source in sources_for_country("zaf")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("usea", source_ids)

    def test_level_filter_includes_all_national_levels(self):
        source_ids = [source.id for source in sources_for_level("schooling")]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
