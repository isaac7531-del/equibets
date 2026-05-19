import json
import unittest

from equibets.sources import (
    load_event_sources,
    sources_for_country,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_registry_declares_all_country_all_level_coverage(self):
        with open("data/event_sources.json", encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["coverage_wildcards"]["countries"], "all_countries")
        self.assertEqual(
            payload["coverage_wildcards"]["event_levels"],
            "all_eventing_levels",
        )

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

    def test_region_sources_cover_all_eventing_levels(self):
        source_ids = [
            source.id for source in sources_for_region("usa", level="starter")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_sources_cover_priority_and_global_national_events(self):
        source_ids = [
            source.id for source in sources_for_country("gbr", level="novice")
        ]

        self.assertEqual(source_ids[0], "british_eventing")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_global_backfill_covers_any_country_and_eventing_level(self):
        source_ids = [
            source.id for source in sources_for_country("BRA", level="starter")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
