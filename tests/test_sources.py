import json
import unittest

from equibets.sources import (
    DATA_FILE,
    load_event_level_groups,
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

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [source.id for source in sources_for_region("usa", include_planned=False)]

        self.assertEqual(source_ids, ["data_fei"])

    def test_registry_declares_all_country_and_all_level_scope(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["country_scope"], ["all_fei_member_nations"])
        level_groups = load_event_level_groups()
        self.assertIn("grassroots", level_groups["all_national_event_levels"])
        self.assertIn("cci5", level_groups["all_fei_international_levels"])

        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]
        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source_id=source.id):
                self.assertEqual(source.event_levels, ("all_national_event_levels",))

    def test_sources_for_country_supports_every_country_and_level(self):
        canadian_grassroots_sources = [
            source.id for source in sources_for_country("CAN", level="grassroots")
        ]
        british_intro_sources = [
            source.id for source in sources_for_country("gbr", level="Beginner Novice")
        ]
        fei_championship_sources = [
            source.id for source in sources_for_country("NZL", level="CCI5")
        ]

        self.assertEqual(canadian_grassroots_sources, ["global_national_federations"])
        self.assertEqual(
            british_intro_sources,
            ["british_eventing", "global_national_federations"],
        )
        self.assertEqual(fei_championship_sources, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
