import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


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
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_global_national_source_covers_all_countries(self):
        sources = {source.id: source for source in load_event_sources()}

        self.assertEqual(
            sources["global_national_federations"].countries,
            ("all_countries",),
        )

    def test_country_lookup_includes_specific_and_global_sources(self):
        source_ids = [
            source.id for source in sources_for_country("USA", level="Starter")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_lookup_uses_global_backfill_for_any_country(self):
        source_ids = [
            source.id for source in sources_for_country("BRA", level="Beginner Novice")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_lookup_without_level_keeps_primary_source(self):
        source_ids = [source.id for source in sources_for_country("gbr")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_region_lookup_can_filter_to_national_levels(self):
        source_ids = [
            source.id for source in sources_for_region("usa", level="Training")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
