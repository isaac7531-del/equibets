import unittest

from equibets.sources import (
    DOMESTIC_EVENT_LEVELS,
    FEI_EVENT_LEVELS,
    load_event_source_registry,
    load_event_sources,
    normalize_event_level,
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

    def test_registry_declares_all_country_and_level_targets(self):
        registry = load_event_source_registry()

        self.assertEqual(registry.version, 2)
        self.assertEqual(registry.primary_source_id, "data_fei")
        self.assertEqual(
            registry.coverage_targets.countries, ("all_fei_member_nations",)
        )
        self.assertEqual(
            registry.coverage_targets.domestic_event_levels, DOMESTIC_EVENT_LEVELS
        )
        self.assertEqual(registry.coverage_targets.fei_event_levels, FEI_EVENT_LEVELS)
        self.assertEqual(
            registry.coverage_targets.event_levels,
            DOMESTIC_EVENT_LEVELS + FEI_EVENT_LEVELS,
        )

    def test_priority_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "middle_east": "middle_east_national_federations",
            "north_america": "north_america_national_federations",
            "central_america_caribbean": (
                "central_america_caribbean_national_federations"
            ),
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

    def test_country_lookup_includes_regional_and_priority_sources(self):
        expected_country_sources = {
            "ZAF": "africa_national_federations",
            "JPN": "asia_national_federations",
            "IRL": "europe_national_federations",
            "UAE": "middle_east_national_federations",
            "CAN": "north_america_national_federations",
            "JAM": "central_america_caribbean_national_federations",
            "ARG": "south_america_national_federations",
            "AUS": "equestrian_australia",
            "NZL": "equestrian_sports_new_zealand",
            "USA": "usea",
            "GBR": "british_eventing",
        }

        for country, national_source_id in expected_country_sources.items():
            with self.subTest(country=country):
                source_ids = [source.id for source in sources_for_country(country)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn(national_source_id, source_ids)
                self.assertIn("global_national_federations", source_ids)

    def test_country_specific_sources_only_match_their_country_codes(self):
        argentina_source_ids = [source.id for source in sources_for_country("ARG")]

        self.assertNotIn("british_eventing", argentina_source_ids)
        self.assertNotIn("equestrian_australia", argentina_source_ids)
        self.assertNotIn("equestrian_sports_new_zealand", argentina_source_ids)
        self.assertNotIn("usea", argentina_source_ids)

    def test_event_level_lookup_covers_all_domestic_levels(self):
        for event_level in DOMESTIC_EVENT_LEVELS:
            with self.subTest(event_level=event_level):
                source_ids = [
                    source.id for source in sources_for_event_level(event_level)
                ]
                self.assertIn("global_national_federations", source_ids)
                self.assertNotIn("data_fei", source_ids)

    def test_event_level_lookup_covers_all_fei_levels(self):
        for event_level in FEI_EVENT_LEVELS:
            with self.subTest(event_level=event_level):
                source_ids = [
                    source.id for source in sources_for_event_level(event_level)
                ]
                self.assertEqual(source_ids, ["data_fei"])

    def test_common_event_level_labels_are_normalized(self):
        expected_labels = {
            "CCI5*-L": "cci5_long",
            "CCI3*-S": "cci3_short",
            "CCI1*-Intro": "cci1_intro",
            "CCI Intro": "cci_intro",
            "prelim": "preliminary",
            "National 3*": "national_three_star",
        }

        for label, event_level in expected_labels.items():
            with self.subTest(label=label):
                self.assertEqual(normalize_event_level(label), event_level)

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
