import json
from pathlib import Path
import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_registry_declares_all_country_all_level_national_scope(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        global_source = next(
            source
            for source in payload["sources"]
            if source["id"] == "global_national_federations"
        )

        self.assertEqual(payload["version"], 2)
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

    def test_country_lookup_covers_any_country_without_level_filter(self):
        source_ids = [source.id for source in sources_for_country("JPN")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("europe_national_federations", source_ids)

    def test_country_lookup_includes_regional_country_groups(self):
        source_ids = [source.id for source in sources_for_country("FRA", level="grassroots")]

        self.assertIn("europe_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_covers_any_eventing_level(self):
        source_ids = [source.id for source in sources_for_country("CAN", level="grassroots")]

        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_level_filter_normalizes_common_level_names(self):
        source_ids = [source.id for source in sources_for_country("BRA", level="FEI International")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
