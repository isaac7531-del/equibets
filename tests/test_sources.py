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

    def test_national_sources_cover_all_eventing_levels(self):
        sources = [
            source
            for source in load_event_sources()
            if source.scope == "national" and source.status == "planned"
        ]

        self.assertTrue(sources)
        for source in sources:
            with self.subTest(source=source.id):
                self.assertIn("all_eventing_levels", source.event_levels)

    def test_global_national_source_covers_any_country_and_level(self):
        source_ids = [
            source.id for source in sources_for_country("BRA", level="starter")
        ]

        self.assertIn("global_national_federations", source_ids)

    def test_priority_country_source_covers_any_eventing_level(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="modified")
        ]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_priority_region_source_covers_any_eventing_level(self):
        source_ids = [
            source.id for source in sources_for_region("usa", level="modified")
        ]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_registry_declares_all_country_national_backfill(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        global_source = next(
            source
            for source in payload["sources"]
            if source["id"] == "global_national_federations"
        )

        self.assertEqual(payload["version"], 2)
        self.assertIn("all_countries", global_source["countries"])
        self.assertIn("all_eventing_levels", global_source["event_levels"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
