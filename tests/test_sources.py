import unittest

from equibets.sources import load_event_sources, sources_for_country, sources_for_region


class EventSourceTests(unittest.TestCase):
    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertEqual(sources[0].countries, ("all_countries",))

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

    def test_priority_national_sources_cover_all_eventing_levels(self):
        priority_source_ids = {
            "europe_national_federations",
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
        }

        national_sources = {
            source.id: source
            for source in load_event_sources()
            if source.id in priority_source_ids
        }

        self.assertEqual(set(national_sources), priority_source_ids)
        for source in national_sources.values():
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_country_lookup_includes_primary_priority_and_global_backfill(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("british_eventing", source_ids)

    def test_level_filter_uses_all_eventing_levels_wildcard(self):
        source_ids = [
            source.id
            for source in sources_for_country("USA", level="Beginner Novice")
        ]

        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_global_national_backfill_covers_all_countries_and_levels(self):
        source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )

        self.assertEqual(source.countries, ("all_countries",))
        self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_active_only_country_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id for source in sources_for_country("USA", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
