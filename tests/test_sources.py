import unittest

from equibets.sources import (
    expand_country_codes,
    load_event_sources,
    load_national_federations,
    national_event_levels,
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

    def test_national_federation_registry_covers_all_fei_member_nations(self):
        federations = load_national_federations()
        noc_codes = [federation.noc for federation in federations]

        self.assertEqual(len(federations), 135)
        self.assertEqual(len(noc_codes), len(set(noc_codes)))
        self.assertEqual(noc_codes, sorted(noc_codes))
        self.assertIn("GBR", noc_codes)
        self.assertIn("USA", noc_codes)
        self.assertIn("NZL", noc_codes)

    def test_national_event_levels_include_national_and_regional_tiers(self):
        self.assertEqual(national_event_levels(), ("national", "regional"))

    def test_country_coverage_tokens_expand_to_concrete_federations(self):
        all_member_codes = expand_country_codes(("all_fei_member_nations",))
        european_codes = expand_country_codes(("all_fei_europe_member_nations",))

        self.assertEqual(len(all_member_codes), 135)
        self.assertIn("AUS", all_member_codes)
        self.assertIn("GER", european_codes)
        self.assertIn("GBR", european_codes)
        self.assertNotIn("USA", european_codes)
        self.assertNotIn("AUS", european_codes)

    def test_source_country_coverage_can_be_resolved_without_placeholders(self):
        for source in load_event_sources():
            with self.subTest(source=source.id):
                country_codes = expand_country_codes(source.countries)

                self.assertTrue(country_codes)
                self.assertFalse(any(code.startswith("all_") for code in country_codes))


if __name__ == "__main__":
    unittest.main()
