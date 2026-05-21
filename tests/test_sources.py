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
        sources = {
            source.id: source
            for source in load_event_sources()
            if source.scope == "national"
        }

        for source_id, source in sources.items():
            with self.subTest(source_id=source_id):
                self.assertIn("all_eventing_levels", source.event_levels)

    def test_global_national_source_covers_all_countries(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)

        source = next(
            item
            for item in payload["sources"]
            if item["id"] == "global_national_federations"
        )
        self.assertEqual(source["countries"], ["all_countries"])
        self.assertEqual(source["event_levels"], ["all_eventing_levels"])

    def test_country_lookup_uses_global_national_backfill_for_any_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("bra", level="introductory")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_priority_country_lookup_keeps_specific_national_source(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="grassroots")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
