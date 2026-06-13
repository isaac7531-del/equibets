import json
import unittest

from equibets.sources import DATA_FILE, load_event_sources, sources_for_country, sources_for_region


ALL_NATIONAL_LEVELS = {
    "national_championship",
    "national_elite",
    "national_advanced",
    "national_intermediate",
    "national_preliminary",
    "national_novice",
    "national_introductory",
    "national",
    "regional",
    "local",
    "club",
    "schooling",
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

    def test_global_national_source_covers_all_countries_and_levels(self):
        sources = load_event_sources()
        global_source = next(
            source for source in sources if source.id == "global_national_federations"
        )

        self.assertEqual(global_source.countries, ("all_fei_member_nations",))
        self.assertTrue(ALL_NATIONAL_LEVELS.issubset(set(global_source.event_levels)))

    def test_national_sources_cover_all_domestic_levels(self):
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        for source in national_sources:
            with self.subTest(source_id=source.id):
                self.assertTrue(ALL_NATIONAL_LEVELS.issubset(set(source.event_levels)))

    def test_sources_for_country_uses_explicit_and_global_coverage(self):
        source_ids = [source.id for source in sources_for_country("gbr")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_sources_for_country_backfills_non_priority_fei_country(self):
        source_ids = [source.id for source in sources_for_country("CAN")]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_sources_for_country_active_only_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_country("CAN", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_country_coverage_metadata_tracks_fei_federation_count(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        self.assertEqual(payload["country_coverage"]["coverage_token"], "all_fei_member_nations")
        self.assertEqual(payload["country_coverage"]["verified_member_count"], 135)

    def test_sources_for_country_rejects_invalid_country_codes(self):
        with self.assertRaises(ValueError):
            sources_for_country("canada")


if __name__ == "__main__":
    unittest.main()
