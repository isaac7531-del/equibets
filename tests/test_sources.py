import json
import unittest

from equibets.sources import DATA_FILE, load_event_sources, sources_for_country, sources_for_level, sources_for_region

with DATA_FILE.open(encoding="utf-8") as data_file:
    SOURCE_REGISTRY = json.load(data_file)

NATIONAL_EVENT_LEVELS = set(SOURCE_REGISTRY["national_event_levels"])


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "asia": "asia_national_federations",
            "africa": "africa_national_federations",
            "oceania": "oceania_national_federations",
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

    def test_country_lookup_keeps_fei_primary_for_international_results(self):
        source_ids = [source.id for source in sources_for_country("USA", event_level="fei-international")]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_lookup_includes_global_backfill_for_any_national_level(self):
        source_ids = [source.id for source in sources_for_country("KEN", event_level="schooling")]

        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_priority_country_sources_cover_all_national_levels(self):
        source_ids = {
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
            "global_national_federations",
        }

        sources_by_id = {source.id: source for source in load_event_sources()}

        for source_id in source_ids:
            with self.subTest(source_id=source_id):
                self.assertTrue(NATIONAL_EVENT_LEVELS.issubset(sources_by_id[source_id].event_levels))

    def test_level_lookup_finds_global_national_level_coverage(self):
        source_ids = [source.id for source in sources_for_level("pony club")]

        self.assertIn("global_national_federations", source_ids)


if __name__ == "__main__":
    unittest.main()
