import json
import unittest

from equibets.sources import (
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_level,
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

    def test_registry_declares_global_country_and_level_scope(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        global_source = next(
            source for source in load_event_sources() if source.id == "global_national_federations"
        )

        self.assertIn("all_countries_with_national_eventing", payload["country_scope"])
        self.assertIn("starter", payload["event_level_catalog"]["national"])
        self.assertIn("cci5_l", payload["event_level_catalog"]["fei"])
        self.assertEqual(global_source.countries, ("all_countries",))
        self.assertEqual(global_source.event_levels, ("all_event_levels",))

    def test_country_lookup_uses_global_backfill_for_non_priority_countries(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("usea", source_ids)

    def test_country_lookup_keeps_direct_national_sources_when_available(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_level_lookup_covers_grassroots_and_fei_levels(self):
        starter_source_ids = [source.id for source in sources_for_level("Starter")]
        cci_source_ids = [source.id for source in sources_for_level("CCI3*-S")]

        self.assertIn("global_national_federations", starter_source_ids)
        self.assertNotIn("data_fei", starter_source_ids)
        self.assertEqual(cci_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", cci_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
