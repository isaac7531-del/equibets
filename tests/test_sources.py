import unittest

from equibets.sources import (
    ALL_FEI_MEMBER_NATIONS,
    ALL_NATIONAL_EVENT_LEVELS,
    load_event_sources,
    national_event_sources,
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_national_event_scope_covers_all_countries_and_levels(self):
        sources_by_id = {source.id: source for source in load_event_sources()}
        global_source = sources_by_id["global_national_federations"]

        self.assertEqual(global_source.countries, (ALL_FEI_MEMBER_NATIONS,))
        self.assertEqual(global_source.event_levels, (ALL_NATIONAL_EVENT_LEVELS,))

        national_sources = [
            source for source in sources_by_id.values() if source.scope == "national"
        ]
        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source_id=source.id):
                self.assertIn(ALL_NATIONAL_EVENT_LEVELS, source.event_levels)

    def test_national_event_sources_can_filter_any_country_level_pair(self):
        source_ids = [
            source.id
            for source in national_event_sources(country="FRA", level="club")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_national_event_sources_prefers_specific_country_source(self):
        source_ids = [
            source.id
            for source in national_event_sources(country="GBR", level="grassroots")
        ]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertLess(
            source_ids.index("british_eventing"),
            source_ids.index("global_national_federations"),
        )


if __name__ == "__main__":
    unittest.main()
