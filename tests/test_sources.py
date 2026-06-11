import unittest

from equibets.sources import (
    load_event_coverage_targets,
    load_event_sources,
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
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "central_america_caribbean": "central_america_caribbean_national_federations",
            "south_america": "south_america_national_federations",
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_global_national_source_targets_all_countries_and_levels(self):
        targets = load_event_coverage_targets()
        sources = {source.id: source for source in load_event_sources()}
        global_source = sources["global_national_federations"]

        self.assertEqual(targets.countries, ("all_countries",))
        self.assertEqual(global_source.countries, targets.countries)
        self.assertEqual(global_source.event_levels, targets.event_levels)
        self.assertIn("starter", global_source.event_levels)
        self.assertIn("advanced", global_source.event_levels)
        self.assertIn("cci1_intro", global_source.event_levels)
        self.assertIn("cci5_long", global_source.event_levels)

    def test_regional_national_sources_cover_every_national_level(self):
        targets = load_event_coverage_targets()
        national_levels = set(targets.national_event_levels)

        for source in load_event_sources():
            if source.source_type != "federation_registry" or source.id == "global_national_federations":
                continue

            with self.subTest(source=source.id):
                self.assertEqual(source.scope, "national")
                self.assertTrue(national_levels.issubset(source.event_levels))


if __name__ == "__main__":
    unittest.main()
