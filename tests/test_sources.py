import json
import unittest

from equibets.sources import (
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_country_and_level,
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

    def test_registry_scope_covers_all_countries_and_levels(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        global_source = next(
            source
            for source in payload["sources"]
            if source["id"] == "global_national_federations"
        )

        self.assertEqual(payload["priority_regions"], ["global"])
        self.assertEqual(payload["country_scope"], ["all_fei_member_nations"])
        self.assertEqual(payload["event_level_scope"], ["all_eventing_levels"])
        self.assertIn("all_fei_member_nations", global_source["countries"])
        self.assertIn("all_eventing_levels", global_source["event_levels"])

    def test_sources_for_country_includes_global_national_source_for_any_country(self):
        for country in ("CHI", "JPN", "ZAF"):
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_and_level_matches_all_national_levels(self):
        source_ids = [source.id for source in sources_for_country_and_level("CHI", "Starter")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_sources_for_country_and_level_keeps_fei_primary_for_international_levels(self):
        source_ids = [source.id for source in sources_for_country_and_level("GBR", "CCI3*-S")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
