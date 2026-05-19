import json
import unittest

from equibets.sources import (
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_event,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_national_event_scope_covers_all_countries_and_levels(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        self.assertEqual(payload["national_event_scope"]["country_coverage"], "all_fei_member_nations")
        self.assertEqual(
            payload["national_event_scope"]["level_coverage"],
            "all_national_eventing_levels",
        )
        self.assertIn("starter", payload["national_event_scope"]["levels"])
        self.assertIn("national_championship", payload["national_event_scope"]["levels"])

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

    def test_country_lookup_includes_global_national_backfill(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_event_lookup_respects_country_and_level_scope(self):
        starter_source_ids = [source.id for source in sources_for_event("JPN", "Starter")]
        five_star_source_ids = [source.id for source in sources_for_event("GBR", "CCI5*-L")]

        self.assertIn("global_national_federations", starter_source_ids)
        self.assertEqual(five_star_source_ids[0], "data_fei")


if __name__ == "__main__":
    unittest.main()
