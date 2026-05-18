import json
import unittest
from pathlib import Path

from equibets.sources import (
    load_event_sources,
    sources_for_country_and_level,
    sources_for_region,
)


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"


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

    def test_global_regions_include_fei_and_national_registry_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "latin_america": "latin_america_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, national_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_national_sources_cover_declared_national_level_scope(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)
        national_level_scope = set(payload["event_level_scope"]) - {"fei_international"}

        for source in load_event_sources():
            if source.scope != "national":
                continue
            with self.subTest(source_id=source.id):
                self.assertEqual(set(source.event_levels), national_level_scope)

    def test_country_and_level_sources_use_specific_then_global_coverage(self):
        usa_source_ids = [
            source.id for source in sources_for_country_and_level("USA", "club")
        ]
        brazil_source_ids = [
            source.id for source in sources_for_country_and_level("BRA", "club")
        ]
        fei_source_ids = [
            source.id
            for source in sources_for_country_and_level("GBR", "fei international")
        ]

        self.assertEqual(usa_source_ids, ["usea", "global_national_federations"])
        self.assertEqual(brazil_source_ids, ["global_national_federations"])
        self.assertEqual(fei_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
