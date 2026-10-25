"""Tests for Equiresults classification parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.equiresults import (
    EquiresultsClass,
    parse_results_page,
    pratoni_cci3s_2026_class,
    pratoni_ccij2s_2026_class,
    pratoni_cci4l_2026_class,
    pratoni_ccip2s_2026_class,
)


COMPETITION = EquiresultsClass(
    url="https://www.equiresults.com/competition/15751/404300/results",
    event_name="Pratoni del Vivaro · CCI2*-S",
    level="CCI2*-S",
    event_date=date(2026, 10, 22),
    country="ITA",
)
COLLECTED_AT = datetime(2026, 10, 24, 12, 20, tzinfo=timezone.utc)

FINISHED_PAGE = """
<h2>Classifica 003 - CCI2*-S</h2>
<table id="results_table_404300">
<tr id="result_404300_77" data-ranking-position="1">
  <td>1</td>
  <td>77</td>
  <td>
    <a href="/rider/9229">BERTOLI Evelina</a>
    <span class="flagContainer-right"><span class="clearfix">ITA</span></span>
    <a href="/horse/189940">PEPPERSHAKE Z</a>
  </td>
  <td class="splitBold"><a href="/score-card">30.50</a></td>
  <td class="split">0</td>
  <td class="split">69.520</td>
  <td class="splitBold">30.50</td>
  <td class="split">5</td>
  <td class="splitBold secondPhase">0</td>
  <td class="split secondPhase">77.27</td>
  <td class="split secondPhase">0.00</td>
  <td class="split secondPhase">1</td>
  <td class="splitBold secondPhase">30.50</td>
  <td class="split secondPhase">2</td>
  <td class="splitBold thirdPhase">0</td>
  <td class="split thirdPhase">5.3</td>
  <td class="split thirdPhase">0.40</td>
  <td class="split thirdPhase">7</td>
  <td class="splitBold">30.90</td>
</tr>
<tr id="result_404300_57">
  <td>29</td>
  <td>57</td>
  <td>
    <a href="/rider/2">LUCIANI Victoria</a>
    <span class="flagContainer-right"><span class="clearfix">ITA</span></span>
    <a href="/horse/3">ALTATURK CARISMA</a>
  </td>
  <td class="splitBold">37.70</td>
  <td class="split">0</td>
  <td class="split">62.260</td>
  <td class="splitBold">37.70</td>
  <td class="split">29</td>
  <td class="splitBold secondPhase">0</td>
  <td class="split secondPhase">77.07</td>
  <td class="split secondPhase">0.00</td>
  <td class="split secondPhase">1</td>
  <td class="splitBold secondPhase">37.70</td>
  <td class="split secondPhase">15</td>
  <td class="splitBold thirdPhase">40 <span class="clearfix small">r(5b) r(6)</span></td>
  <td class="split thirdPhase">5.53</td>
  <td class="split thirdPhase">49.60</td>
  <td class="split thirdPhase">29</td>
  <td class="splitBold">87.30</td>
</tr>
<tr id="result_404300_52">
  <td>Rit.</td>
  <td>52</td>
  <td>
    <a href="/rider/9">INTRECCIALAGLI Samuel</a>
    <span class="flagContainer-right"><span class="clearfix">ITA</span></span>
    <a href="/horse/10">ANNSFORT HQ POWER</a>
  </td>
  <td class="splitBold">36.20</td>
  <td class="split">0</td>
  <td class="split">63.810</td>
  <td class="splitBold">36.20</td>
  <td class="split">22</td>
  <td class="splitBold secondPhase">20 Automatic Elimination</td>
  <td class="split secondPhase">78.57</td>
  <td class="split secondPhase">20.00</td>
  <td class="split secondPhase">31</td>
  <td class="splitBold secondPhase">56.20</td>
  <td class="split secondPhase">32</td>
  <td class="splitBold thirdPhase">W.D. after S.O.</td>
  <td class="split thirdPhase">0</td>
  <td class="split thirdPhase">0.00</td>
  <td class="split thirdPhase">Rit.</td>
  <td class="splitBold">0.00</td>
</tr>
<tr id="result_404300_54">
  <td></td>
  <td>54</td>
  <td>
    <a href="/rider/4">GUALTIERI Lisa</a>
    <span class="flagContainer-right"><span class="clearfix">FRA</span></span>
    <a href="/horse/5">IT'S ME DES SALINES</a>
  </td>
  <td class="splitBold">30.40</td>
  <td class="split">0</td>
  <td class="split">69.640</td>
  <td class="splitBold">30.40</td>
  <td class="split">3</td>
  <td class="splitBold secondPhase">Elim. S.J.</td>
  <td class="split secondPhase"></td>
  <td class="split secondPhase">0.00</td>
  <td class="split secondPhase"></td>
  <td class="splitBold secondPhase"></td>
  <td class="split secondPhase"></td>
  <td class="splitBold thirdPhase"></td>
  <td class="split thirdPhase"></td>
  <td class="split thirdPhase">0.00</td>
  <td class="split thirdPhase"></td>
  <td class="splitBold">0.00</td>
</tr>
<tr id="result_404300_88">
  <td>Rit.</td>
  <td>88</td>
  <td>
    <a href="/rider/11">RYAN Philip</a>
    <span class="flagContainer-right"><span class="clearfix">IRL</span></span>
    <a href="/horse/12">DREAM POINT B</a>
  </td>
  <td class="splitBold">39.20</td>
  <td class="split">0</td>
  <td class="split">60.760</td>
  <td class="splitBold">39.20</td>
  <td class="split">11</td>
  <td class="splitBold secondPhase">0</td>
  <td class="split secondPhase">81.54</td>
  <td class="split secondPhase">0.00</td>
  <td class="split secondPhase">1</td>
  <td class="splitBold secondPhase">39.20</td>
  <td class="split secondPhase">6</td>
  <td class="splitBold thirdPhase">Rit. X-Country r(10d) R(12a)</td>
  <td class="split thirdPhase">0</td>
  <td class="split thirdPhase">0.00</td>
  <td class="split thirdPhase">Rit.</td>
  <td class="splitBold">0.00</td>
</tr>
</table>
"""


class EquiresultsParserTests(unittest.TestCase):
    def test_finished_page_keeps_numeric_phases_and_skips_elimination(self) -> None:
        results = parse_results_page(FINISHED_PAGE, competition=COMPETITION, collected_at=COLLECTED_AT)

        self.assertEqual(
            [
                (
                    result.rider_name,
                    result.horse_name,
                    result.dressage_score,
                    result.show_jumping_penalties,
                    result.cross_country_jump_penalties,
                    result.cross_country_time_penalties,
                    result.finishing_score,
                )
                for result in results
            ],
            [
                ("BERTOLI Evelina (ITA)", "PEPPERSHAKE Z", 30.5, 0.0, 0.0, 0.4, 30.9),
                ("LUCIANI Victoria (ITA)", "ALTATURK CARISMA", 37.7, 0.0, 40.0, 9.6, 87.3),
            ],
        )
        self.assertEqual(results[0].event_name, "Pratoni del Vivaro · CCI2*-S")
        self.assertEqual(results[0].event_date, date(2026, 10, 22))
        self.assertEqual(results[0].country, "ITA")
        self.assertEqual(results[0].source_id, "equiresults")

    def test_provisional_page_is_not_a_finish(self) -> None:
        html = FINISHED_PAGE.replace("<h2>Classifica 003 - CCI2*-S</h2>", "<h2>Classifica Provvisoria</h2>")

        self.assertEqual(parse_results_page(html, competition=COMPETITION, collected_at=COLLECTED_AT), [])

    def test_live_heading_is_not_a_finish(self) -> None:
        html = FINISHED_PAGE.replace("<h2>Classifica 003 - CCI2*-S</h2>", "<h2>Classifica live</h2>")

        self.assertEqual(parse_results_page(html, competition=COMPETITION, collected_at=COLLECTED_AT), [])

    def test_pratoni_cci3s_class_uses_the_published_final_date(self) -> None:
        competition = pratoni_cci3s_2026_class()

        self.assertEqual(competition.url, "https://www.equiresults.com/competition/15751/404299/results")
        self.assertEqual(competition.event_name, "Pratoni del Vivaro · CCI3*-S")
        self.assertEqual(competition.level, "CCI3*-S")
        self.assertEqual(competition.event_date, date(2026, 10, 23))
        self.assertEqual(competition.country, "ITA")

    def test_pratoni_ccij2s_class_uses_the_published_final_date(self) -> None:
        competition = pratoni_ccij2s_2026_class()

        self.assertEqual(competition.url, "https://www.equiresults.com/competition/15751/404304/results")
        self.assertEqual(competition.event_name, "Pratoni del Vivaro · CCIJ2*-S")
        self.assertEqual(competition.level, "CCIJ2*-S")
        self.assertEqual(competition.event_date, date(2026, 10, 23))
        self.assertEqual(competition.country, "ITA")

    def test_pratoni_cci4l_class_uses_the_published_final_date(self) -> None:
        competition = pratoni_cci4l_2026_class()

        self.assertEqual(competition.url, "https://www.equiresults.com/competition/15751/404305/results")
        self.assertEqual(competition.event_name, "Pratoni del Vivaro · CCI4*-L")
        self.assertEqual(competition.level, "CCI4*-L")
        self.assertEqual(competition.event_date, date(2026, 10, 23))
        self.assertEqual(competition.country, "ITA")

    def test_pratoni_ccip2s_class_uses_the_published_final_date(self) -> None:
        competition = pratoni_ccip2s_2026_class()

        self.assertEqual(competition.url, "https://www.equiresults.com/competition/15751/404303/results")
        self.assertEqual(competition.event_name, "Pratoni del Vivaro · CCIP2-S")
        self.assertEqual(competition.level, "CCIP2-S")
        self.assertEqual(competition.event_date, date(2026, 10, 23))
        self.assertEqual(competition.country, "ITA")

    def test_blank_cross_country_cell_rejects_the_class(self) -> None:
        html = FINISHED_PAGE.replace(
            '<td class="splitBold thirdPhase">0</td>',
            '<td class="splitBold thirdPhase"></td>',
            1,
        )

        self.assertEqual(parse_results_page(html, competition=COMPETITION, collected_at=COLLECTED_AT), [])


if __name__ == "__main__":
    unittest.main()
