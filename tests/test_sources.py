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

    def test_registry_scope_tracks_all_countries_and_levels(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)
        global_source = next(
            source
            for source in payload["sources"]
            if source["id"] == "global_national_federations"
        )
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_lookup_includes_global_national_source_for_any_country(self):
        source_ids = [
            source.id for source in sources_for_country("BRA", level="grassroots")
        ]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_country_specific_source(self):
        source_ids = [
            source.id for source in sources_for_country("usa", level="regional")
        ]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_level_filter_keeps_fei_for_international_results(self):
        source_ids = [
            source.id for source in sources_for_country("GER", level="fei_international")
        ]

        self.assertEqual(source_ids[0], "data_fei")

    def test_region_lookup_can_filter_by_level(self):
        source_ids = [source.id for source in sources_for_region("usa", level="starter")]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)


if __name__ == "__main__":
    unittest.main()
