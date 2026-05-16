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

    def test_registry_declares_all_country_all_level_coverage(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["coverage_scope"]["countries"], [ALL_COUNTRIES])
        self.assertEqual(
            payload["coverage_scope"]["event_levels"],
            [ALL_EVENTING_LEVELS],
        )

        global_source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )
        self.assertIn(ALL_COUNTRIES, global_source.countries)
        self.assertIn(ALL_EVENTING_LEVELS, global_source.event_levels)

    def test_country_selection_uses_global_backfill_for_any_level(self):
        source_ids = [source.id for source in sources_for_country("CAN", level="starter")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_selection_keeps_specific_national_source_before_backfill(self):
        source_ids = [source.id for source in sources_for_country("GBR", level="novice")]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertLess(
            source_ids.index("british_eventing"),
            source_ids.index("global_national_federations"),
        )

    def test_fei_international_level_keeps_primary_source_first(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="fei_international")
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
