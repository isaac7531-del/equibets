import json
import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_all_level_scope(self):
        with open("data/event_sources.json", encoding="utf-8") as source_file:
            registry = json.load(source_file)

        self.assertEqual(registry["version"], 2)
        self.assertEqual(registry["sources"][0]["countries"], ["all_countries"])
        self.assertEqual(registry["sources"][0]["event_levels"], ["all_eventing_levels"])
        self.assertIn(
            {
                "id": "global_national_federations",
                "countries": ["all_countries"],
                "event_levels": ["all_eventing_levels"],
            },
            [
                {
                    "id": source["id"],
                    "countries": source["countries"],
                    "event_levels": source["event_levels"],
                }
                for source in registry["sources"]
            ],
        )

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertTrue(sources[0].covers_country("bra"))
        self.assertTrue(sources[0].covers_level("starter"))

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

    def test_country_lookup_includes_country_specific_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("usa", level="starter")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_backfills_countries_without_specific_sources(self):
        source_ids = [source.id for source in sources_for_country("bra", level="grassroots")]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_country("usa", level="national", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
