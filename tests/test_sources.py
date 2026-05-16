import json
import unittest
from pathlib import Path

from equibets.sources import (
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_level,
    sources_for_region,
)


NATIONAL_EVENT_LEVELS = {
    "national_championship",
    "advanced",
    "intermediate",
    "preliminary",
    "modified",
    "training",
    "novice",
    "beginner_novice",
    "starter",
    "grassroots",
    "regional",
    "state_or_provincial",
    "area",
    "local",
    "club",
    "schooling",
    "youth",
    "young_horse",
}


def registry_payload(path: Path = DATA_FILE):
    with path.open(encoding="utf-8") as source_file:
        return json.load(source_file)


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")

    def test_regions_include_fei_and_national_sources(self):
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

    def test_global_national_source_covers_all_countries_and_levels(self):
        sources = {source.id: source for source in load_event_sources()}
        global_source = sources["global_national_federations"]

        self.assertEqual(global_source.countries, ("all_fei_member_nations",))
        self.assertTrue(NATIONAL_EVENT_LEVELS.issubset(global_source.event_levels))

    def test_every_national_source_declares_full_level_scope(self):
        for source in load_event_sources():
            if source.scope != "national":
                continue

            with self.subTest(source_id=source.id):
                self.assertTrue(NATIONAL_EVENT_LEVELS.issubset(source.event_levels))

    def test_registry_top_level_declares_full_national_scope(self):
        payload = registry_payload()

        self.assertEqual(payload["country_coverage_goal"], "all_fei_member_nations")
        self.assertEqual(set(payload["national_event_levels"]), NATIONAL_EVENT_LEVELS)

    def test_country_lookup_uses_global_and_specific_national_sources(self):
        source_ids = [source.id for source in sources_for_country("gbr")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_uses_global_backfill_for_unlisted_country(self):
        source_ids = [source.id for source in sources_for_country("CAN")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_level_lookup_covers_international_and_national_levels(self):
        international_source_ids = [source.id for source in sources_for_level("CCI4-L")]
        national_source_ids = [source.id for source in sources_for_level("starter")]

        self.assertEqual(international_source_ids[0], "data_fei")
        self.assertIn("british_eventing", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
