import unittest

from equibets.sources import (
    load_event_sources,
    load_national_event_levels,
    load_national_federations,
    national_federation_for_country,
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_national_sources_cover_all_configured_national_levels(self):
        national_level_ids = {level.id for level in load_national_event_levels()}
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertGreaterEqual(len(national_level_ids), 10)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertTrue(national_level_ids.issubset(set(source.event_levels)))

    def test_national_federation_manifest_covers_all_fei_members(self):
        federations = load_national_federations()
        noc_codes = [federation.noc_code for federation in federations]

        self.assertEqual(len(federations), 135)
        self.assertEqual(len(noc_codes), len(set(noc_codes)))
        self.assertIn("GBR", noc_codes)
        self.assertIn("USA", noc_codes)
        self.assertIn("ZIM", noc_codes)
        self.assertTrue(
            all(federation.event_levels for federation in federations),
            "Every federation should inherit the national level coverage list.",
        )

    def test_country_lookup_preserves_priority_source_overrides(self):
        expectations = {
            "GBR": [
                "data_fei",
                "europe_national_federations",
                "british_eventing",
                "global_national_federations",
            ],
            "AUS": [
                "data_fei",
                "equestrian_australia",
                "global_national_federations",
            ],
            "FRA": [
                "data_fei",
                "europe_national_federations",
                "global_national_federations",
            ],
            "USA": [
                "data_fei",
                "usea",
                "global_national_federations",
            ],
        }

        for country_code, expected_source_ids in expectations.items():
            with self.subTest(country=country_code):
                source_ids = [
                    source.id for source in sources_for_country(country_code)
                ]
                self.assertEqual(source_ids, expected_source_ids)

    def test_country_lookup_can_filter_to_active_sources(self):
        source_ids = [
            source.id for source in sources_for_country("GBR", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])

    def test_national_federation_for_country_uses_noc_codes(self):
        federation = national_federation_for_country("nzl")

        self.assertEqual(federation.noc_code, "NZL")
        self.assertEqual(federation.country, "New Zealand")
        self.assertIn("equestrian_sports_new_zealand", federation.source_ids)


if __name__ == "__main__":
    unittest.main()
