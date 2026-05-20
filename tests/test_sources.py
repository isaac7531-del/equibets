import json
import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].countries, ("all_countries",))

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
            if source.scope == "national"
        ]

        self.assertTrue(sources)
        for source in sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_country_lookup_includes_exact_and_global_national_sources(self):
        source_ids = [
            source.id
            for source in sources_for_country("GBR", level="grassroots")
        ]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_country_lookup_backfills_every_country_and_level(self):
        source_ids = [
            source.id
            for source in sources_for_country("CAN", level="introductory")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_international_level_lookup_keeps_fei_primary(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="fei_international")
        ]

        self.assertEqual(source_ids[0], "data_fei")

    def test_registry_declares_all_country_national_backfill(self):
        with open("data/event_sources.json", encoding="utf-8") as sources_file:
            payload = json.load(sources_file)

        self.assertEqual(payload["version"], 2)
        global_source = next(
            source
            for source in payload["sources"]
            if source["id"] == "global_national_federations"
        )
        self.assertEqual(global_source["countries"], ["all_countries"])
        self.assertEqual(global_source["event_levels"], ["all_eventing_levels"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
