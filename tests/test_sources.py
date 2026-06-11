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
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        national_sources = [
            source
            for source in payload["sources"]
            if source["scope"] == "national"
        ]

        self.assertEqual(payload["version"], 2)
        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source=source["id"]):
                self.assertEqual(source["event_levels"], ["all_eventing_levels"])

    def test_global_national_source_covers_every_country(self):
        source_ids = [
            source.id
            for source in sources_for_country("CHI", level="intro")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_priority_country_sources_apply_to_any_national_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("gbr", level="grassroots")
        ]

        self.assertEqual(
            source_ids,
            ["british_eventing", "global_national_federations"],
        )

    def test_fei_source_matches_international_eventing_levels(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="CCI5*-L")
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
