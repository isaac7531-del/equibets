import json
import unittest

from equibets.sources import DATA_FILE, load_event_sources, sources_for_country, sources_for_region


NATIONAL_EVENT_LEVELS = {
    "national_championship",
    "national",
    "state_or_province",
    "regional",
    "local",
    "grassroots",
    "training",
}

REGIONAL_REGISTRY_BY_REGION = {
    "africa": "africa_national_federations",
    "asia": "asia_national_federations",
    "europe": "europe_national_federations",
    "middle_east": "middle_east_national_federations",
    "north_america": "north_america_national_federations",
    "central_america_caribbean": "central_america_caribbean_national_federations",
    "south_america": "south_america_national_federations",
    "oceania": "oceania_national_federations",
}


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "central_america_caribbean": "central_america_caribbean_national_federations",
            "asia": "asia_national_federations",
            "middle_east": "middle_east_national_federations",
            "africa": "africa_national_federations",
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_registry_declares_all_region_and_level_coverage(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        sources_by_id = {source.id: source for source in load_event_sources()}

        self.assertEqual(set(payload["coverage_regions"]), set(REGIONAL_REGISTRY_BY_REGION))
        self.assertEqual(set(payload["national_event_levels"]), NATIONAL_EVENT_LEVELS)

        for region, source_id in REGIONAL_REGISTRY_BY_REGION.items():
            with self.subTest(region=region):
                source = sources_by_id[source_id]
                self.assertEqual(source.source_type, "federation_registry")
                self.assertIn(region, source.regions)
                self.assertIn(f"all_fei_{region}_member_nations", source.countries)
                self.assertTrue(NATIONAL_EVENT_LEVELS.issubset(source.event_levels))

        for source in sources_by_id.values():
            if source.scope == "national":
                with self.subTest(source_id=source.id):
                    self.assertTrue(NATIONAL_EVENT_LEVELS.issubset(source.event_levels))

    def test_sources_for_country_includes_exact_and_global_backfill(self):
        source_ids = [source.id for source in sources_for_country("gbr")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_accepts_fei_country_groups(self):
        source_ids = [
            source.id
            for source in sources_for_country("all_fei_south_america_member_nations")
        ]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("south_america_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)


if __name__ == "__main__":
    unittest.main()
