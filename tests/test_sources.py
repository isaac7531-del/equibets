import json
import unittest
from pathlib import Path

from equibets.sources import (
    load_event_sources,
    sources_for_country,
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

    def test_national_sources_cover_all_eventing_levels(self):
        national_sources = [
            source
            for source in load_event_sources()
            if source.scope == "national"
        ]

        self.assertGreater(len(national_sources), 0)
        for source in national_sources:
            with self.subTest(source_id=source.id):
                self.assertIn("all_eventing_levels", source.event_levels)

    def test_global_national_backfill_covers_all_countries(self):
        global_source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )

        self.assertIn("all_countries", global_source.countries)
        self.assertIn("all_eventing_levels", global_source.event_levels)

    def test_sources_for_country_includes_country_source_and_global_backfill(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="starter")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_sources_for_country_backfills_unknown_countries_at_any_level(self):
        source_ids = [source.id for source in sources_for_country("BRA", level="intro")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_registry_version_tracks_all_country_all_level_scope(self):
        with DATA_FILE.open(encoding="utf-8") as registry_file:
            payload = json.load(registry_file)

        self.assertEqual(payload["version"], 2)
        self.assertIn("all countries", payload["coverage_goal"])
        self.assertIn("all eventing levels", payload["coverage_goal"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
