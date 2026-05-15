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
        sources_by_id = {source.id: source for source in load_event_sources()}
        global_source = sources_by_id["global_national_federations"]

        self.assertEqual(global_source.countries, ("all_countries",))
        self.assertEqual(global_source.event_levels, ("all_eventing_levels",))

    def test_country_lookup_includes_global_backfill_for_any_country(self):
        source_ids = [source.id for source in sources_for_country("CAN")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_filters_by_all_eventing_levels(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="Grassroots")
        ]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_region_lookup_can_filter_by_event_level(self):
        source_ids = [
            source.id
            for source in sources_for_region("uk", level="training-level")
        ]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_registry_documents_coverage_groups(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        self.assertEqual(payload["version"], 2)
        self.assertIn("all_countries", payload["coverage_groups"]["countries"])
        self.assertIn(
            "all_eventing_levels",
            payload["coverage_groups"]["event_levels"],
        )

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
