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

    def test_registry_targets_all_countries_and_eventing_levels(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            registry = json.load(source_file)

        self.assertEqual(registry["version"], 2)

        source_by_id = {source.id: source for source in load_event_sources()}
        global_source = source_by_id["global_national_federations"]

        self.assertIn("all_countries", global_source.countries)
        self.assertIn("all_eventing_levels", global_source.event_levels)

    def test_country_lookup_covers_priority_and_backfill_sources(self):
        source_ids = [source.id for source in sources_for_country("USA", level="starter")]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_global_backfill_for_any_country(self):
        source_ids = [source.id for source in sources_for_country("CAN", level="training")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_lookup_keeps_fei_for_international_levels(self):
        source_ids = [source.id for source in sources_for_country("CAN", level="fei_international")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
