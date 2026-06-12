import json
import unittest

from equibets.sources import DATA_FILE, load_event_sources, sources_for_country, sources_for_region


class EventSourceTests(unittest.TestCase):
    def test_registry_tracks_all_country_all_level_coverage(self):
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

        sources = {
            source.id: source
            for source in load_event_sources()
            if source.id in priority_national_source_ids
        }

        self.assertEqual(set(sources), priority_national_source_ids)
        for source in sources.values():
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_country_lookup_includes_priority_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("USA", level="starter")]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_lookup_uses_global_backfill_for_any_country(self):
        source_ids = [source.id for source in sources_for_country("BRA", level="novice")]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_level_filter_keeps_fei_for_international_results(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="fei_international")
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)


if __name__ == "__main__":
    unittest.main()
