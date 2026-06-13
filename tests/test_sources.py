import json
import unittest

from equibets.sources import (
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_tracks_all_country_all_level_coverage(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        global_source = next(
            source
            for source in payload["sources"]
            if source["id"] == "global_national_federations"
        )

        self.assertEqual(payload["version"], 2)
        self.assertIn("starter", payload["national_event_levels"])
        self.assertIn("cci5_long", payload["fei_international_event_levels"])
        self.assertEqual(global_source["countries"], ["all_countries"])
        self.assertEqual(global_source["event_levels"], ["all_eventing_levels"])

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "americas": "americas_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "oceania": "oceania_national_federations",
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
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_country_lookup_uses_direct_and_global_sources(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="starter")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_lookup_uses_global_backfill_for_any_country(self):
        source_ids = [
            source.id for source in sources_for_country("BRA", level="novice")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_event_level_lookup_accepts_display_level_labels(self):
        cci4_short_source_ids = [
            source.id for source in sources_for_event_level("CCI4*-S")
        ]
        cci5_long_source_ids = [
            source.id for source in sources_for_country("GBR", level="CCI5-L")
        ]
        beginner_novice_source_ids = [
            source.id for source in sources_for_event_level("beginner novice")
        ]

        self.assertEqual(cci4_short_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", cci4_short_source_ids)
        self.assertEqual(cci5_long_source_ids[0], "data_fei")
        self.assertIn("british_eventing", cci5_long_source_ids)
        self.assertIn("global_national_federations", beginner_novice_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
