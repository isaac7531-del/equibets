import unittest

from equibets.sources import (
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
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

    def test_global_scope_covers_all_countries_and_national_levels(self):
        global_backfill = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )

        self.assertIn("all_fei_member_nations", global_backfill.countries)
        self.assertEqual(
            global_backfill.event_levels,
            (
                "national",
                "regional",
                "state_provincial",
                "local",
                "club",
                "grassroots",
                "schooling",
            ),
        )

    def test_sources_for_country_includes_global_and_specific_coverage(self):
        gbr_source_ids = [source.id for source in sources_for_country("gbr")]
        brazil_source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(gbr_source_ids[0], "data_fei")
        self.assertIn("british_eventing", gbr_source_ids)
        self.assertIn("global_national_federations", gbr_source_ids)
        self.assertIn("data_fei", brazil_source_ids)
        self.assertIn("global_national_federations", brazil_source_ids)
        self.assertNotIn("usea", brazil_source_ids)

    def test_sources_for_event_level_includes_all_national_levels(self):
        grassroots_source_ids = [
            source.id for source in sources_for_event_level("grassroots")
        ]
        state_source_ids = [
            source.id for source in sources_for_event_level("state/provincial")
        ]

        self.assertIn("global_national_federation_directory", grassroots_source_ids)
        self.assertIn("global_national_federations", grassroots_source_ids)
        self.assertNotIn("data_fei", grassroots_source_ids)
        self.assertIn("equestrian_australia", state_source_ids)
        self.assertIn("usea", state_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
