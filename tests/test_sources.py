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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_global_national_source_covers_all_countries_and_levels(self):
        global_source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )

        self.assertIn("all_countries", global_source.countries)
        self.assertIn("all_levels", global_source.event_levels)

    def test_country_lookup_includes_global_national_backfill(self):
        source_ids = [source.id for source in sources_for_country("bra")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_includes_all_level_national_sources(self):
        source_ids = [source.id for source in sources_for_event_level("grassroots")]

        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)


if __name__ == "__main__":
    unittest.main()
