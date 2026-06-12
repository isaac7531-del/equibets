import json
import unittest

from equibets.sources import DATA_FILE, load_event_sources, sources_for_country, sources_for_region


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_all_level_coverage(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        sources_by_id = {source["id"]: source for source in payload["sources"]}

        self.assertEqual(payload["version"], 2)
        self.assertEqual(
            sources_by_id["global_national_federations"]["countries"],
            ["all_countries"],
        )
        self.assertEqual(
            sources_by_id["global_national_federations"]["event_levels"],
            ["all_eventing_levels"],
        )

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

    def test_priority_national_sources_cover_all_eventing_levels(self):
        priority_national_source_ids = {
            "europe_national_federations",
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
        }
        sources = load_event_sources()

        for source in sources:
            if source.id in priority_national_source_ids:
                with self.subTest(source=source.id):
                    self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_country_lookup_includes_global_backfill_for_any_country(self):
        source_ids = [source.id for source in sources_for_country("BRA", level="national")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_lookup_keeps_priority_country_sources_before_global_backfill(self):
        source_ids = [source.id for source in sources_for_country("usa", level="training")]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_fei_level_lookup_includes_primary_source_and_all_level_backfill(self):
        source_ids = [source.id for source in sources_for_country("CHI", level="CCI3*-S")]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
