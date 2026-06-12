import json
import unittest
from pathlib import Path

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_registry_declares_all_country_and_level_coverage(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["country_coverage"], "all_countries")
        self.assertEqual(payload["level_coverage"], "all_eventing_levels")

        global_source = next(
            source for source in payload["sources"] if source["id"] == "global_national_federations"
        )
        self.assertEqual(global_source["countries"], ["all_countries"])
        self.assertEqual(global_source["event_levels"], ["all_eventing_levels"])

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

    def test_country_filter_includes_priority_and_global_national_sources(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="Beginner Novice")
        ]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertLess(
            source_ids.index("usea"),
            source_ids.index("global_national_federations"),
        )

    def test_country_filter_uses_global_backfill_for_any_country_and_level(self):
        source_ids = [
            source.id for source in sources_for_country("JPN", level="grassroots")
        ]

        self.assertIn("global_national_federations", source_ids)

    def test_fei_international_level_uses_fei_source_only_when_active(self):
        source_ids = [
            source.id
            for source in sources_for_country(
                "USA",
                include_planned=False,
                level="fei_international",
            )
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
