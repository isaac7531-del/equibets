import json
import unittest

from equibets.sources import (
    ALL_COUNTRIES,
    ALL_EVENTING_LEVELS,
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_region,
)

with DATA_FILE.open(encoding="utf-8") as source_file:
    REGISTRY_PAYLOAD = json.load(source_file)


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn(ALL_COUNTRIES, sources[0].countries)

    def test_registry_declares_all_country_all_level_coverage(self):
        self.assertEqual(REGISTRY_PAYLOAD["version"], 2)

        source_ids = {
            source["id"]
            for source in REGISTRY_PAYLOAD["sources"]
            if ALL_COUNTRIES in source["countries"]
            and ALL_EVENTING_LEVELS in source["event_levels"]
        }

        self.assertEqual(source_ids, {"global_national_federations"})

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

    def test_country_lookup_includes_exact_and_global_sources_for_any_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("gbr", level="grassroots")
        ]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_country_lookup_backfills_countries_without_priority_sources(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="starter")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_fei_source_matches_international_country_lookup(self):
        source_ids = [
            source.id
            for source in sources_for_country("BRA", level="fei_international")
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
