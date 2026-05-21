import unittest

from equibets.sources import (
    load_event_sources,
    sources_for_country,
    sources_for_country_level,
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

    def test_global_national_source_covers_all_countries_and_levels(self):
        global_source = next(
            source for source in load_event_sources() if source.id == "global_national_federations"
        )

        self.assertEqual(global_source.countries, ("all_fei_member_nations",))
        self.assertEqual(global_source.event_levels, ("all_national_levels",))

    def test_country_lookup_includes_global_sources_for_any_fei_country(self):
        for country in ("BRA", "JPN", "ZAF"):
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]

                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_keeps_specific_national_sources(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_level_lookup_covers_every_domestic_level(self):
        for level in ("Introductory", "Training", "Advanced", "Youth Championship"):
            with self.subTest(level=level):
                source_ids = [
                    source.id for source in sources_for_country_level("BRA", level)
                ]

                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)


if __name__ == "__main__":
    unittest.main()
