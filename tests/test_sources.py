import json
import unittest
from pathlib import Path

from equibets.sources import (
    load_event_sources,
    sources_for_country,
    sources_for_region,
)


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"


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

    def test_national_sources_cover_all_eventing_levels(self):
        national_sources = [
            source for source in load_event_sources() if source.scope == "national"
        ]

        self.assertTrue(national_sources)
        for source in national_sources:
            with self.subTest(source=source.id):
                self.assertEqual(source.event_levels, ("all_eventing_levels",))

    def test_global_national_source_covers_all_countries(self):
        with DATA_FILE.open(encoding="utf-8") as source_file:
            payload = json.load(source_file)

        self.assertEqual(payload["version"], 2)
        self.assertEqual(
            payload["coverage_wildcards"],
            {
                "countries": "all_countries",
                "levels": "all_eventing_levels",
            },
        )

        global_source = next(
            source
            for source in load_event_sources()
            if source.id == "global_national_federations"
        )
        self.assertEqual(global_source.countries, ("all_countries",))
        self.assertEqual(global_source.event_levels, ("all_eventing_levels",))

    def test_sources_for_country_uses_priority_and_global_national_sources(self):
        source_ids = [
            source.id
            for source in sources_for_country("gbr", level="grassroots")
        ]

        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)
        self.assertNotIn("data_fei", source_ids)

    def test_sources_for_country_backfills_unprioritized_countries(self):
        source_ids = [
            source.id
            for source in sources_for_country("CAN", level="regional")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_active_only_filter_keeps_current_primary_source(self):
        source_ids = [
            source.id
            for source in sources_for_region("usa", include_planned=False)
        ]

        self.assertEqual(source_ids, ["data_fei"])


if __name__ == "__main__":
    unittest.main()
