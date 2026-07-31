import unittest

from equibets.sources import (
    load_event_source_registry,
    load_event_sources,
    sources_for_country,
    sources_for_event_level,
    sources_for_region,
)


class EventSourceTests(unittest.TestCase):
    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.coverage_targets.countries, ("all_fei_member_nations",))
        self.assertIn("starter", registry.coverage_targets.national_and_regional_levels)
        self.assertIn("introductory", registry.coverage_targets.national_and_regional_levels)
        self.assertIn("national_five_star", registry.coverage_targets.national_and_regional_levels)
        self.assertIn("cci_intro", registry.coverage_targets.fei_levels)
        self.assertIn("cci1_intro", registry.coverage_targets.fei_levels)
        self.assertIn("cci5_long", registry.coverage_targets.fei_levels)
        self.assertIn("championship", registry.coverage_targets.fei_levels)

    def test_data_fei_is_primary_source(self):
        sources = load_event_sources()

        self.assertEqual(sources[0].id, "data_fei")
        self.assertEqual(sources[0].priority, 0)
        self.assertEqual(sources[0].base_url, "https://data.fei.org/")
        self.assertIn("cci5_long", sources[0].event_levels)

    def test_every_priority_region_includes_fei_regional_and_global_sources(self):
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

    def test_country_lookup_includes_fei_specific_and_global_sources(self):
        source_ids = [source.id for source in sources_for_country("usa")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("north_america_national_federations", source_ids)
        self.assertIn("usea", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_lookup_includes_regional_and_global_backfill_sources(self):
        source_ids = [source.id for source in sources_for_country("can")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("north_america_national_federations", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("usea", source_ids)

    def test_country_lookup_routes_known_countries_to_declared_regions(self):
        expected_sources = {
            "fra": "europe_national_federations",
            "bra": "south_america_national_federations",
            "zaf": "africa_national_federations",
        }

        for country, regional_source_id in expected_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(regional_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_event_level_lookup_separates_fei_and_national_levels(self):
        fei_source_ids = [source.id for source in sources_for_event_level("CCI3*-S")]
        cci_intro_source_ids = [source.id for source in sources_for_event_level("CCI Intro")]
        cci_one_intro_source_ids = [source.id for source in sources_for_event_level("CCI1*-Intro")]
        introductory_source_ids = [source.id for source in sources_for_event_level("Introductory")]
        national_source_ids = [source.id for source in sources_for_event_level("Training")]

        self.assertEqual(fei_source_ids, ["data_fei"])
        self.assertEqual(cci_intro_source_ids, ["data_fei"])
        self.assertEqual(cci_one_intro_source_ids, ["data_fei"])
        self.assertNotIn("data_fei", introductory_source_ids)
        self.assertIn("global_national_federations", introductory_source_ids)
        self.assertIn("central_america_caribbean_national_federations", introductory_source_ids)
        self.assertNotIn("data_fei", national_source_ids)
        self.assertIn("global_national_federations", national_source_ids)
        self.assertIn("north_america_national_federations", national_source_ids)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
