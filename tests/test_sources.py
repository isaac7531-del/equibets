import json
import unittest
from pathlib import Path

from equibets.sources import load_event_sources, sources_for_region


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
COVERAGE_FILE = DATA_DIR / "national_event_coverage.json"


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

    def test_national_coverage_metadata_references_configured_sources(self):
        sources_by_id = {source.id: source for source in load_event_sources()}
        coverage = _load_national_coverage()

        self.assertEqual(
            coverage["authority"]["affiliated_national_federation_count"],
            coverage["country_coverage"]["country_count"],
        )
        self.assertEqual(
            coverage["country_coverage"]["national_backfill_source_id"],
            "global_national_federations",
        )

        referenced_source_ids = set(coverage["country_coverage"]["priority_country_source_ids"])
        referenced_source_ids.add(coverage["country_coverage"]["primary_source_id"])
        referenced_source_ids.add(coverage["country_coverage"]["national_backfill_source_id"])

        for level_group in coverage["event_level_groups"]:
            referenced_source_ids.update(level_group["covered_by_source_ids"])
        for region in coverage["priority_regions"]:
            referenced_source_ids.update(region["source_ids"])

        self.assertLessEqual(referenced_source_ids, set(sources_by_id))

    def test_coverage_levels_match_source_level_declarations(self):
        sources_by_id = {source.id: source for source in load_event_sources()}
        coverage = _load_national_coverage()

        for level_group in coverage["event_level_groups"]:
            level_id = level_group["id"]
            for source_id in level_group["covered_by_source_ids"]:
                with self.subTest(level_id=level_id, source_id=source_id):
                    self.assertIn(level_id, sources_by_id[source_id].event_levels)


def _load_national_coverage():
    with COVERAGE_FILE.open(encoding="utf-8") as coverage_file:
        return json.load(coverage_file)


if __name__ == "__main__":
    unittest.main()
