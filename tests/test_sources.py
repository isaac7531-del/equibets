import json
import tempfile
import unittest
from pathlib import Path

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


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

    def test_global_national_source_covers_all_countries_and_levels(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="introductory")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_sources_include_specific_and_global_all_level_sources(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="modified")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_sources_include_fei_when_level_is_unspecified(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_region_sources_can_filter_by_all_eventing_levels(self):
        source_ids = [
            source.id
            for source in sources_for_region("uk", level="grassroots")
        ]

        self.assertEqual(source_ids, ["british_eventing", "global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_duplicate_source_ids_are_rejected(self):
        payload = {
            "sources": [
                {
                    "id": "duplicate",
                    "name": "First",
                    "priority": 1,
                    "scope": "national",
                    "regions": ["global"],
                    "countries": ["all_countries"],
                    "disciplines": ["eventing"],
                    "event_levels": ["all_eventing_levels"],
                    "source_type": "test",
                    "base_url": None,
                    "status": "planned",
                    "notes": "Test source.",
                },
                {
                    "id": "duplicate",
                    "name": "Second",
                    "priority": 2,
                    "scope": "national",
                    "regions": ["global"],
                    "countries": ["all_countries"],
                    "disciplines": ["eventing"],
                    "event_levels": ["all_eventing_levels"],
                    "source_type": "test",
                    "base_url": None,
                    "status": "planned",
                    "notes": "Test source.",
                },
            ]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "event_sources.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "source ids must be unique"):
                load_event_sources(path)


if __name__ == "__main__":
    unittest.main()
