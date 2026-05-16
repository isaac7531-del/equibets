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
        self.assertIn("all_countries", sources[0].countries)
        self.assertIn("all_eventing_levels", sources[0].event_levels)

    def test_registry_declares_all_country_and_level_scope(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        sources = {source.id: source for source in load_event_sources()}

        self.assertEqual(payload["version"], 2)
        self.assertIn("all_countries", sources["global_national_federations"].countries)
        self.assertIn(
            "all_eventing_levels",
            sources["global_national_federations"].event_levels,
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

    def test_sources_for_country_cover_any_country_and_level(self):
        for country, level in [
            ("USA", "starter"),
            ("BRA", "national"),
            ("Japan", "CCI4*-L"),
        ]:
            with self.subTest(country=country, level=level):
                source_ids = [
                    source.id for source in sources_for_country(country, level=level)
                ]

                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_keeps_specific_national_source_priority(self):
        source_ids = [source.id for source in sources_for_country("usa", level="regional")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertLess(
            source_ids.index("usea"),
            source_ids.index("global_national_federations"),
        )

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region(
                "usa", include_planned=False, level="national"
            )
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
