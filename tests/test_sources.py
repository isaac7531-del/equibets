import unittest

from equibets.sources import (
    ALL_COUNTRIES,
    ALL_EVENTING_LEVELS,
    load_event_sources,
    sources_for_country,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].countries, (ALL_COUNTRIES,))

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

    def test_national_sources_cover_all_domestic_eventing_levels(self):
        national_sources = [
            source
            for source in load_event_sources()
            if source.scope == "national"
        ]

        self.assertGreater(len(national_sources), 0)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, (ALL_EVENTING_LEVELS,))

    def test_global_national_backfill_covers_all_countries(self):
        source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )

        self.assertEqual(source.countries, (ALL_COUNTRIES,))
        self.assertEqual(source.event_levels, (ALL_EVENTING_LEVELS,))

    def test_sources_for_country_includes_country_specific_and_global_backfill(self):
        source_ids = [
            source.id
            for source in sources_for_country("usa", level="Beginner Novice")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_sources_for_country_uses_global_sources_for_unprioritized_countries(self):
        source_ids = [
            source.id
            for source in sources_for_country("CAN", level="regional")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_sources_for_country_without_level_includes_fei_first(self):
        source_ids = [source.id for source in sources_for_country("GBR")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
