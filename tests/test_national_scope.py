import unittest

from equibets.national_scope import (
    build_update_plan,
    load_national_event_scope,
    national_sources_for_country,
    national_update_sources,
    public_update_sources,
)


class NationalEventScopeTests(unittest.TestCase):
    def test_scope_tracks_all_fei_countries_and_domestic_levels(self):
        scope = load_national_event_scope()
        all_countries = scope.country_group("all_fei_member_nations")

        self.assertIsNotNone(all_countries)
        self.assertEqual(all_countries.member_count, 135)
        self.assertTrue(all_countries.covers_country("CAN"))
        self.assertEqual(scope.all_national_event_levels, ("national", "regional"))
        self.assertIn(
            "every published national",
            scope.event_level_groups[0].class_policy,
        )

    def test_public_update_sources_follow_scope_order(self):
        source_ids = [source.id for source in public_update_sources()]

        self.assertEqual(source_ids[0], "data_fei")
        self.assertEqual(source_ids[-1], "global_national_federations")

    def test_national_update_sources_exclude_fei_primary(self):
        source_ids = [source.id for source in national_update_sources()]

        self.assertNotIn("data_fei", source_ids)
        self.assertIn("british_eventing", source_ids)
        self.assertIn("global_national_federations", source_ids)

    def test_country_filter_includes_specific_and_global_backfill_sources(self):
        source_ids = [
            source.id
            for source in national_sources_for_country("USA", event_level="regional")
        ]

        self.assertEqual(source_ids, ["usea", "global_national_federations"])

    def test_country_filter_uses_global_backfill_for_non_priority_country(self):
        source_ids = [
            source.id
            for source in national_sources_for_country("CAN", event_level="national")
        ]

        self.assertEqual(source_ids, ["global_national_federations"])

    def test_country_filter_rejects_fei_international_level(self):
        source_ids = [
            source.id
            for source in national_sources_for_country("USA", event_level="fei_international")
        ]

        self.assertEqual(source_ids, [])

    def test_update_plan_defaults_to_all_countries_and_levels(self):
        plan = build_update_plan()

        self.assertEqual(plan["countries"], "all_fei_member_nations")
        self.assertEqual(plan["event_levels"], ["national", "regional"])
        self.assertEqual(plan["national_results_output"], "data/national_results.json")
        self.assertIn(
            "global_national_federations",
            {source["id"] for source in plan["sources"]},
        )


if __name__ == "__main__":
    unittest.main()
