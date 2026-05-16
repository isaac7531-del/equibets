import json
import unittest

from equibets.sources import (
    DATA_FILE,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


NATIONAL_EVENT_LEVELS = {
    "national_championship",
    "national_elite",
    "national_advanced",
    "national_intermediate",
    "national_preliminary",
    "national_training",
    "national_novice",
    "national_beginner_novice",
    "national_introductory",
    "regional",
    "local",
    "club",
    "grassroots",
    "schooling",
    "starter",
    "pony_youth",
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

    def test_national_event_scope_covers_all_countries_and_levels(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(
            payload["national_event_scope"]["countries"],
            ["all_fei_member_nations"],
        )
        self.assertTrue(
            NATIONAL_EVENT_LEVELS.issubset(
                set(payload["national_event_scope"]["event_levels"])
            )
        )

        global_source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )
        self.assertEqual(global_source.countries, ("all_fei_member_nations",))
        self.assertTrue(
            NATIONAL_EVENT_LEVELS.issubset(set(global_source.event_levels))
        )

    def test_sources_for_country_include_specific_and_global_sources(self):
        uk_source_ids = [source.id for source in sources_for_country("gbr")]
        brazil_source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(uk_source_ids[0], "data_fei")
        self.assertIn("british_eventing", uk_source_ids)
        self.assertIn("global_national_federations", uk_source_ids)
        self.assertEqual(brazil_source_ids[0], "data_fei")
        self.assertIn("global_national_federations", brazil_source_ids)
        self.assertNotIn("british_eventing", brazil_source_ids)

    def test_sources_for_event_level_include_all_national_levels(self):
        club_source_ids = [source.id for source in sources_for_event_level("club")]
        training_source_ids = [
            source.id for source in sources_for_event_level("training")
        ]
        cci_source_ids = [source.id for source in sources_for_event_level("CCI2*-L")]

        self.assertIn("global_national_federations", club_source_ids)
        self.assertIn("british_eventing", club_source_ids)
        self.assertNotIn("data_fei", club_source_ids)
        self.assertIn("global_national_federations", training_source_ids)
        self.assertEqual(cci_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
