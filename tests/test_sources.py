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

    def test_active_only_filter_includes_national_sources(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei", "usea", "global_national_federations"])

    def test_global_national_source_covers_all_countries_and_levels(self):
        global_source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )

        self.assertIn("all_fei_member_nations", global_source.countries)
        self.assertEqual(
            global_source.event_levels,
            ("national", "regional", "local", "grassroots", "schooling"),
        )

    def test_sources_can_be_selected_by_country(self):
        source_ids = [source.id for source in sources_for_country("BRA")]

        self.assertEqual(source_ids, ["data_fei", "global_national_federations"])

    def test_sources_can_be_selected_by_local_event_level(self):
        source_ids = [source.id for source in sources_for_event_level("local")]

        self.assertEqual(
            source_ids,
            [
                "europe_national_federations",
                "british_eventing",
                "equestrian_australia",
                "equestrian_sports_new_zealand",
                "usea",
                "global_national_federations",
            ],
        )


if __name__ == "__main__":
    unittest.main()
