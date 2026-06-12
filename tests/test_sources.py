import json
import unittest

from equibets.sources import (
    DATA_FILE,
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

    def test_registry_declares_all_country_all_level_national_backfill(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        source_by_id = {source["id"]: source for source in payload["sources"]}

        self.assertEqual(payload["version"], 2)
        self.assertEqual(
            source_by_id["global_national_federations"]["countries"],
            ["all_countries"],
        )
        self.assertEqual(
            source_by_id["global_national_federations"]["event_levels"],
            ["all_eventing_levels"],
        )

    def test_country_lookup_covers_any_country_and_eventing_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="introductory")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_priority_national_sources_cover_all_eventing_levels(self):
        source_ids = [
            source.id
            for source in sources_for_country("GBR", level="grassroots")
        ]

        self.assertEqual(
            source_ids,
            ["british_eventing", "global_national_federations"],
        )

    def test_country_lookup_keeps_fei_primary_when_level_is_unspecified(self):
        source_ids = [source.id for source in sources_for_country("CAN")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
