import json
import unittest

from equibets.sources import (
    DATA_FILE,
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

    def test_registry_declares_all_country_all_level_coverage(self):
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))

        self.assertEqual(payload["coverage"]["countries"], ["all_countries"])
        self.assertEqual(
            payload["coverage"]["event_levels"],
            [
                "fei_international",
                "national_championship",
                "national",
                "regional",
                "local",
                "grassroots",
                "club",
            ],
        )
        self.assertEqual(
            payload["coverage"]["update_scope"],
            "national_events_all_countries_all_levels",
        )

    def test_global_regions_include_fei_and_national_sources(self):
        expected_national_sources = {
            "africa": "africa_national_federations",
            "asia": "asia_national_federations",
            "europe": "europe_national_federations",
            "north_america": "north_america_national_federations",
            "south_america": "south_america_national_federations",
            "oceania": "oceania_national_federations",
        }

        for region, regional_source_id in expected_national_sources.items():
            with self.subTest(region=region):
                source_ids = [source.id for source in sources_for_region(region)]
                self.assertEqual(source_ids[0], "data_fei")
                self.assertIn("global_national_federations", source_ids)
                self.assertIn(regional_source_id, source_ids)

    def test_country_lookup_uses_global_sources_and_known_national_sources(self):
        source_ids = [source.id for source in sources_for_country("USA")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)
        self.assertIn("usea", source_ids)

    def test_all_national_levels_have_source_coverage(self):
        national_levels = (
            "national_championship",
            "national",
            "regional",
            "local",
            "grassroots",
            "club",
        )

        for event_level in national_levels:
            with self.subTest(event_level=event_level):
                source_ids = [source.id for source in sources_for_event_level(event_level)]
                self.assertIn("global_national_federations", source_ids)

        self.assertEqual(
            [source.id for source in sources_for_event_level("fei_international")],
            ["data_fei"],
        )

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
