import unittest

from equibets.sources import (
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

    def test_national_sources_cover_all_eventing_levels(self):
        sources_by_id = {source.id: source for source in load_event_sources()}

        for source_id in (
            "europe_national_federations",
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
            "global_national_federations",
        ):
            with self.subTest(source_id=source_id):
                self.assertEqual(
                    sources_by_id[source_id].event_levels,
                    ("all_eventing_levels",),
                )

    def test_global_national_source_covers_every_country(self):
        sources_by_id = {source.id: source for source in load_event_sources()}

        self.assertEqual(
            sources_by_id["global_national_federations"].countries,
            ("all_countries",),
        )

        source_ids = [
            source.id for source in sources_for_country("BRA", level="grassroots")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_lookup_includes_priority_source_and_backfill(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="starter")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_level_filter_keeps_fei_for_international_events(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="fei_international")
        ]

        self.assertEqual(
            source_ids,
            ["data_fei", "usea", "global_national_federations"],
        )

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
