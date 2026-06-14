import unittest

from equibets.sources import (
    load_event_source_registry,
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

    def test_registry_targets_all_countries_and_all_levels(self):
        registry = load_event_source_registry()
        data_fei = next(source for source in registry.sources if source.id == "data_fei")
        global_backfill = next(
            source for source in registry.sources if source.id == "global_national_federations"
        )

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertIn("advanced", registry.coverage_targets.national_event_levels)
        self.assertIn("national_five_star", registry.coverage_targets.national_event_levels)
        self.assertIn("cci5_star_long", registry.coverage_targets.international_event_levels)
        self.assertEqual(
            set(registry.coverage_targets.national_event_levels),
            set(global_backfill.event_levels),
        )
        self.assertEqual(
            set(registry.coverage_targets.international_event_levels),
            set(data_fei.event_levels),
        )

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "europe": "europe_national_federations",
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
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

    def test_country_sources_include_exact_match_and_all_country_backfills(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_event_level_sources_cover_specific_national_and_fei_levels(self):
        national_source_ids = [source.id for source in sources_for_event_level("advanced")]
        fei_source_ids = [source.id for source in sources_for_event_level("CCI5*-L")]

        self.assertIn("global_national_federations", national_source_ids)
        self.assertIn("usea", national_source_ids)
        self.assertEqual(fei_source_ids, ["data_fei"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
