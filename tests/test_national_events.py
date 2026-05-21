import unittest

from equibets.national_events import (
    event_levels_for_countries,
    expand_country_scope,
    federation_for_country,
    federations_for_source,
    load_national_federations,
)
from equibets.sources import country_codes_for_source, load_event_sources


class NationalFederationTests(unittest.TestCase):
    def test_registry_covers_all_fei_national_federations(self):
        federations = load_national_federations()

        self.assertEqual(len(federations), 135)
        self.assertEqual(federations[0].noc_code, "ALB")
        self.assertEqual(federations[-1].noc_code, "ZIM")

    def test_country_scopes_expand_symbolic_tokens(self):
        all_codes = expand_country_scope(["all_fei_member_nations"])
        european_codes = expand_country_scope(["all_fei_europe_member_nations"])

        self.assertEqual(len(all_codes), 135)
        self.assertIn("USA", all_codes)
        self.assertIn("GBR", european_codes)
        self.assertNotIn("USA", european_codes)

    def test_priority_national_sources_cover_their_countries_and_all_levels(self):
        usa_sources = federation_for_country("usa").coverage_sources
        usea_countries = [federation.noc_code for federation in federations_for_source("usea")]

        self.assertEqual(usea_countries, ["USA"])
        self.assertIn("usea", usa_sources)
        self.assertEqual(event_levels_for_countries(["USA"]), ("national", "regional"))

    def test_event_source_country_tokens_resolve_against_national_registry(self):
        sources = {source.id: source for source in load_event_sources()}

        self.assertEqual(len(country_codes_for_source(sources["global_national_federations"])), 135)
        self.assertEqual(country_codes_for_source(sources["usea"]), ("USA",))
        self.assertIn("GBR", country_codes_for_source(sources["europe_national_federations"]))


if __name__ == "__main__":
    unittest.main()
