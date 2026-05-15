import json
import unittest

from equibets.sources import (
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_event,
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
            "africa": "africa_national_federations",
            "americas": "americas_national_federations",
            "asia": "asia_national_federations",
            "middle_east": "middle_east_national_federations",
            "oceania": "oceania_national_federations",
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

    def test_global_backfill_covers_every_country(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_global_backfill_covers_every_national_level(self):
        source_ids = [source.id for source in sources_for_level("grassroots")]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_event_combines_country_and_level_coverage(self):
        source_ids = [source.id for source in sources_for_event("ZAF", "training")]

        self.assertIn("global_national_federations", source_ids)

    def test_registry_declares_global_country_and_level_coverage(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertIn("all_countries", payload["country_coverage"])
        self.assertIn("all_national_event_levels", payload["level_coverage"])


if __name__ == "__main__":
    unittest.main()
