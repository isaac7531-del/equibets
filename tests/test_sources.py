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

    def test_registry_declares_all_country_all_level_scope(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        sources = load_event_sources()
        global_source = next(source for source in sources if source.id == "global_national_federations")

        self.assertEqual(payload["version"], 2)
        self.assertIn("all_countries", payload["coverage"]["countries"])
        self.assertIn("all_eventing_levels", payload["coverage"]["event_levels"])
        self.assertEqual(global_source.countries, ("all_countries",))
        self.assertEqual(global_source.event_levels, ("all_eventing_levels",))

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

    def test_country_lookup_returns_specific_and_global_national_sources(self):
        source_ids = [source.id for source in sources_for_country("GBR", level="introductory")]

        self.assertEqual(source_ids, ["british_eventing", "global_national_federations"])

    def test_country_lookup_backfills_unknown_country_at_any_level(self):
        source_ids = [source.id for source in sources_for_country("BRA", level="novice")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_lookup_keeps_fei_primary_when_level_is_unspecified(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)


if __name__ == "__main__":
    unittest.main()
