import unittest

from equibets.sources import (
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_global_national_source_covers_every_country(self):
        for country in ("BRA", "JPN", "RSA", "USA"):
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)

    def test_priority_country_sources_keep_regional_overrides(self):
        source_ids = [source.id for source in sources_for_country("gbr")]

        self.assertIn("british_eventing", source_ids)
        self.assertLess(
            source_ids.index("british_eventing"),
            source_ids.index("global_national_federations"),
        )

    def test_national_sources_cover_every_national_eventing_level(self):
        for level in ("starter", "novice", "advanced", "championship"):
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_level(level)]
                self.assertNotIn("data_fei", source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_fei_source_covers_all_fei_eventing_levels(self):
        for level in ("CCI1*-Intro", "CCI5*-L", "CH-EU"):
            with self.subTest(level=level):
                source_ids = [source.id for source in sources_for_level(level)]
                self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
