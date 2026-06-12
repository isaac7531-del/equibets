import json
import unittest

from equibets.sources import (
    DATA_FILE,
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

    def test_national_event_sources_cover_all_eventing_levels(self):
        source_by_id = {source.id: source for source in load_event_sources()}
        expected_all_level_sources = {
            "europe_national_federations",
            "british_eventing",
            "equestrian_australia",
            "equestrian_sports_new_zealand",
            "usea",
            "global_national_federations",
        }

        for source_id in expected_all_level_sources:
            with self.subTest(source_id=source_id):
                self.assertEqual(source_by_id[source_id].event_levels, ("all_eventing_levels",))

    def test_global_national_source_covers_all_countries(self):
        sources = load_event_sources()
        global_source = next(
            source for source in sources if source.id == "global_national_federations"
        )

        self.assertEqual(global_source.countries, ("all_countries",))

    def test_country_lookup_backfills_any_country_at_national_levels(self):
        for country in ("BRA", "JPN", "RSA"):
            with self.subTest(country=country):
                source_ids = [
                    source.id for source in sources_for_country(country, level="introductory")
                ]

                self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_lookup_includes_priority_sources_for_all_levels(self):
        source_ids = [source.id for source in sources_for_country("gbr", level="training")]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_country_lookup_keeps_fei_first_for_international_levels(self):
        source_ids = [source.id for source in sources_for_country("BRA", level="CCI3*-S")]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertIn("global_national_federations", source_ids)

    def test_registry_declares_current_all_country_all_level_schema(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)
        self.assertIn("every country", payload["coverage_goal"])
        self.assertIn("every eventing level", payload["coverage_goal"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
