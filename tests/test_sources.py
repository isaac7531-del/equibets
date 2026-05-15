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

    def test_priority_countries_include_all_level_national_sources(self):
        expected_national_sources = {
            "GBR": "british_eventing",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
        }

        for country, national_source_id in expected_national_sources.items():
            with self.subTest(country=country):
                source_ids = [
                    source.id
                    for source in sources_for_country(
                        country,
                        level="beginner novice",
                    )
                ]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_global_national_source_covers_any_country_and_level(self):
        source_ids = [
            source.id
            for source in sources_for_country(
                "BRA",
                level="introductory",
            )
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("usea", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region(
                "usa",
                level="advanced",
                include_planned=False,
            )
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_level_filter_keeps_matching_specific_levels(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "sources.json"
            source_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "id": "national_advanced_only",
                                "name": "National advanced-only source",
                                "priority": 5,
                                "scope": "national",
                                "regions": ["global"],
                                "countries": ["all_countries"],
                                "disciplines": ["eventing"],
                                "event_levels": ["advanced"],
                                "source_type": "national_federation",
                                "base_url": None,
                                "status": "planned",
                                "notes": "Test source.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            matching_ids = [
                source.id
                for source in sources_for_country(
                    "CAN",
                    level="advanced",
                    path=source_path,
                )
            ]
            non_matching_ids = [
                source.id
                for source in sources_for_country(
                    "CAN",
                    level="training",
                    path=source_path,
                )
            ]

        self.assertEqual(matching_ids, ["national_advanced_only"])
        self.assertEqual(non_matching_ids, [])


if __name__ == "__main__":
    unittest.main()
