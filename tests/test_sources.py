import json
import unittest

from equibets.sources import DATA_FILE, load_event_sources, sources_for_country, sources_for_region


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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_registry_declares_global_national_event_scope(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)
        self.assertIn("all_countries", payload["coverage_wildcards"]["countries"])
        self.assertIn("all_eventing_levels", payload["coverage_wildcards"]["event_levels"])

        global_source = next(
            source for source in load_event_sources() if source.id == "global_national_federations"
        )
        self.assertIn("all_countries", global_source.countries)
        self.assertIn("all_eventing_levels", global_source.event_levels)

    def test_national_sources_cover_all_eventing_levels(self):
        national_sources = [source for source in load_event_sources() if source.scope == "national"]

        self.assertGreater(len(national_sources), 0)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertIn("all_eventing_levels", source.event_levels)

    def test_sources_for_country_includes_global_backfill_for_any_country_and_level(self):
        source_ids = [
            source.id for source in sources_for_country("bra", level="grassroots")
        ]

        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_keeps_country_specific_priority(self):
        source_ids = [source.id for source in sources_for_country("GBR", level="novice")]

        self.assertLess(
            source_ids.index("british_eventing"),
            source_ids.index("global_national_federations"),
        )


if __name__ == "__main__":
    unittest.main()
