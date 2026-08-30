"""Tests for Rechenstelle live leaderboard parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.rechenstelle import (
    RechenstelleBoard,
    _LeaderboardParser,
    hambach_aug_2026_boards,
    parse_leaderboard_results,
    segersjo_aug_2026_boards,
)


SAMPLE_HTML = """
<html>
  <head><title>LeaderBoard · Millstreet 2026 · CH-M-U25-C</title></head>
  <body>
    <p class="lastupdate">Last Update: Jul 23 2026 5:01PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>302</td>
          <td class="riderCell"><span class="riderName">Calvin B&Ouml;CKMANN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Altair de la Cense</span></td>
          <td>456,0</td>
          <td>72,38</td>
          <td>27,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>332</td>
          <td class="riderCell"><span class="riderName">Jennifer KUEHNLE</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Sammy Davis Junior</span></td>
          <td>446,0</td>
          <td>70,79</td>
          <td>29,2</td>
          <td>2.</td>
          <td>20,0</td>
          <td>1,6</td>
          <td>50,8</td>
          <td>2.</td>
          <td>4,0</td>
          <td></td>
          <td>54,8</td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>340</td>
          <td class="riderCell"><span class="riderName">Maddison PERIES</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Vivero DH Z</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>337</td>
          <td class="riderCell"><span class="riderName">Alice CASBURN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Topspin</span></td>
          <td>420,0</td>
          <td>66,67</td>
          <td>33,3</td>
          <td>16.</td>
          <td>2,8</td>
          <td>06:37</td>
          <td>36,1</td>
          <td>1.</td>
          <td></td>
          <td></td>
          <td class="borderCell">WDbSJ</td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>256</td>
          <td class="riderCell"><span class="riderName">Savannah CARLESUND</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">First Choice 33</span></td>
          <td>388,5</td>
          <td>61,67</td>
          <td>38,3</td>
          <td>36.</td>
          <td>0,0</td>
          <td>07:19</td>
          <td>38,3</td>
          <td>36.</td>
          <td></td>
          <td></td>
          <td class="borderCell">NAbSJ</td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>111</td>
          <td class="riderCell"><span class="riderName">Kaylawna SMITH-COOK</span></td>
          <td><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Calling Cooley</span></td>
          <td>538,5</td>
          <td>71,80</td>
          <td>28,2</td>
          <td>1.</td>
          <td></td>
          <td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SHORT_FORMAT_HTML = """
<html>
  <head><title>LeaderBoard · Millstreet 2026 · CCI3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Jul 25 2026 10:23AM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Jumping</th><th>Rank after Jumping</th>
          <th>Cross-Country</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>601</td>
          <td class="riderCell"><span class="riderName">Ian CASSELLS</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Cooley Capri Sun</span></td>
          <td>526,0</td>
          <td>70,13</td>
          <td>29,9</td>
          <td>2.</td>
          <td>0,0</td>
          <td class="good">73,22</td>
          <td>29,9</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>8.</strong></td>
          <td>608</td>
          <td class="riderCell"><span class="riderName">Kevin MCNAB</span></td>
          <td><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Newmarket Amy</span></td>
          <td>525,0</td>
          <td>70,00</td>
          <td>30,0</td>
          <td>3.</td>
          <td>4,0</td>
          <td>70,31</td>
          <td>34,0</td>
          <td>8.</td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

LONG_FORMAT_CLOCK_TIME_HTML = """
<html>
  <head><title>LeaderBoard · Millstreet 2026 · CCI3*-L</title></head>
  <body>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>102</td>
          <td class="riderCell"><span class="riderName">Hallie COON</span></td>
          <td><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Boleybawn Oliva</span></td>
          <td>493,0</td>
          <td>65,73</td>
          <td>34,3</td>
          <td>9.</td>
          <td>2,8</td>
          <td>08:35</td>
          <td>37,1</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_START_LIST_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 12 2026 1:15PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>09:30:00</td>
          <td>107</td>
          <td class="riderCell"><span class="riderName">Daniel DUNST</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUT.PNG" alt="AUT"></td>
          <td class="horseCell"><span class="horseName">Chevalier 97</span></td>
          <td>&nbsp;&nbsp;&nbsp;</td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>09:37:00</td>
          <td>165</td>
          <td class="riderCell"><span class="riderName">Clarke JOHNSTONE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Rocket Man</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_FIRST_HOUR_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 10:17AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>1.</td>
          <td>165</td>
          <td class="riderCell"><span class="riderName">Clarke JOHNSTONE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Rocket Man</span></td>
          <td>513,5</td>
          <td>71,32</td>
          <td>28,7</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>129</td>
          <td class="riderCell"><span class="riderName">Benjamin MASSIE</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Figaro Fonroy</span></td>
          <td>61,5</td>
          <td>64,00</td>
          <td>36,0</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>10:19:00</td>
          <td>172</td>
          <td class="riderCell"><span class="riderName">Robin GODEL</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Grandeur de Lully CH</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_REVISED_MARKS_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 11:09AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>165</td>
          <td class="riderCell"><span class="riderName">Clarke JOHNSTONE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Rocket Man</span></td>
          <td>513,5</td>
          <td>71,32</td>
          <td>28,7</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>172</td>
          <td class="riderCell"><span class="riderName">Robin GODEL</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Grandeur de Lully CH</span></td>
          <td>503,0</td>
          <td>69,86</td>
          <td>30,1</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>140</td>
          <td class="riderCell"><span class="riderName">Libussa L&Uuml;BBEKE</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Caramia FRH</span></td>
          <td>495,0</td>
          <td>68,75</td>
          <td>31,3</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>7.</strong></td>
          <td>114</td>
          <td class="riderCell"><span class="riderName">Senne VERVAECKE</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Google van Alsingen</span></td>
          <td>(R)467,0</td>
          <td>64,86</td>
          <td>35,1</td>
          <td>7.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>11:16:00</td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_AFTERNOON_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 1:09PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>167</td>
          <td class="riderCell"><span class="riderName">Jonelle PRICE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Senor Crocodillo</span></td>
          <td>524,5</td>
          <td>72,85</td>
          <td>27,2</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>165</td>
          <td class="riderCell"><span class="riderName">Clarke JOHNSTONE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Rocket Man</span></td>
          <td>513,5</td>
          <td>71,32</td>
          <td>28,7</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>136</td>
          <td class="riderCell"><span class="riderName">Gemma STEVENS</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Flash Cooley</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>110</td>
          <td class="riderCell"><span class="riderName">Maarten BOON</span></td>
          <td><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Gravin van Cantos</span></td>
          <td>494,0</td>
          <td>68,61</td>
          <td>31,4</td>
          <td>6.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1400_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 2:00PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>167</td>
          <td class="riderCell"><span class="riderName">Jonelle PRICE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Senor Crocodillo</span></td>
          <td>524,5</td>
          <td>72,85</td>
          <td>27,2</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>8.</strong></td>
          <td>185</td>
          <td class="riderCell"><span class="riderName">Phillip DUTTON</span></td>
          <td><sup>*</sup><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Denim</span></td>
          <td>485,5</td>
          <td>67,43</td>
          <td>32,6</td>
          <td>8.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>19.</strong></td>
          <td>105</td>
          <td class="riderCell"><span class="riderName">Sam WOODS</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">SS Eight Count</span></td>
          <td>451,0</td>
          <td>62,64</td>
          <td>37,4</td>
          <td>19.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>25.</strong></td>
          <td>151</td>
          <td class="riderCell"><span class="riderName">Francesco AONDIO BERTERO</span></td>
          <td><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">It's Athene</span></td>
          <td>423,5</td>
          <td>58,82</td>
          <td>41,2</td>
          <td>25.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

AACHEN_LIVE_1502_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 3:02PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>167</td>
          <td class="riderCell"><span class="riderName">Jonelle PRICE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Senor Crocodillo</span></td>
          <td>524,5</td>
          <td>72,85</td>
          <td>27,2</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>127</td>
          <td class="riderCell"><span class="riderName">Alexis GOURY</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Je'vall</span></td>
          <td>516,0</td>
          <td>71,67</td>
          <td>28,3</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>165</td>
          <td class="riderCell"><span class="riderName">Clarke JOHNSTONE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Rocket Man</span></td>
          <td>513,5</td>
          <td>71,32</td>
          <td>28,7</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>136</td>
          <td class="riderCell"><span class="riderName">Gemma STEVENS</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Flash Cooley</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>29.</strong></td>
          <td>121</td>
          <td class="riderCell"><span class="riderName">Matěj SUKDOLÁK</span></td>
          <td><sup>*</sup><img src="../../../../flags/CZE.PNG" alt="CZE"></td>
          <td class="horseCell"><span class="horseName">Qaid</span></td>
          <td>403,0</td>
          <td>55,97</td>
          <td>44,0</td>
          <td>29.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

AACHEN_LIVE_1506_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 3:06PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>167</td>
          <td class="riderCell"><span class="riderName">Jonelle PRICE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Senor Crocodillo</span></td>
          <td>524,5</td>
          <td>72,85</td>
          <td>27,2</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>127</td>
          <td class="riderCell"><span class="riderName">Alexis GOURY</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Je'vall</span></td>
          <td>515,0</td>
          <td>71,53</td>
          <td>28,5</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>10.</strong></td>
          <td>173</td>
          <td class="riderCell"><span class="riderName">Mélody JOHNER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Erin</span></td>
          <td>467,0</td>
          <td>67,41</td>
          <td>32,6</td>
          <td>10.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

AACHEN_LIVE_1602_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 4:02PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent1">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>167</td>
          <td class="riderCell"><span class="riderName">Jonelle PRICE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Senor Crocodillo</span></td>
          <td>524,5</td>
          <td>72,85</td>
          <td>27,2</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>137</td>
          <td class="riderCell"><span class="riderName">Malin HANSEN-HOTOPP</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Carlitos Quidditch K</span></td>
          <td>514,0</td>
          <td>71,39</td>
          <td>28,6</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>11.</strong></td>
          <td>173</td>
          <td class="riderCell"><span class="riderName">Mélody JOHNER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Erin</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>11.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

AACHEN_LIVE_1658_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 4:58PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent1">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>166</td>
          <td class="riderCell"><span class="riderName">Samantha LISSINGTON</span></td>
          <td><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Lucas Stone</span></td>
          <td>506,0</td>
          <td>70,28</td>
          <td>29,7</td>
          <td>7.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>9.</strong></td>
          <td>102</td>
          <td class="riderCell"><span class="riderName">Olivia BARTON</span></td>
          <td><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">APH Sodoku</span></td>
          <td>499,5</td>
          <td>69,38</td>
          <td>30,6</td>
          <td>9.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>38.</strong></td>
          <td>154</td>
          <td class="riderCell"><span class="riderName">Paolo TORLONIA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Zinny</span></td>
          <td>(R)426,0</td>
          <td>59,17</td>
          <td>40,8</td>
          <td>38.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

AACHEN_LIVE_1000_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 10:00AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>127</td>
          <td class="riderCell"><span class="riderName">Alexis GOURY</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Je'Vall</span></td>
          <td>515,0</td>
          <td>71,53</td>
          <td>28,5</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>123</td>
          <td class="riderCell"><span class="riderName">Peter T. FLARUP</span></td>
          <td><img src="../../../../flags/DEN.PNG" alt="DEN"></td>
          <td class="horseCell"><span class="horseName">H.Carald Z</span></td>
          <td>178,0</td>
          <td>68,46</td>
          <td>31,5</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>28.</strong></td>
          <td>143</td>
          <td class="riderCell"><span class="riderName">Bal&aacute;zs KAIZINGER</span></td>
          <td><img src="../../../../flags/HUN.PNG" alt="HUN"></td>
          <td class="horseCell"><span class="horseName">Clover 15</span></td>
          <td>466,0</td>
          <td>64,72</td>
          <td>35,3</td>
          <td>28.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>32.</strong></td>
          <td>170</td>
          <td class="riderCell"><span class="riderName">Joanna PAWLAK</span></td>
          <td><img src="../../../../flags/POL.PNG" alt="POL"></td>
          <td class="horseCell"><span class="horseName">Armin de Monsieur</span></td>
          <td>452,0</td>
          <td>62,78</td>
          <td>37,2</td>
          <td>32.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>36.</strong></td>
          <td>159</td>
          <td class="riderCell"><span class="riderName">Noor SLAOUI</span></td>
          <td><img src="../../../../flags/MAR.PNG" alt="MAR"></td>
          <td class="horseCell"><span class="horseName">Legende P</span></td>
          <td>441,5</td>
          <td>61,32</td>
          <td>38,7</td>
          <td>36.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>44.</strong></td>
          <td>181</td>
          <td class="riderCell"><span class="riderName">Weerapat PITAKANONDA</span></td>
          <td><img src="../../../../flags/THA.PNG" alt="THA"></td>
          <td class="horseCell"><span class="horseName">B.Grimm Chateau de Versailles M2S</span></td>
          <td>422,0</td>
          <td>58,61</td>
          <td>41,4</td>
          <td>44.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1007_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 10:07AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>119</td>
          <td class="riderCell"><span class="riderName">Alex HUA TIAN</span></td>
          <td><img src="../../../../flags/CHN.PNG" alt="CHN"></td>
          <td class="horseCell"><span class="horseName">Chicko</span></td>
          <td>185,5</td>
          <td>68,70</td>
          <td>31,9</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>26.</strong></td>
          <td>123</td>
          <td class="riderCell"><span class="riderName">Peter T. FLARUP</span></td>
          <td><img src="../../../../flags/DEN.PNG" alt="DEN"></td>
          <td class="horseCell"><span class="horseName">H.Carald Z</span></td>
          <td>467,0</td>
          <td>64,86</td>
          <td>35,1</td>
          <td>26.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>46.</strong></td>
          <td>181</td>
          <td class="riderCell"><span class="riderName">Weerapat PITAKANONDA</span></td>
          <td><img src="../../../../flags/THA.PNG" alt="THA"></td>
          <td class="horseCell"><span class="horseName">B.Grimm Chateau de Versailles M2S</span></td>
          <td>422,0</td>
          <td>58,61</td>
          <td>41,4</td>
          <td>46.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1102_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 11:02AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>169</td>
          <td class="riderCell"><span class="riderName">Monica SPENCER</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Artist</span></td>
          <td>512,0</td>
          <td>71,11</td>
          <td>28,9</td>
          <td>6.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>11.</strong></td>
          <td>186</td>
          <td class="riderCell"><span class="riderName">Boyd MARTIN</span></td>
          <td><sup>*</sup><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Cooley Nutcracker</span></td>
          <td>497,5</td>
          <td>69,10</td>
          <td>30,9</td>
          <td>11.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>17.</strong></td>
          <td>119</td>
          <td class="riderCell"><span class="riderName">Alex HUA TIAN</span></td>
          <td><img src="../../../../flags/CHN.PNG" alt="CHN"></td>
          <td class="horseCell"><span class="horseName">Chicko</span></td>
          <td>486,0</td>
          <td>67,50</td>
          <td>32,5</td>
          <td>17.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>41.</strong></td>
          <td>108</td>
          <td class="riderCell"><span class="riderName">Katrin KHODDAM-HAZRATI</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUT.PNG" alt="AUT"></td>
          <td class="horseCell"><span class="horseName">Renegade</span></td>
          <td>444,5</td>
          <td>61,74</td>
          <td>38,3</td>
          <td>41.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>44.</strong></td>
          <td>120</td>
          <td class="riderCell"><span class="riderName">Pavel BŘEZINA</span></td>
          <td><sup>*</sup><img src="../../../../flags/CZE.PNG" alt="CZE"></td>
          <td class="horseCell"><span class="horseName">Turin</span></td>
          <td>441,0</td>
          <td>61,25</td>
          <td>38,8</td>
          <td>44.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1105_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 11:05AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>101</td>
          <td class="riderCell"><span class="riderName">Oliver BARRETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Sandhills Briar</span></td>
          <td>22,0</td>
          <td>73,33</td>
          <td>26,7</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>169</td>
          <td class="riderCell"><span class="riderName">Monica SPENCER</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Artist</span></td>
          <td>512,0</td>
          <td>71,11</td>
          <td>28,9</td>
          <td>7.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1105_BARRETT_REVISED_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 11:05AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>101</td>
          <td class="riderCell"><span class="riderName">Oliver BARRETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Sandhills Briar</span></td>
          <td>146,5</td>
          <td>69,76</td>
          <td>30,2</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1151_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 11:51AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>8.</strong></td>
          <td>150</td>
          <td class="riderCell"><span class="riderName">Austin O'CONNOR</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Colorado Blue</span></td>
          <td>511,0</td>
          <td>70,97</td>
          <td>29,0</td>
          <td>8.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>9.</strong></td>
          <td>128</td>
          <td class="riderCell"><span class="riderName">Gaspard MAKSUD</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Zaragoza</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>9.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>19.</strong></td>
          <td>101</td>
          <td class="riderCell"><span class="riderName">Oliver BARRETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Sandhills Briar</span></td>
          <td>(R)491,5</td>
          <td>68,26</td>
          <td>31,7</td>
          <td>19.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>38.</strong></td>
          <td>178</td>
          <td class="riderCell"><span class="riderName">Louise ROMEIKE</span></td>
          <td><sup>*</sup><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Caspian 15</span></td>
          <td>466,0</td>
          <td>64,72</td>
          <td>35,3</td>
          <td>38.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>59.</strong></td>
          <td>117</td>
          <td class="riderCell"><span class="riderName">Carlos PARRO</span></td>
          <td><sup>*</sup><img src="../../../../flags/BRA.PNG" alt="BRA"></td>
          <td class="horseCell"><span class="horseName">Safira</span></td>
          <td>(R)402,0</td>
          <td>55,83</td>
          <td>44,2</td>
          <td>59.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>61.</strong></td>
          <td>174</td>
          <td class="riderCell"><span class="riderName">Nadja MINDER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Top Job's Jalisco</span></td>
          <td>385,5</td>
          <td>53,54</td>
          <td>46,5</td>
          <td>61.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1301_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 1:01PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>148</td>
          <td class="riderCell"><span class="riderName">Georgie GOSS</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Kojak</span></td>
          <td>199,5</td>
          <td>68,79</td>
          <td>31,2</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>21.</strong></td>
          <td>113</td>
          <td class="riderCell"><span class="riderName">Karin DONCKERS</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Leipheimer van't Verahof</span></td>
          <td>492,0</td>
          <td>68,33</td>
          <td>31,7</td>
          <td>21.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>26.</strong></td>
          <td>134</td>
          <td class="riderCell"><span class="riderName">Caroline HARRIS</span></td>
          <td><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">D. Day</span></td>
          <td>485,0</td>
          <td>67,36</td>
          <td>32,6</td>
          <td>26.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>32.</strong></td>
          <td>152</td>
          <td class="riderCell"><span class="riderName">Andrea CINCINNATI</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Cecelia Lad</span></td>
          <td>(R)477,0</td>
          <td>66,25</td>
          <td>33,8</td>
          <td>32.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1324_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 1:24PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>12.</strong></td>
          <td>141</td>
          <td class="riderCell"><span class="riderName">Christoph WAHLER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">D'Accord FRH</span></td>
          <td>508,5</td>
          <td>70,63</td>
          <td>29,4</td>
          <td>12.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>17.</strong></td>
          <td>148</td>
          <td class="riderCell"><span class="riderName">Georgie GOSS</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Kojak</span></td>
          <td>496,5</td>
          <td>68,96</td>
          <td>31,0</td>
          <td>17.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>34.</strong></td>
          <td>162</td>
          <td class="riderCell"><span class="riderName">Jillian GIESSEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Seattle Park</span></td>
          <td>476,0</td>
          <td>66,11</td>
          <td>33,9</td>
          <td>34.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>35.</strong></td>
          <td>152</td>
          <td class="riderCell"><span class="riderName">Andrea CINCINNATI</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Cecelia Lad</span></td>
          <td>474,5</td>
          <td>65,90</td>
          <td>34,1</td>
          <td>35.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1517_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 3:17PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>188</td>
          <td class="riderCell"><span class="riderName">Tamra SMITH</span></td>
          <td><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Lillet 3</span></td>
          <td>525,5</td>
          <td>72,99</td>
          <td>27,0</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>11.</strong></td>
          <td>109</td>
          <td class="riderCell"><span class="riderName">Lea SIEGL</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUT.PNG" alt="AUT"></td>
          <td class="horseCell"><span class="horseName">Watermill Giorgio RS</span></td>
          <td>510,0</td>
          <td>70,83</td>
          <td>29,2</td>
          <td>11.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>16.</strong></td>
          <td>184</td>
          <td class="riderCell"><span class="riderName">William COLEMAN</span></td>
          <td><sup>*</sup><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Diabolo</span></td>
          <td>504,0</td>
          <td>70,00</td>
          <td>30,0</td>
          <td>16.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>18.</strong></td>
          <td>130</td>
          <td class="riderCell"><span class="riderName">Astier NICOLAS</span></td>
          <td><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Alertamalib'Or</span></td>
          <td>(R)499,5</td>
          <td>69,38</td>
          <td>30,6</td>
          <td>18.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>38.</strong></td>
          <td>168</td>
          <td class="riderCell"><span class="riderName">Tim PRICE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Falco</span></td>
          <td>477,5</td>
          <td>66,32</td>
          <td>33,7</td>
          <td>38.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1620_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 4:20PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>7,5</td>
          <td>76,90</td>
          <td>23,1</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1622_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 4:22PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1657_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 4:57PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>35.</strong></td>
          <td>176</td>
          <td class="riderCell"><span class="riderName">Frida ANDERSEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Box Leo</span></td>
          <td>488,0</td>
          <td>67,78</td>
          <td>32,2</td>
          <td>35.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>42.</strong></td>
          <td>153</td>
          <td class="riderCell"><span class="riderName">Vittoria PANIZZON</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">DHI Jackpot</span></td>
          <td>483,0</td>
          <td>67,08</td>
          <td>32,9</td>
          <td>42.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>44.</strong></td>
          <td>112</td>
          <td class="riderCell"><span class="riderName">Lara DE LIEDEKERKE-MEIER</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Kiarado d'Arville</span></td>
          <td>481,0</td>
          <td>66,81</td>
          <td>33,2</td>
          <td>44.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>67.</strong></td>
          <td>161</td>
          <td class="riderCell"><span class="riderName">Sanne DE JONG</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Enjoy</span></td>
          <td>450,0</td>
          <td>62,50</td>
          <td>37,5</td>
          <td>67.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1900_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026  7:00PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>42.</strong></td>
          <td>153</td>
          <td class="riderCell"><span class="riderName">Vittoria PANIZZON</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">DHI Jackpot</span></td>
          <td>483,0</td>
          <td>67,08</td>
          <td>32,9</td>
          <td>42.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1002_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026 10:02AM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>13:39:00</td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>13:55:00</td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>103</td>
          <td class="riderCell"><span class="riderName">Sophia HILL</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Humble Glory</span></td>
          <td>449,5</td>
          <td>62,43</td>
          <td>37,6</td>
          <td>68.</td>
          <td>0,0</td>
          <td class="good">09:45</td>
          <td>37,6</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>172</td>
          <td class="riderCell"><span class="riderName">Robin GODEL</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Grandeur de Lully CH</span></td>
          <td>503,0</td>
          <td>69,86</td>
          <td>30,1</td>
          <td>22.</td>
          <td>10,4</td>
          <td>10:16</td>
          <td>40,5</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>165</td>
          <td class="riderCell"><span class="riderName">Clarke JOHNSTONE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Rocket Man</span></td>
          <td>513,5</td>
          <td>71,32</td>
          <td>28,7</td>
          <td>12.</td>
          <td></td>
          <td></td>
          <td>EL XC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>159</td>
          <td class="riderCell"><span class="riderName">Noor SLAOUI</span></td>
          <td><img src="../../../../flags/MAR.PNG" alt="MAR"></td>
          <td class="horseCell"><span class="horseName">Legende P</span></td>
          <td>441,5</td>
          <td>61,32</td>
          <td>38,7</td>
          <td>72.</td>
          <td></td>
          <td></td>
          <td>WDbXC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>126</td>
          <td class="riderCell"><span class="riderName">Sanna SILTAKORPI</span></td>
          <td><img src="../../../../flags/FIN.PNG" alt="FIN"></td>
          <td class="horseCell"><span class="horseName">Bofey Click</span></td>
          <td>442,0</td>
          <td>61,39</td>
          <td>38,6</td>
          <td>71.</td>
          <td></td>
          <td></td>
          <td>WDbXC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td>09:43:00</td>
          <td>153</td>
          <td class="riderCell"><span class="riderName">Vittoria PANIZZON</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">DHI Jackpot</span></td>
          <td>483,0</td>
          <td>67,08</td>
          <td>32,9</td>
          <td>42.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1103_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026 11:03AM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>13:39:00</td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>13:55:00</td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>182</td>
          <td class="riderCell"><span class="riderName">Korntawat SAMRAN</span></td>
          <td><img src="../../../../flags/THA.PNG" alt="THA"></td>
          <td class="horseCell"><span class="horseName">B.Grimm Carouzo Bois Marotin</span></td>
          <td>474,0</td>
          <td>65,83</td>
          <td>34,2</td>
          <td>52.</td>
          <td>1,2</td>
          <td>09:53</td>
          <td>35,4</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>103</td>
          <td class="riderCell"><span class="riderName">Sophia HILL</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Humble Glory</span></td>
          <td>449,5</td>
          <td>62,43</td>
          <td>37,6</td>
          <td>68.</td>
          <td>0,0</td>
          <td class="good">09:45</td>
          <td>37,6</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>172</td>
          <td class="riderCell"><span class="riderName">Robin GODEL</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Grandeur de Lully CH</span></td>
          <td>503,0</td>
          <td>69,86</td>
          <td>30,1</td>
          <td>22.</td>
          <td>10,4</td>
          <td>10:16</td>
          <td>40,5</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>136</td>
          <td class="riderCell"><span class="riderName">Gemma STEVENS</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Flash Cooley</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td></td>
          <td></td>
          <td>EL XC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>151</td>
          <td class="riderCell"><span class="riderName">Francesco AONDIO BERTERO</span></td>
          <td><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">It's Athene</span></td>
          <td>423,5</td>
          <td>58,82</td>
          <td>41,2</td>
          <td>80.</td>
          <td></td>
          <td></td>
          <td>RT XC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>114</td>
          <td class="riderCell"><span class="riderName">Senne VERVAECKE</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Google van Alsingen</span></td>
          <td>469,5</td>
          <td>65,21</td>
          <td>34,8</td>
          <td>54.</td>
          <td></td>
          <td></td>
          <td>EL XC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>126</td>
          <td class="riderCell"><span class="riderName">Sanna SILTAKORPI</span></td>
          <td><img src="../../../../flags/FIN.PNG" alt="FIN"></td>
          <td class="horseCell"><span class="horseName">Bofey Click</span></td>
          <td>442,0</td>
          <td>61,39</td>
          <td>38,6</td>
          <td>71.</td>
          <td></td>
          <td></td>
          <td>WDbXC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1408_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  2:08PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>15:19:00</td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:35:00</td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td>0,8</td>
          <td>09:52</td>
          <td>23,6</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>5.</td>
          <td>2,0</td>
          <td>09:55</td>
          <td>28,6</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>128</td>
          <td class="riderCell"><span class="riderName">Gaspard MAKSUD</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Zaragoza</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>1,6</td>
          <td>09:54</td>
          <td>30,9</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>8.</strong></td>
          <td>162</td>
          <td class="riderCell"><span class="riderName">Jillian GIESSEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Seattle Park</span></td>
          <td>476,0</td>
          <td>66,11</td>
          <td>33,9</td>
          <td>50.</td>
          <td>0,8</td>
          <td>09:52</td>
          <td>34,7</td>
          <td>8.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>11.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td>13,6</td>
          <td>10:24</td>
          <td>35,6</td>
          <td>11.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>24.</strong></td>
          <td>113</td>
          <td class="riderCell"><span class="riderName">Karin DONCKERS</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Leipheimer van't Verahof</span></td>
          <td>492,0</td>
          <td>68,33</td>
          <td>31,7</td>
          <td>34.</td>
          <td>18,8</td>
          <td>10:37</td>
          <td>50,5</td>
          <td>24.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>173</td>
          <td class="riderCell"><span class="riderName">M&eacute;lody JOHNER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Erin</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>33.</td>
          <td>0,0</td>
          <td class="good">09:44</td>
          <td>31,5</td>
          <td>4.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>22.</strong></td>
          <td>118</td>
          <td class="riderCell"><span class="riderName">Jessica PHOENIX</span></td>
          <td><img src="../../../../flags/CAN.PNG" alt="CAN"></td>
          <td class="horseCell"><span class="horseName">Fluorescent Adolescent</span></td>
          <td>467,5</td>
          <td>64,93</td>
          <td>35,1</td>
          <td>56.</td>
          <td>12,0</td>
          <td>10:20</td>
          <td>47,1</td>
          <td>22.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>101</td>
          <td class="riderCell"><span class="riderName">Oliver BARRETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Sandhills Briar</span></td>
          <td>494,5</td>
          <td>68,68</td>
          <td>31,3</td>
          <td>29.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>174</td>
          <td class="riderCell"><span class="riderName">Nadja MINDER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Top Job's Jalisco</span></td>
          <td>385,5</td>
          <td>53,54</td>
          <td>46,5</td>
          <td>87.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1506_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  3:06PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>15:19:00</td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:35:00</td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td>0,8</td>
          <td>09:52</td>
          <td>23,6</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:07:00</td>
          <td>131</td>
          <td class="riderCell"><span class="riderName">Nicolas TOUZAINT</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Diabolo Menthe</span></td>
          <td>527,5</td>
          <td>73,26</td>
          <td>26,7</td>
          <td>6.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>5.</td>
          <td>2,0</td>
          <td>09:55</td>
          <td>28,6</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>141</td>
          <td class="riderCell"><span class="riderName">Christoph WAHLER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">D'Accord FRH</span></td>
          <td>508,5</td>
          <td>70,63</td>
          <td>29,4</td>
          <td>19.</td>
          <td>0,0</td>
          <td>09:41</td>
          <td>29,4</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>130</td>
          <td class="riderCell"><span class="riderName">Astier NICOLAS</span></td>
          <td><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Alertamalib'Or</span></td>
          <td>502,0</td>
          <td>69,72</td>
          <td>30,3</td>
          <td>23.</td>
          <td>0,8</td>
          <td>09:52</td>
          <td>31,1</td>
          <td>6.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>8.</strong></td>
          <td>104</td>
          <td class="riderCell"><span class="riderName">Andrew HOY</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Vassily de Lassos</span></td>
          <td>526,0</td>
          <td>73,06</td>
          <td>26,9</td>
          <td>7.</td>
          <td>4,8</td>
          <td>10:02</td>
          <td>31,7</td>
          <td>8.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>14.</strong></td>
          <td>188</td>
          <td class="riderCell"><span class="riderName">Tamra SMITH</span></td>
          <td><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Lillet 3</span></td>
          <td>525,5</td>
          <td>72,99</td>
          <td>27,0</td>
          <td>8.</td>
          <td>8,0</td>
          <td>10:10</td>
          <td>35,0</td>
          <td>14.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>30.</strong></td>
          <td>109</td>
          <td class="riderCell"><span class="riderName">Lea SIEGL</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUT.PNG" alt="AUT"></td>
          <td class="horseCell"><span class="horseName">Watermill Giorgio RS</span></td>
          <td>510,0</td>
          <td>70,83</td>
          <td>29,2</td>
          <td>15.</td>
          <td>18,4</td>
          <td>10:36</td>
          <td>47,6</td>
          <td>30.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>158</td>
          <td class="riderCell"><span class="riderName">Toshiyuki TANAKA</span></td>
          <td><sup>*</sup><img src="../../../../flags/JPN.PNG" alt="JPN"></td>
          <td class="horseCell"><span class="horseName">Jefferson JRA</span></td>
          <td>494,0</td>
          <td>68,61</td>
          <td>31,4</td>
          <td>30.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>145</td>
          <td class="riderCell"><span class="riderName">Fouaad MIRZA</span></td>
          <td><img src="../../../../flags/IND.PNG" alt="IND"></td>
          <td class="horseCell"><span class="horseName">Mokatoo</span></td>
          <td>435,0</td>
          <td>60,42</td>
          <td>39,6</td>
          <td>77.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1600_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  4:00PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td>0,0</td>
          <td>09:45</td>
          <td>23,0</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td>0,0</td>
          <td>09:44</td>
          <td>23,4</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td>0,8</td>
          <td>09:52</td>
          <td>23,6</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>5.</td>
          <td>2,0</td>
          <td>09:55</td>
          <td>28,6</td>
          <td>4.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>141</td>
          <td class="riderCell"><span class="riderName">Christoph WAHLER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">D'Accord FRH</span></td>
          <td>508,5</td>
          <td>70,63</td>
          <td>29,4</td>
          <td>19.</td>
          <td>0,0</td>
          <td>09:41</td>
          <td>29,4</td>
          <td>5.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>184</td>
          <td class="riderCell"><span class="riderName">William COLEMAN</span></td>
          <td><sup>*</sup><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Diabolo</span></td>
          <td>504,0</td>
          <td>70,00</td>
          <td>30,0</td>
          <td>21.</td>
          <td>0,0</td>
          <td>09:48</td>
          <td>30,0</td>
          <td>6.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>128</td>
          <td class="riderCell"><span class="riderName">Gaspard MAKSUD</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Zaragoza</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>1,6</td>
          <td>09:54</td>
          <td>30,9</td>
          <td>7.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>15.</strong></td>
          <td>175</td>
          <td class="riderCell"><span class="riderName">Felix VOGG</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Frieda</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>5,2</td>
          <td>10:03</td>
          <td>34,5</td>
          <td>15.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>38.</strong></td>
          <td>131</td>
          <td class="riderCell"><span class="riderName">Nicolas TOUZAINT</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Diabolo Menthe</span></td>
          <td>527,5</td>
          <td>73,26</td>
          <td>26,7</td>
          <td>6.</td>
          <td>21,4</td>
          <td>10:16</td>
          <td>48,1</td>
          <td>38.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>151</td>
          <td class="riderCell"><span class="riderName">Francesco AONDIO BERTERO</span></td>
          <td><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">It's Athene</span></td>
          <td>423,5</td>
          <td>58,82</td>
          <td>41,2</td>
          <td>80.</td>
          <td></td><td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>154</td>
          <td class="riderCell"><span class="riderName">Paolo TORLONIA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Zinny</span></td>
          <td>422,5</td>
          <td>58,68</td>
          <td>41,3</td>
          <td>81.</td>
          <td></td><td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1659_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  4:59PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td>0,0</td>
          <td>09:45</td>
          <td>23,0</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td>0,0</td>
          <td>09:44</td>
          <td>23,4</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td>0,8</td>
          <td>09:52</td>
          <td>23,6</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>5.</td>
          <td>2,0</td>
          <td>09:55</td>
          <td>28,6</td>
          <td>4.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>141</td>
          <td class="riderCell"><span class="riderName">Christoph WAHLER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">D'Accord FRH</span></td>
          <td>508,5</td>
          <td>70,63</td>
          <td>29,4</td>
          <td>19.</td>
          <td>0,0</td>
          <td>09:41</td>
          <td>29,4</td>
          <td>5.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>184</td>
          <td class="riderCell"><span class="riderName">William COLEMAN</span></td>
          <td><sup>*</sup><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Diabolo</span></td>
          <td>504,0</td>
          <td>70,00</td>
          <td>30,0</td>
          <td>21.</td>
          <td>0,0</td>
          <td>09:48</td>
          <td>30,0</td>
          <td>6.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>128</td>
          <td class="riderCell"><span class="riderName">Gaspard MAKSUD</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Zaragoza</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>1,6</td>
          <td>09:54</td>
          <td>30,9</td>
          <td>7.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>15.</strong></td>
          <td>175</td>
          <td class="riderCell"><span class="riderName">Felix VOGG</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Frieda</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>5,2</td>
          <td>10:03</td>
          <td>34,5</td>
          <td>15.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>38.</strong></td>
          <td>131</td>
          <td class="riderCell"><span class="riderName">Nicolas TOUZAINT</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Diabolo Menthe</span></td>
          <td>527,5</td>
          <td>73,26</td>
          <td>26,7</td>
          <td>6.</td>
          <td>21,4</td>
          <td>10:16</td>
          <td>48,1</td>
          <td>38.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>151</td>
          <td class="riderCell"><span class="riderName">Francesco AONDIO BERTERO</span></td>
          <td><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">It's Athene</span></td>
          <td>423,5</td>
          <td>58,82</td>
          <td>41,2</td>
          <td>80.</td>
          <td></td><td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>154</td>
          <td class="riderCell"><span class="riderName">Paolo TORLONIA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Zinny</span></td>
          <td>422,5</td>
          <td>58,68</td>
          <td>41,3</td>
          <td>81.</td>
          <td></td><td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1933_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  7:33PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td>0,0</td>
          <td>09:45</td>
          <td>23,0</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td>0,0</td>
          <td>09:44</td>
          <td>23,4</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td>0,8</td>
          <td>09:52</td>
          <td>23,6</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>128</td>
          <td class="riderCell"><span class="riderName">Gaspard MAKSUD</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Zaragoza</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>1,6</td>
          <td>09:54</td>
          <td>30,9</td>
          <td>7.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>15.</strong></td>
          <td>175</td>
          <td class="riderCell"><span class="riderName">Felix VOGG</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Frieda</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>5,2</td>
          <td>10:03</td>
          <td>34,5</td>
          <td>15.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>38.</strong></td>
          <td>131</td>
          <td class="riderCell"><span class="riderName">Nicolas TOUZAINT</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Diabolo Menthe</span></td>
          <td>527,5</td>
          <td>73,26</td>
          <td>26,7</td>
          <td>6.</td>
          <td>21,4</td>
          <td>10:16</td>
          <td>48,1</td>
          <td>38.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>157</td>
          <td class="riderCell"><span class="riderName">Kento NAGURA</span></td>
          <td><sup>*</sup><img src="../../../../flags/JPN.PNG" alt="JPN"></td>
          <td class="horseCell"><span class="horseName">Vinci de la Vigne JRA</span></td>
          <td>480,0</td>
          <td>66,67</td>
          <td>33,3</td>
          <td>45.</td>
          <td>65,4</td>
          <td>11:16</td>
          <td>98,7</td>
          <td>62.</td>
          <td></td><td></td>
          <td class="borderCell">WDbSJ</td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>156</td>
          <td class="riderCell"><span class="riderName">Ryuzo KITAJIMA</span></td>
          <td><sup>*</sup><img src="../../../../flags/JPN.PNG" alt="JPN"></td>
          <td class="horseCell"><span class="horseName">Feroza Nieuwmoed</span></td>
          <td>465,5</td>
          <td>64,65</td>
          <td>35,4</td>
          <td>62.</td>
          <td>78,8</td>
          <td>11:27</td>
          <td>114,2</td>
          <td>63.</td>
          <td></td><td></td>
          <td class="borderCell">WDbSJ</td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>151</td>
          <td class="riderCell"><span class="riderName">Francesco AONDIO BERTERO</span></td>
          <td><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">It's Athene</span></td>
          <td>423,5</td>
          <td>58,82</td>
          <td>41,2</td>
          <td>80.</td>
          <td></td><td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>154</td>
          <td class="riderCell"><span class="riderName">Paolo TORLONIA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Zinny</span></td>
          <td>422,5</td>
          <td>58,68</td>
          <td>41,3</td>
          <td>81.</td>
          <td></td><td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1354_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  1:54PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>13:55:00</td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>5.</td>
          <td>2,0</td>
          <td>09:55</td>
          <td>28,6</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>128</td>
          <td class="riderCell"><span class="riderName">Gaspard MAKSUD</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Zaragoza</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>16.</td>
          <td>1,6</td>
          <td>09:54</td>
          <td>30,9</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>173</td>
          <td class="riderCell"><span class="riderName">M&eacute;lody JOHNER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Erin</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>33.</td>
          <td>0,0</td>
          <td class="good">09:44</td>
          <td>31,5</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>13:51:00</td>
          <td>113</td>
          <td class="riderCell"><span class="riderName">Karin DONCKERS</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Leipheimer van't Verahof</span></td>
          <td>492,0</td>
          <td>68,33</td>
          <td>31,7</td>
          <td>34.</td>
          <td>0,0</td>
          <td></td>
          <td>31,7</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>169</td>
          <td class="riderCell"><span class="riderName">Monica SPENCER</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Artist</span></td>
          <td>512,0</td>
          <td>71,11</td>
          <td>28,9</td>
          <td>13.</td>
          <td>4,8</td>
          <td>10:02</td>
          <td>33,7</td>
          <td>6.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>9.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td>13,6</td>
          <td>10:24</td>
          <td>35,6</td>
          <td>9.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>20.</strong></td>
          <td>118</td>
          <td class="riderCell"><span class="riderName">Jessica PHOENIX</span></td>
          <td><img src="../../../../flags/CAN.PNG" alt="CAN"></td>
          <td class="horseCell"><span class="horseName">Fluorescent Adolescent</span></td>
          <td>467,5</td>
          <td>64,93</td>
          <td>35,1</td>
          <td>56.</td>
          <td>12,0</td>
          <td>10:20</td>
          <td>47,1</td>
          <td>20.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>13:47:00</td>
          <td>162</td>
          <td class="riderCell"><span class="riderName">Jillian GIESSEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Seattle Park</span></td>
          <td>476,0</td>
          <td>66,11</td>
          <td>33,9</td>
          <td>50.</td>
          <td>18,0</td>
          <td></td>
          <td>51,9</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>36.</strong></td>
          <td>124</td>
          <td class="riderCell"><span class="riderName">Esteban BENITEZ VALLE</span></td>
          <td><img src="../../../../flags/ESP.PNG" alt="ESP"></td>
          <td class="horseCell"><span class="horseName">Utrera AA 35 1</span></td>
          <td>480,5</td>
          <td>66,74</td>
          <td>33,3</td>
          <td>46.</td>
          <td>50,0</td>
          <td>11:05</td>
          <td>83,3</td>
          <td>36.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>101</td>
          <td class="riderCell"><span class="riderName">Oliver BARRETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Sandhills Briar</span></td>
          <td>494,5</td>
          <td>68,68</td>
          <td>31,3</td>
          <td>29.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>174</td>
          <td class="riderCell"><span class="riderName">Nadja MINDER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Top Job's Jalisco</span></td>
          <td>385,5</td>
          <td>53,54</td>
          <td>46,5</td>
          <td>87.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>137</td>
          <td class="riderCell"><span class="riderName">Malin HANSEN-HOTOPP</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Carlitos Quidditch K</span></td>
          <td>514,0</td>
          <td>71,39</td>
          <td>28,6</td>
          <td>11.</td>
          <td>3,2</td>
          <td>09:58</td>
          <td>31,8</td>
          <td>4.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>147</td>
          <td class="riderCell"><span class="riderName">Aoife CLARK</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Full Monty de Lacense</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>32.</td>
          <td>1,2</td>
          <td>09:53</td>
          <td>32,7</td>
          <td>5.</td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1304_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  1:04PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>13:39:00</td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>5.</td>
          <td>2,0</td>
          <td>09:55</td>
          <td>28,6</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>12:59:00</td>
          <td>169</td>
          <td class="riderCell"><span class="riderName">Monica SPENCER</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Artist</span></td>
          <td>512,0</td>
          <td>71,11</td>
          <td>28,9</td>
          <td>13.</td>
          <td>0,0</td>
          <td></td>
          <td>28,9</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>173</td>
          <td class="riderCell"><span class="riderName">M&eacute;lody JOHNER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Erin</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>33.</td>
          <td>0,0</td>
          <td class="good">09:44</td>
          <td>31,5</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>137</td>
          <td class="riderCell"><span class="riderName">Malin HANSEN-HOTOPP</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Carlitos Quidditch K</span></td>
          <td>514,0</td>
          <td>71,39</td>
          <td>28,6</td>
          <td>11.</td>
          <td>3,2</td>
          <td>09:58</td>
          <td>31,8</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>147</td>
          <td class="riderCell"><span class="riderName">Aoife CLARK</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Full Monty de Lacense</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>32.</td>
          <td>1,2</td>
          <td>09:53</td>
          <td>32,7</td>
          <td>4.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>127</td>
          <td class="riderCell"><span class="riderName">Alexis GOURY</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Je'Vall</span></td>
          <td>515,0</td>
          <td>71,53</td>
          <td>28,5</td>
          <td>10.</td>
          <td>6,4</td>
          <td>10:06</td>
          <td>34,9</td>
          <td>5.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>14.</strong></td>
          <td>118</td>
          <td class="riderCell"><span class="riderName">Jessica PHOENIX</span></td>
          <td><img src="../../../../flags/CAN.PNG" alt="CAN"></td>
          <td class="horseCell"><span class="horseName">Fluorescent Adolescent</span></td>
          <td>467,5</td>
          <td>64,93</td>
          <td>35,1</td>
          <td>56.</td>
          <td>12,0</td>
          <td>10:20</td>
          <td>47,1</td>
          <td>14.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>31.</strong></td>
          <td>124</td>
          <td class="riderCell"><span class="riderName">Esteban BENITEZ VALLE</span></td>
          <td><img src="../../../../flags/ESP.PNG" alt="ESP"></td>
          <td class="horseCell"><span class="horseName">Utrera AA 35 1</span></td>
          <td>480,5</td>
          <td>66,74</td>
          <td>33,3</td>
          <td>46.</td>
          <td>59,0</td>
          <td>11:05</td>
          <td>92,3</td>
          <td>31.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>123</td>
          <td class="riderCell"><span class="riderName">Peter T. FLARUP</span></td>
          <td><img src="../../../../flags/DEN.PNG" alt="DEN"></td>
          <td class="horseCell"><span class="horseName">H.Carald Z</span></td>
          <td>467,0</td>
          <td>64,86</td>
          <td>35,1</td>
          <td>57.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>170</td>
          <td class="riderCell"><span class="riderName">Joanna PAWLAK</span></td>
          <td><img src="../../../../flags/POL.PNG" alt="POL"></td>
          <td class="horseCell"><span class="horseName">Armin de Monsieur</span></td>
          <td>452,0</td>
          <td>62,78</td>
          <td>37,2</td>
          <td>65.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>154</td>
          <td class="riderCell"><span class="riderName">Paolo TORLONIA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Zinny</span></td>
          <td>422,5</td>
          <td>58,68</td>
          <td>41,3</td>
          <td>81.</td>
          <td></td><td></td>
          <td>RT XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>181</td>
          <td class="riderCell"><span class="riderName">Weerapat PITAKANONDA</span></td>
          <td><img src="../../../../flags/THA.PNG" alt="THA"></td>
          <td class="horseCell"><span class="horseName">B.Grimm Chateau de Versailles M2S</span></td>
          <td>422,0</td>
          <td>58,61</td>
          <td>41,4</td>
          <td>82.</td>
          <td></td><td></td>
          <td>EL XC</td>
          <td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1203_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026 12:03PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>13:39:00</td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>173</td>
          <td class="riderCell"><span class="riderName">M&eacute;lody JOHNER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Erin</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>33.</td>
          <td>0,0</td>
          <td class="good">09:44</td>
          <td>31,5</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>137</td>
          <td class="riderCell"><span class="riderName">Malin HANSEN-HOTOPP</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Carlitos Quidditch K</span></td>
          <td>514,0</td>
          <td>71,39</td>
          <td>28,6</td>
          <td>11.</td>
          <td>3,2</td>
          <td>09:58</td>
          <td>31,8</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>147</td>
          <td class="riderCell"><span class="riderName">Aoife CLARK</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Full Monty de Lacense</span></td>
          <td>493,5</td>
          <td>68,54</td>
          <td>31,5</td>
          <td>32.</td>
          <td>1,2</td>
          <td>09:53</td>
          <td>32,7</td>
          <td>3.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>11:59:00</td>
          <td>124</td>
          <td class="riderCell"><span class="riderName">Esteban BENITEZ VALLE</span></td>
          <td><img src="../../../../flags/ESP.PNG" alt="ESP"></td>
          <td class="horseCell"><span class="horseName">Utrera AA 35 1</span></td>
          <td>480,5</td>
          <td>66,74</td>
          <td>33,3</td>
          <td>46.</td>
          <td>0,0</td>
          <td></td>
          <td>33,3</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>127</td>
          <td class="riderCell"><span class="riderName">Alexis GOURY</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Je'Vall</span></td>
          <td>515,0</td>
          <td>71,53</td>
          <td>28,5</td>
          <td>10.</td>
          <td>6,4</td>
          <td>10:06</td>
          <td>34,9</td>
          <td>4.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>5.</td>
          <td>11,0</td>
          <td>09:55</td>
          <td>37,6</td>
          <td>7.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>187</td>
          <td class="riderCell"><span class="riderName">Caroline PAMUKCU</span></td>
          <td><sup>*</sup><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">HSH Blake</span></td>
          <td>487,5</td>
          <td>67,71</td>
          <td>32,3</td>
          <td>36.</td>
          <td></td>
          <td></td>
          <td>EL XC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>105</td>
          <td class="riderCell"><span class="riderName">Sam WOODS</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">SS Eight Count</span></td>
          <td>451,0</td>
          <td>62,64</td>
          <td>37,4</td>
          <td>66.</td>
          <td></td>
          <td></td>
          <td>EL XC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_0854_SATURDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 15 2026  8:54AM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>13:39:00</td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>13:55:00</td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:19:00</td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:35:00</td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>126</td>
          <td class="riderCell"><span class="riderName">Sanna SILTAKORPI</span></td>
          <td><img src="../../../../flags/FIN.PNG" alt="FIN"></td>
          <td class="horseCell"><span class="horseName">Bofey Click</span></td>
          <td>442,0</td>
          <td>61,39</td>
          <td>38,6</td>
          <td>71.</td>
          <td></td>
          <td></td>
          <td>WDbXC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td>09:43:00</td>
          <td>153</td>
          <td class="riderCell"><span class="riderName">Vittoria PANIZZON</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">DHI Jackpot</span></td>
          <td>483,0</td>
          <td>67,08</td>
          <td>32,9</td>
          <td>42.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1922_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026  7:22PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time<br>Cross/ <br>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>13:39:00</td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>13:55:00</td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:19:00</td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:35:00</td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td>09:43:00</td>
          <td>153</td>
          <td class="riderCell"><span class="riderName">Vittoria PANIZZON</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">DHI Jackpot</span></td>
          <td>483,0</td>
          <td>67,08</td>
          <td>32,9</td>
          <td>42.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1723_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 5:23PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>133</td>
          <td class="riderCell"><span class="riderName">Laura COLLETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">London 52</span></td>
          <td>556,0</td>
          <td>77,22</td>
          <td>22,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>554,5</td>
          <td>77,01</td>
          <td>23,0</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>132</td>
          <td class="riderCell"><span class="riderName">Rosalind CANTER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Lordships Graffalo</span></td>
          <td>551,5</td>
          <td>76,60</td>
          <td>23,4</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1611_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 4:11PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>175</td>
          <td class="riderCell"><span class="riderName">Felix VOGG</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Frieda</span></td>
          <td>7,5</td>
          <td>75,00</td>
          <td>25,0</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>4.</strong></td>
          <td>131</td>
          <td class="riderCell"><span class="riderName">Nicolas TOUZAINT</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Diabolo Menthe</span></td>
          <td>527,5</td>
          <td>73,26</td>
          <td>26,7</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>104</td>
          <td class="riderCell"><span class="riderName">Andrew HOY</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Vassily de Lassos</span></td>
          <td>526,0</td>
          <td>73,06</td>
          <td>26,9</td>
          <td>5.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>24.</strong></td>
          <td>115</td>
          <td class="riderCell"><span class="riderName">Marcio CARVALHO JORGE</span></td>
          <td><sup>*</sup><img src="../../../../flags/BRA.PNG" alt="BRA"></td>
          <td class="horseCell"><span class="horseName">Royal Encounter</span></td>
          <td>495,5</td>
          <td>68,82</td>
          <td>31,2</td>
          <td>24.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>37.</strong></td>
          <td>149</td>
          <td class="riderCell"><span class="riderName">Padraig MCCARTHY</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">MGH Zabaione</span></td>
          <td>484,0</td>
          <td>67,22</td>
          <td>32,8</td>
          <td>37.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1615_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 4:15PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>4.</strong></td>
          <td>131</td>
          <td class="riderCell"><span class="riderName">Nicolas TOUZAINT</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Diabolo Menthe</span></td>
          <td>527,5</td>
          <td>73,26</td>
          <td>26,7</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>104</td>
          <td class="riderCell"><span class="riderName">Andrew HOY</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Vassily de Lassos</span></td>
          <td>526,0</td>
          <td>73,06</td>
          <td>26,9</td>
          <td>5.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>14.</strong></td>
          <td>175</td>
          <td class="riderCell"><span class="riderName">Felix VOGG</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Frieda</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>14.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1521_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 3:21PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>188</td>
          <td class="riderCell"><span class="riderName">Tamra SMITH</span></td>
          <td><img src="../../../../flags/USA.PNG" alt="USA"></td>
          <td class="horseCell"><span class="horseName">Lillet 3</span></td>
          <td>525,5</td>
          <td>72,99</td>
          <td>27,0</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>158</td>
          <td class="riderCell"><span class="riderName">Toshiyuki TANAKA</span></td>
          <td><sup>*</sup><img src="../../../../flags/JPN.PNG" alt="JPN"></td>
          <td class="horseCell"><span class="horseName">Jefferson JRA</span></td>
          <td>183,5</td>
          <td>70,58</td>
          <td>29,4</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1203_FRIDAY_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 14 2026 12:03PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>139</td>
          <td class="riderCell"><span class="riderName">Julia KRAJEWSKI</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Uelzener's Nickel</span></td>
          <td>561,5</td>
          <td>77,99</td>
          <td>22,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>16.</strong></td>
          <td>101</td>
          <td class="riderCell"><span class="riderName">Oliver BARRETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUS.PNG" alt="AUS"></td>
          <td class="horseCell"><span class="horseName">Sandhills Briar</span></td>
          <td>494,5</td>
          <td>68,68</td>
          <td>31,3</td>
          <td>16.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>27.</strong></td>
          <td>157</td>
          <td class="riderCell"><span class="riderName">Kento NAGURA</span></td>
          <td><sup>*</sup><img src="../../../../flags/JPN.PNG" alt="JPN"></td>
          <td class="horseCell"><span class="horseName">Vinci de la Vigne JRA</span></td>
          <td>480,0</td>
          <td>66,67</td>
          <td>33,3</td>
          <td>27.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>59.</strong></td>
          <td>117</td>
          <td class="riderCell"><span class="riderName">Carlos PARRO</span></td>
          <td><sup>*</sup><img src="../../../../flags/BRA.PNG" alt="BRA"></td>
          <td class="horseCell"><span class="horseName">Safira</span></td>
          <td>399,5</td>
          <td>55,49</td>
          <td>44,5</td>
          <td>59.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_1720_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 5:20PM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>135</td>
          <td class="riderCell"><span class="riderName">Tom MCEWEN</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">JL Dublin</span></td>
          <td>528,5</td>
          <td>73,40</td>
          <td>26,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>35.</strong></td>
          <td>125</td>
          <td class="riderCell"><span class="riderName">Axel LINDBERG</span></td>
          <td><img src="../../../../flags/FIN.PNG" alt="FIN"></td>
          <td class="horseCell"><span class="horseName">Quelle Bonne</span></td>
          <td>439,5</td>
          <td>61,04</td>
          <td>39,0</td>
          <td>35.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>40.</strong></td>
          <td>154</td>
          <td class="riderCell"><span class="riderName">Paolo TORLONIA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Zinny</span></td>
          <td>422,5</td>
          <td>58,68</td>
          <td>41,3</td>
          <td>40.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>43.</strong></td>
          <td>144</td>
          <td class="riderCell"><span class="riderName">Ashish LIMAYE</span></td>
          <td><img src="../../../../flags/IND.PNG" alt="IND"></td>
          <td class="horseCell"><span class="horseName">D'Avril du Pinier</span></td>
          <td>399,0</td>
          <td>55,42</td>
          <td>44,6</td>
          <td>43.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


AACHEN_LIVE_MIDMORNING_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 13 2026 11:49AM</p>
    <table>
      <thead>
        <tr>
          <th>Start TimeDressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank afterDressage</th>
          <th>Cross-Country</th><th>Rank afterCross-Country</th>
          <th>Jumping</th><th>FinalScore</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>165</td>
          <td class="riderCell"><span class="riderName">Clarke JOHNSTONE</span></td>
          <td><sup>*</sup><img src="../../../../flags/NZL.PNG" alt="NZL"></td>
          <td class="horseCell"><span class="horseName">Rocket Man</span></td>
          <td>513,5</td>
          <td>71,32</td>
          <td>28,7</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>136</td>
          <td class="riderCell"><span class="riderName">Gemma STEVENS</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Flash Cooley</span></td>
          <td>509,0</td>
          <td>70,69</td>
          <td>29,3</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>172</td>
          <td class="riderCell"><span class="riderName">Robin GODEL</span></td>
          <td><sup>*</sup><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">Grandeur de Lully CH</span></td>
          <td>503,0</td>
          <td>69,86</td>
          <td>30,1</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>163</td>
          <td class="riderCell"><span class="riderName">Florinoor HOOGLAND</span></td>
          <td><sup>*</sup><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Hontoni</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


HAMBACH_DRESSAGE_HTML = """
<html>
  <head><title>LeaderBoard · Hambach/Ufr. · CCI 3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 20 2026 6:59PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>104</td>
          <td class="riderCell"><span class="riderName">Anna SIEMER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Grazia K</span></td>
          <td>318,5</td>
          <td>69,24</td>
          <td>30,8</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>38</td>
          <td class="riderCell"><span class="riderName">Hanne HENNING</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Sicherlich Wilde Hilde</span></td>
          <td>314,5</td>
          <td>68,37</td>
          <td>31,6</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

HAMBACH_ELIOPE_HTML = """
<html>
  <head><title>LeaderBoard · Hambach/Ufr. · CCI 3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 20 2026 6:59PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>103</td>
          <td class="riderCell"><span class="riderName">Anna SIEMER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Eliope</span></td>
          <td>313,5</td>
          <td>68,15</td>
          <td>31,9</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>12</td>
          <td class="riderCell"><span class="riderName">Lea PONCELET</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Elixir des Cabanes</span></td>
          <td></td>
          <td></td>
          <td>EL XC</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

HAMBACH_CCI3_AFTER_XC_716PM_HTML = """
<html>
  <head><title>LeaderBoard · Hambach/Ufr. · CCI 3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 22 2026  7:16PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>110</td>
          <td class="riderCell"><span class="riderName">Sabrina MERTENS</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">La Duma</span></td>
          <td>330,5</td>
          <td>71,85</td>
          <td>28,2</td>
          <td>3.</td>
          <td>0,0</td>
          <td>06:05</td>
          <td>28,2</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>121</td>
          <td class="riderCell"><span class="riderName">Vanessa B&Ouml;LTING</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Ready To Go Nrw</span></td>
          <td>320,0</td>
          <td>69,57</td>
          <td>30,4</td>
          <td>6.</td>
          <td>0,0</td>
          <td>05:59</td>
          <td>30,4</td>
          <td>2.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>25.</strong></td>
          <td>57</td>
          <td class="riderCell"><span class="riderName">Maj-Jonna ZIEBELL</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Diamar 2</span></td>
          <td>327,5</td>
          <td>71,20</td>
          <td>28,8</td>
          <td>4.</td>
          <td>23,8</td>
          <td>06:42</td>
          <td>52,6</td>
          <td>25.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>30.</strong></td>
          <td>105</td>
          <td class="riderCell"><span class="riderName">Anna SIEMER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Kiss Me</span></td>
          <td>346,0</td>
          <td>75,22</td>
          <td>24,8</td>
          <td>1.</td>
          <td>42,8</td>
          <td>07:07</td>
          <td>67,6</td>
          <td>30.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>39.</strong></td>
          <td>125</td>
          <td class="riderCell"><span class="riderName">Karin DONCKERS</span></td>
          <td><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Shakira</span></td>
          <td>341,5</td>
          <td>74,24</td>
          <td>25,8</td>
          <td>2.</td>
          <td>106,0</td>
          <td>08:05</td>
          <td>131,8</td>
          <td>39.</td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

HAMBACH_INTRO_START_LIST_HTML = """
<html>
  <head><title>LeaderBoard · Hambach/Ufr. · CCI 1*-Intro</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 20 2026 5:53PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>17:00:00</td>
          <td>49</td>
          <td class="riderCell"><span class="riderName">Sophie GRIEGER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Claire Clementine</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_START_LIST_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CCI3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 25 2026  5:40PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td></td>
          <td>114</td>
          <td class="riderCell"><span class="riderName">Kai R&Uuml;DER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Nash</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_JUNIOR_DRESSAGE_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-J-CCI2*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026  8:46AM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td></td>
          <td>205</td>
          <td class="riderCell"><span class="riderName">Eline DE RIDDER</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Mandorior</span></td>
          <td>144,5</td>
          <td>68,81</td>
          <td>31,2</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>1.</strong></td>
          <td>258</td>
          <td class="riderCell"><span class="riderName">Tova MADER</span></td>
          <td><sup>*</sup><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">TJA Morning Star</span></td>
          <td>420,0</td>
          <td>66,67</td>
          <td>33,3</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>08:43:00</td>
          <td>226</td>
          <td class="riderCell"><span class="riderName">Arabella HENDERSON</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Ex Cavalier's Law</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_JUNIOR_DRESSAGE_MID_SESSION_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-J-CCI2*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026 10:01AM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>233</td>
          <td class="riderCell"><span class="riderName">Milla STAADE</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Christ William</span></td>
          <td>447,0</td>
          <td>70,95</td>
          <td>29,1</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td><strong>2.</strong></td>
          <td>226</td>
          <td class="riderCell"><span class="riderName">Arabella HENDERSON</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Ex Cavalier's Law</span></td>
          <td>440,5</td>
          <td>69,92</td>
          <td>30,1</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>205</td>
          <td class="riderCell"><span class="riderName">Eline DE RIDDER</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Mandorior</span></td>
          <td>284,0</td>
          <td>67,62</td>
          <td>32,4</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent1">
          <td>10:03:00</td>
          <td>239</td>
          <td class="riderCell"><span class="riderName">Niamh VERKADE</span></td>
          <td><img src="../../../../flags/NED.PNG" alt="NED"></td>
          <td class="horseCell"><span class="horseName">Duniro</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_JUNIOR_DRESSAGE_LATER_SESSION_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-J-CCI2*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026 11:00AM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>233</td>
          <td class="riderCell"><span class="riderName">Milla STAADE</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Christ William</span></td>
          <td>447,0</td>
          <td>70,95</td>
          <td>29,1</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>226</td>
          <td class="riderCell"><span class="riderName">Arabella HENDERSON</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Ex Cavalier's Law</span></td>
          <td>440,5</td>
          <td>69,92</td>
          <td>30,1</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>235</td>
          <td class="riderCell"><span class="riderName">Jona Isabell HEINE</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Chantilly 38</span></td>
          <td>430,5</td>
          <td>68,33</td>
          <td>31,7</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>205</td>
          <td class="riderCell"><span class="riderName">Eline DE RIDDER</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Mandorior</span></td>
          <td>427,5</td>
          <td>67,86</td>
          <td>32,1</td>
          <td>7.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>11:01:30</td>
          <td>218</td>
          <td class="riderCell"><span class="riderName">Tifaniie VILLETON</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Gaiete d'Agenais</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_JUNIOR_DRESSAGE_LATE_MORNING_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-J-CCI2*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026 12:03PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>228</td>
          <td class="riderCell"><span class="riderName">Annabel RIDGWAY</span></td>
          <td><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Emerald Katie</span></td>
          <td>454,0</td>
          <td>72,06</td>
          <td>27,9</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>233</td>
          <td class="riderCell"><span class="riderName">Milla STAADE</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Christ William</span></td>
          <td>447,0</td>
          <td>70,95</td>
          <td>29,1</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>234</td>
          <td class="riderCell"><span class="riderName">Lukas Wilhelm S&Uuml;HLING</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Allnightparty</span></td>
          <td>389,0</td>
          <td>72,04</td>
          <td>28,0</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>218</td>
          <td class="riderCell"><span class="riderName">Tifaniie VILLETON</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Gaiete d'Agenais</span></td>
          <td>440,0</td>
          <td>69,84</td>
          <td>30,2</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>12:08:30</td>
          <td>251</td>
          <td class="riderCell"><span class="riderName">Camille Lasse WEISS</span></td>
          <td><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">CSF Hi Spec</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_JUNIOR_DRESSAGE_MIDDAY_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-J-CCI2*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026 12:37PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>234</td>
          <td class="riderCell"><span class="riderName">Lukas Wilhelm S&Uuml;HLING</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Allnightparty</span></td>
          <td>457,0</td>
          <td>72,54</td>
          <td>27,5</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>228</td>
          <td class="riderCell"><span class="riderName">Annabel RIDGWAY</span></td>
          <td><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Emerald Katie</span></td>
          <td>454,0</td>
          <td>72,06</td>
          <td>27,9</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>233</td>
          <td class="riderCell"><span class="riderName">Milla STAADE</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Christ William</span></td>
          <td>447,0</td>
          <td>70,95</td>
          <td>29,1</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>32.</strong></td>
          <td>251</td>
          <td class="riderCell"><span class="riderName">Camille Lasse WEISS</span></td>
          <td><img src="../../../../flags/SUI.PNG" alt="SUI"></td>
          <td class="horseCell"><span class="horseName">CSF Hi Spec</span></td>
          <td>383,5</td>
          <td>60,87</td>
          <td>39,1</td>
          <td>32.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>08:00:00</td>
          <td>257</td>
          <td class="riderCell"><span class="riderName">Elly IVGREN</span></td>
          <td><sup>*</sup><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Duvibis Mister</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_YR_DRESSAGE_OPENING_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-Y-CCI3*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026  2:04PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>321</td>
          <td class="riderCell"><span class="riderName">Jago JACKSON</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Kinda Brunette</span></td>
          <td>513,0</td>
          <td>68,40</td>
          <td>31,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>304</td>
          <td class="riderCell"><span class="riderName">Lander VAN DEN BROECK</span></td>
          <td><sup>*</sup><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Quincy VDB</span></td>
          <td>510,0</td>
          <td>68,00</td>
          <td>32,0</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>327</td>
          <td class="riderCell"><span class="riderName">Silva KELLY</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Calypso</span></td>
          <td>508,5</td>
          <td>67,80</td>
          <td>32,2</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>9.</strong></td>
          <td>334</td>
          <td class="riderCell"><span class="riderName">Amelia MCCARTHY</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Finsceal Endeavour</span></td>
          <td>396,0</td>
          <td>52,80</td>
          <td>47,2</td>
          <td>9.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>13:58:30</td>
          <td>326</td>
          <td class="riderCell"><span class="riderName">Liv Noe HARTMANN</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">La Diva</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_YR_DRESSAGE_MIDAFTERNOON_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-Y-CCI3*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026  3:01PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>319</td>
          <td class="riderCell"><span class="riderName">Jeanne BRUNEL</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Dexter Z</span></td>
          <td>518,0</td>
          <td>69,07</td>
          <td>30,9</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>326</td>
          <td class="riderCell"><span class="riderName">Liv Noe HARTMANN</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">La Diva</span></td>
          <td>514,5</td>
          <td>68,60</td>
          <td>31,4</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>321</td>
          <td class="riderCell"><span class="riderName">Jago JACKSON</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Kinda Brunette</span></td>
          <td>513,0</td>
          <td>68,40</td>
          <td>31,6</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>336</td>
          <td class="riderCell"><span class="riderName">Ciara O'CONNOR</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Ashwood Iron Lady</span></td>
          <td>504,5</td>
          <td>67,27</td>
          <td>32,7</td>
          <td>6.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>15:05:30</td>
          <td>331</td>
          <td class="riderCell"><span class="riderName">Carl VOIGT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">DSP Descansado</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_YR_DRESSAGE_LATE_AFTERNOON_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-Y-CCI3*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026  4:02PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>331</td>
          <td class="riderCell"><span class="riderName">Carl VOIGT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">DSP Descansado</span></td>
          <td>573,0</td>
          <td>76,40</td>
          <td>23,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>318</td>
          <td class="riderCell"><span class="riderName">Aline TEILLARD</span></td>
          <td><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Elixir de Sienne</span></td>
          <td>21,5</td>
          <td>71,67</td>
          <td>28,3</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>337</td>
          <td class="riderCell"><span class="riderName">Molly O'CONNOR</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Stillbrook Aoife</span></td>
          <td>523,0</td>
          <td>69,73</td>
          <td>30,3</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>319</td>
          <td class="riderCell"><span class="riderName">Jeanne BRUNEL</span></td>
          <td><sup>*</sup><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Dexter Z</span></td>
          <td>518,0</td>
          <td>69,07</td>
          <td>30,9</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>16:06:00</td>
          <td>306</td>
          <td class="riderCell"><span class="riderName">Lien DE DYCKER</span></td>
          <td><img src="../../../../flags/BEL.PNG" alt="BEL"></td>
          <td class="horseCell"><span class="horseName">Rohan van het Avenhof</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_YR_DRESSAGE_EARLY_EVENING_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-Y-CCI3*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026  5:02PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>331</td>
          <td class="riderCell"><span class="riderName">Carl VOIGT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">DSP Descansado</span></td>
          <td>573,0</td>
          <td>76,40</td>
          <td>23,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>323</td>
          <td class="riderCell"><span class="riderName">Elizabeth BARRATT</span></td>
          <td><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Ride For Thais Chaman Dumontceau</span></td>
          <td>564,0</td>
          <td>75,20</td>
          <td>24,8</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>349</td>
          <td class="riderCell"><span class="riderName">Filip STRZYZEWSKI</span></td>
          <td><img src="../../../../flags/POL.PNG" alt="POL"></td>
          <td class="horseCell"><span class="horseName">El Sovski</span></td>
          <td>541,5</td>
          <td>72,20</td>
          <td>27,8</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>4.</strong></td>
          <td>318</td>
          <td class="riderCell"><span class="riderName">Aline TEILLARD</span></td>
          <td><img src="../../../../flags/FRA.PNG" alt="FRA"></td>
          <td class="horseCell"><span class="horseName">Elixir de Sienne</span></td>
          <td>534,0</td>
          <td>71,20</td>
          <td>28,8</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>328</td>
          <td class="riderCell"><span class="riderName">Ella KRUEGER</span></td>
          <td><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Königsblauer</span></td>
          <td>531,5</td>
          <td>70,87</td>
          <td>29,1</td>
          <td>5.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>17:06:30</td>
          <td>333</td>
          <td class="riderCell"><span class="riderName">Jasper KELLY</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Agatha Raisin</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_YR_DRESSAGE_EVENING_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-Y-CCI3*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026  6:02PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>331</td>
          <td class="riderCell"><span class="riderName">Carl VOIGT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">DSP Descansado</span></td>
          <td>573,0</td>
          <td>76,40</td>
          <td>23,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>329</td>
          <td class="riderCell"><span class="riderName">Mathies R&Uuml;DER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Hjoptimus</span></td>
          <td>572,0</td>
          <td>76,27</td>
          <td>23,7</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>323</td>
          <td class="riderCell"><span class="riderName">Elizabeth BARRATT</span></td>
          <td><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Ride For Thais Chaman Dumontceau</span></td>
          <td>564,0</td>
          <td>75,20</td>
          <td>24,8</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>6.</strong></td>
          <td>339</td>
          <td class="riderCell"><span class="riderName">Eleonora FAVA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Juna R</span></td>
          <td>532,5</td>
          <td>71,00</td>
          <td>29,0</td>
          <td>6.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>9.</strong></td>
          <td>324</td>
          <td class="riderCell"><span class="riderName">Joshua LEVETT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">This Ones On You</span></td>
          <td>518,0</td>
          <td>69,07</td>
          <td>30,9</td>
          <td>9.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>333</td>
          <td class="riderCell"><span class="riderName">Jasper KELLY</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Agatha Raisin</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_YR_DRESSAGE_LATE_EVENING_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-Y-CCI3*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 27 2026  6:04PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Dressage/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>331</td>
          <td class="riderCell"><span class="riderName">Carl VOIGT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">DSP Descansado</span></td>
          <td>573,0</td>
          <td>76,40</td>
          <td>23,6</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>329</td>
          <td class="riderCell"><span class="riderName">Mathies R&Uuml;DER</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Hjoptimus</span></td>
          <td>572,0</td>
          <td>76,27</td>
          <td>23,7</td>
          <td>2.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>323</td>
          <td class="riderCell"><span class="riderName">Elizabeth BARRATT</span></td>
          <td><img src="../../../../flags/GBR.PNG" alt="GBR"></td>
          <td class="horseCell"><span class="horseName">Ride For Thais Chaman Dumontceau</span></td>
          <td>564,0</td>
          <td>75,20</td>
          <td>24,8</td>
          <td>3.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>32.</strong></td>
          <td>335</td>
          <td class="riderCell"><span class="riderName">Anna NANGLE</span></td>
          <td><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Stroke Of Genius</span></td>
          <td>461,5</td>
          <td>61,53</td>
          <td>38,5</td>
          <td>32.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>333</td>
          <td class="riderCell"><span class="riderName">Jasper KELLY</span></td>
          <td><sup>*</sup><img src="../../../../flags/IRL.PNG" alt="IRL"></td>
          <td class="horseCell"><span class="horseName">Agatha Raisin</span></td>
          <td></td>
          <td></td>
          <td>WDbDRE</td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_CCI3_SATURDAY_XC_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CCI3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 29 2026  6:11PM</p>
    <table>
      <thead>
        <tr>
          <th>Start Time Cross/ Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td>18:18:00</td>
          <td>102</td>
          <td class="riderCell"><span class="riderName">Niklas LINDB&Auml;CK</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">A Star Is Born Vuo</span></td>
          <td>303,0</td>
          <td>65,87</td>
          <td>34,1</td>
          <td>4.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td>18:09:00</td>
          <td>105</td>
          <td class="riderCell"><span class="riderName">Martina ANDERSSON</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Condor Da Carma</span></td>
          <td>296,0</td>
          <td>64,35</td>
          <td>35,7</td>
          <td>8.</td>
          <td>0,0</td>
          <td></td>
          <td>35,7</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>5.</strong></td>
          <td>106</td>
          <td class="riderCell"><span class="riderName">Anna NILSSON</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Crottys Rock</span></td>
          <td>305,0</td>
          <td>66,30</td>
          <td>33,7</td>
          <td>3.</td>
          <td>5,6</td>
          <td>06:18</td>
          <td>39,3</td>
          <td>5.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>7.</strong></td>
          <td>103</td>
          <td class="riderCell"><span class="riderName">Jenny GLEBENIUS</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Canela</span></td>
          <td>273,0</td>
          <td>59,35</td>
          <td>40,7</td>
          <td>15.</td>
          <td>0,0</td>
          <td>06:00</td>
          <td>40,7</td>
          <td>7.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>109</td>
          <td class="riderCell"><span class="riderName">Aria RAMKALI</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Flanders</span></td>
          <td>315,0</td>
          <td>68,48</td>
          <td>31,5</td>
          <td>1.</td>
          <td></td>
          <td></td>
          <td>EL XC</td>
          <td></td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_CCI3_SUNDAY_SJ_COMPLETE_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CCI3*-S</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 30 2026  4:26PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>118</td>
          <td class="riderCell"><span class="riderName">Katrin NORLING</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Zixten af Tollstad</span></td>
          <td>302,0</td>
          <td>65,65</td>
          <td>34,4</td>
          <td>5.</td>
          <td>4,0</td>
          <td>06:14</td>
          <td>38,4</td>
          <td>2.</td>
          <td>0,0</td>
          <td>70,15</td>
          <td>38,4</td>
        </tr>
        <tr class="parent0">
          <td><strong>2.</strong></td>
          <td>102</td>
          <td class="riderCell"><span class="riderName">Niklas LINDB&Auml;CK</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">A Star Is Born Vuo</span></td>
          <td>303,0</td>
          <td>65,87</td>
          <td>34,1</td>
          <td>4.</td>
          <td>1,2</td>
          <td>06:07</td>
          <td>35,3</td>
          <td>1.</td>
          <td>4,0</td>
          <td>67,94</td>
          <td>39,3</td>
        </tr>
        <tr class="parent0">
          <td><strong>3.</strong></td>
          <td>103</td>
          <td class="riderCell"><span class="riderName">Jenny GLEBENIUS</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Canela</span></td>
          <td>273,0</td>
          <td>59,35</td>
          <td>40,7</td>
          <td>15.</td>
          <td>0,0</td>
          <td>06:00</td>
          <td>40,7</td>
          <td>4.</td>
          <td>0,0</td>
          <td>69,04</td>
          <td>40,7</td>
        </tr>
        <tr class="parent0">
          <td><strong></strong></td>
          <td>111</td>
          <td class="riderCell"><span class="riderName">Linnea OP DE WEEGH THVETUS</span></td>
          <td><img src="../../../../flags/SWE.PNG" alt="SWE"></td>
          <td class="horseCell"><span class="horseName">Joli Harlem LVST</span></td>
          <td>282,5</td>
          <td>61,41</td>
          <td>38,6</td>
          <td>12.</td>
          <td>36,8</td>
          <td>06:46</td>
          <td>75,4</td>
          <td>12.</td>
          <td></td>
          <td></td>
          <td>EL SJ</td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

SEGERSJO_YR_JUNA_R_XC_CORRECTION_HTML = """
<html>
  <head><title>LeaderBoard · Segersjö 2026 · CH-EU-Y-CCI3*-L</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 29 2026  5:21PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>331</td>
          <td class="riderCell"><span class="riderName">Carl VOIGT</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">DSP Descansado</span></td>
          <td>573,0</td>
          <td>76,40</td>
          <td>23,6</td>
          <td>1.</td>
          <td>0,0</td>
          <td>08:46</td>
          <td>23,6</td>
          <td>1.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>32.</strong></td>
          <td>327</td>
          <td class="riderCell"><span class="riderName">Silva KELLY</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">Calypso</span></td>
          <td>508,5</td>
          <td>67,80</td>
          <td>32,2</td>
          <td>21.</td>
          <td>18,4</td>
          <td>09:32</td>
          <td>50,6</td>
          <td>32.</td>
          <td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td><strong>39.</strong></td>
          <td>339</td>
          <td class="riderCell"><span class="riderName">Eleonora FAVA</span></td>
          <td><sup>*</sup><img src="../../../../flags/ITA.PNG" alt="ITA"></td>
          <td class="horseCell"><span class="horseName">Juna R</span></td>
          <td>532,5</td>
          <td>71,00</td>
          <td>29,0</td>
          <td>6.</td>
          <td>51,2</td>
          <td>10:04</td>
          <td>80,2</td>
          <td>39.</td>
          <td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""

AACHEN_DRESSAGE_HTML = """
<html>
  <head><title>LeaderBoard · Aachen 2026 · FEI Eventing World Championship</title></head>
  <body>
    <p class="lastupdate">Last Update: Aug 12 2026 2:00PM</p>
    <table>
      <thead>
        <tr>
          <th>Rank</th><th>No.</th><th>Rider</th><th>&nbsp;</th><th>Horse</th>
          <th>Dressage</th><th>Rank after Dressage</th>
          <th>Cross-Country</th><th>Rank after Cross-Country</th>
          <th>Jumping</th><th>Final Score</th>
        </tr>
      </thead>
      <tbody>
        <tr class="parent0">
          <td><strong>1.</strong></td>
          <td>138</td>
          <td class="riderCell"><span class="riderName">Michael JUNG</span></td>
          <td><sup>*</sup><img src="../../../../flags/GER.PNG" alt="GER"></td>
          <td class="horseCell"><span class="horseName">fischerChipmunk FRH</span></td>
          <td>480,0</td>
          <td>80,00</td>
          <td>20,0</td>
          <td>1.</td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
        <tr class="parent0">
          <td></td>
          <td>107</td>
          <td class="riderCell"><span class="riderName">Daniel DUNST</span></td>
          <td><sup>*</sup><img src="../../../../flags/AUT.PNG" alt="AUT"></td>
          <td class="horseCell"><span class="horseName">Chevalier 97</span></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td>
          <td></td><td></td><td></td><td></td><td></td><td></td><td></td>
        </tr>
      </tbody>
    </table>
  </body>
</html>
"""


class RechenstelleTests(unittest.TestCase):
    def test_parse_leaderboard_results_normalizes_scores_and_skips_status_rows(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/millstreet_07/leaderboard52.html",
            event_name="Millstreet · CH-M-U25-C",
            level="CH-M-U25-C",
            event_date=date(2026, 7, 21),
            country="IRL",
        )
        collected_at = datetime(2026, 7, 24, 2, 0, tzinfo=timezone.utc)
        results = parse_leaderboard_results(
            SAMPLE_HTML,
            board=board,
            collected_at=collected_at,
        )

        self.assertEqual(len(results), 2)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Calvin BÖCKMANN (GER)")
        self.assertEqual(leader.horse_name, "Altair de la Cense")
        self.assertEqual(leader.dressage_score, 27.6)
        self.assertEqual(leader.finishing_score, 27.6)
        self.assertEqual(leader.source_id, "rechenstelle")
        self.assertEqual(leader.event_name, "Millstreet · CH-M-U25-C")

        second = results[1]
        self.assertEqual(second.cross_country_jump_penalties, 20.0)
        self.assertEqual(second.cross_country_time_penalties, 1.6)
        self.assertEqual(second.show_jumping_penalties, 4.0)
        self.assertEqual(second.finishing_score, 54.8)

    def test_parse_short_format_uses_jumping_faults_not_clock_time(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/millstreet_07/leaderboard05.html",
            event_name="Millstreet · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 7, 21),
            country="IRL",
        )
        results = parse_leaderboard_results(SHORT_FORMAT_HTML, board=board)

        self.assertEqual(len(results), 2)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Ian CASSELLS (IRL)")
        self.assertEqual(leader.dressage_score, 29.9)
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.cross_country_time_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 29.9)

        eighth = results[1]
        self.assertEqual(eighth.rider_name, "Kevin MCNAB (AUS)")
        self.assertEqual(eighth.show_jumping_penalties, 4.0)
        self.assertEqual(eighth.finishing_score, 34.0)

    def test_parse_long_format_ignores_mmss_clock_times(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/millstreet_07/leaderboard02.html",
            event_name="Millstreet · CCI3*-L",
            level="CCI3*-L",
            event_date=date(2026, 7, 21),
            country="IRL",
        )
        results = parse_leaderboard_results(LONG_FORMAT_CLOCK_TIME_HTML, board=board)

        self.assertEqual(len(results), 1)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Hallie COON (USA)")
        self.assertEqual(leader.cross_country_jump_penalties, 2.8)
        self.assertEqual(leader.cross_country_time_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 37.1)

    def test_aachen_start_list_without_dressage_yields_no_scored_rows(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_START_LIST_HTML, board=board)
        self.assertEqual(results, [])

    def test_aachen_dressage_scores_are_parsed(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_DRESSAGE_HTML, board=board)
        self.assertEqual(len(results), 1)
        leader = results[0]
        self.assertEqual(leader.rider_name, "Michael JUNG (GER)")
        self.assertEqual(leader.horse_name, "fischerChipmunk FRH")
        self.assertEqual(leader.dressage_score, 20.0)
        self.assertEqual(leader.event_name, "Aachen · CH-M-C")
        self.assertEqual(leader.level, "CH-M-C")
        self.assertEqual(leader.country, "GER")

    def test_aachen_live_first_hour_dressage_leaders_are_parsed(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_FIRST_HOUR_HTML, board=board)
        self.assertEqual(len(results), 2)
        leader, second = results
        self.assertEqual(leader.rider_name, "Clarke JOHNSTONE (NZL)")
        self.assertEqual(leader.horse_name, "Rocket Man")
        self.assertEqual(leader.dressage_score, 28.7)
        self.assertEqual(leader.finishing_score, 28.7)
        self.assertEqual(second.rider_name, "Benjamin MASSIE (FRA)")
        self.assertEqual(second.horse_name, "Figaro Fonroy")
        self.assertEqual(second.dressage_score, 36.0)

    def test_aachen_live_revised_dressage_marks_use_score_column(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_REVISED_MARKS_HTML, board=board)
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        self.assertEqual(by_horse["Rocket Man"].dressage_score, 28.7)
        self.assertEqual(by_horse["Grandeur de Lully CH"].rider_name, "Robin GODEL (SUI)")
        self.assertEqual(by_horse["Grandeur de Lully CH"].dressage_score, 30.1)
        self.assertEqual(by_horse["Caramia FRH"].rider_name, "Libussa LÜBBEKE (GER)")
        self.assertEqual(by_horse["Caramia FRH"].dressage_score, 31.3)
        self.assertEqual(by_horse["Google van Alsingen"].rider_name, "Senne VERVAECKE (BEL)")
        self.assertEqual(by_horse["Google van Alsingen"].dressage_score, 35.1)

    def test_aachen_live_midmorning_inserts_stevens_second(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_MIDMORNING_HTML, board=board)
        self.assertEqual(len(results), 3)
        leader, second, third = results
        self.assertEqual(leader.rider_name, "Clarke JOHNSTONE (NZL)")
        self.assertEqual(leader.horse_name, "Rocket Man")
        self.assertEqual(leader.dressage_score, 28.7)
        self.assertEqual(second.rider_name, "Gemma STEVENS (GBR)")
        self.assertEqual(second.horse_name, "Flash Cooley")
        self.assertEqual(second.dressage_score, 29.3)
        self.assertEqual(second.finishing_score, 29.3)
        self.assertEqual(third.rider_name, "Robin GODEL (SUI)")
        self.assertEqual(third.dressage_score, 30.1)

    def test_aachen_live_afternoon_inserts_price_lead(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_AFTERNOON_HTML, board=board)
        self.assertEqual(len(results), 4)
        leader, second, third, fourth = results
        self.assertEqual(leader.rider_name, "Jonelle PRICE (NZL)")
        self.assertEqual(leader.horse_name, "Senor Crocodillo")
        self.assertEqual(leader.dressage_score, 27.2)
        self.assertEqual(leader.finishing_score, 27.2)
        self.assertEqual(second.rider_name, "Clarke JOHNSTONE (NZL)")
        self.assertEqual(second.horse_name, "Rocket Man")
        self.assertEqual(second.dressage_score, 28.7)
        self.assertEqual(third.rider_name, "Gemma STEVENS (GBR)")
        self.assertEqual(third.horse_name, "Flash Cooley")
        self.assertEqual(third.dressage_score, 29.3)
        self.assertEqual(fourth.rider_name, "Maarten BOON (BEL)")
        self.assertEqual(fourth.horse_name, "Gravin van Cantos")
        self.assertEqual(fourth.dressage_score, 31.4)

    def test_aachen_live_1400_revises_woods_and_aondio_marks(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1400_HTML, board=board)
        self.assertEqual(len(results), 4)
        leader, dutton, woods, aondio = results
        self.assertEqual(leader.rider_name, "Jonelle PRICE (NZL)")
        self.assertEqual(leader.horse_name, "Senor Crocodillo")
        self.assertEqual(leader.dressage_score, 27.2)
        self.assertEqual(dutton.rider_name, "Phillip DUTTON (USA)")
        self.assertEqual(dutton.horse_name, "Denim")
        self.assertEqual(dutton.dressage_score, 32.6)
        self.assertEqual(woods.rider_name, "Sam WOODS (AUS)")
        self.assertEqual(woods.horse_name, "SS Eight Count")
        self.assertEqual(woods.dressage_score, 37.4)
        self.assertEqual(woods.finishing_score, 37.4)
        self.assertEqual(aondio.rider_name, "Francesco AONDIO BERTERO (ITA)")
        self.assertEqual(aondio.horse_name, "It's Athene")
        self.assertEqual(aondio.dressage_score, 41.2)
        self.assertEqual(aondio.finishing_score, 41.2)

    def test_aachen_live_1502_inserts_goury_second(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1502_HTML, board=board)
        self.assertEqual(len(results), 5)
        leader, goury, johnstone, stevens, sukdolak = results
        self.assertEqual(leader.rider_name, "Jonelle PRICE (NZL)")
        self.assertEqual(leader.horse_name, "Senor Crocodillo")
        self.assertEqual(leader.dressage_score, 27.2)
        self.assertEqual(goury.rider_name, "Alexis GOURY (FRA)")
        self.assertEqual(goury.horse_name, "Je'vall")
        self.assertEqual(goury.dressage_score, 28.3)
        self.assertEqual(goury.finishing_score, 28.3)
        self.assertEqual(johnstone.rider_name, "Clarke JOHNSTONE (NZL)")
        self.assertEqual(johnstone.horse_name, "Rocket Man")
        self.assertEqual(johnstone.dressage_score, 28.7)
        self.assertEqual(stevens.rider_name, "Gemma STEVENS (GBR)")
        self.assertEqual(stevens.horse_name, "Flash Cooley")
        self.assertEqual(stevens.dressage_score, 29.3)
        self.assertEqual(sukdolak.rider_name, "Matěj SUKDOLÁK (CZE)")
        self.assertEqual(sukdolak.horse_name, "Qaid")
        self.assertEqual(sukdolak.dressage_score, 44.0)

    def test_aachen_live_1506_revises_goury_and_adds_johner(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1506_HTML, board=board)
        self.assertEqual(len(results), 3)
        leader, goury, johner = results
        self.assertEqual(leader.rider_name, "Jonelle PRICE (NZL)")
        self.assertEqual(leader.horse_name, "Senor Crocodillo")
        self.assertEqual(leader.dressage_score, 27.2)
        self.assertEqual(goury.rider_name, "Alexis GOURY (FRA)")
        self.assertEqual(goury.horse_name, "Je'vall")
        self.assertEqual(goury.dressage_score, 28.5)
        self.assertEqual(goury.finishing_score, 28.5)
        self.assertEqual(johner.rider_name, "Mélody JOHNER (SUI)")
        self.assertEqual(johner.horse_name, "Erin")
        self.assertEqual(johner.dressage_score, 32.6)
        self.assertEqual(johner.finishing_score, 32.6)

    def test_aachen_live_1602_inserts_mcewen_lead_and_revises_johner(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1602_HTML, board=board)
        self.assertEqual(len(results), 4)
        leader, price, hansen, johner = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.horse_name, "JL Dublin")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(leader.finishing_score, 26.6)
        self.assertEqual(price.rider_name, "Jonelle PRICE (NZL)")
        self.assertEqual(price.horse_name, "Senor Crocodillo")
        self.assertEqual(price.dressage_score, 27.2)
        self.assertEqual(hansen.rider_name, "Malin HANSEN-HOTOPP (GER)")
        self.assertEqual(hansen.horse_name, "Carlitos Quidditch K")
        self.assertEqual(hansen.dressage_score, 28.6)
        self.assertEqual(hansen.finishing_score, 28.6)
        self.assertEqual(johner.rider_name, "Mélody JOHNER (SUI)")
        self.assertEqual(johner.horse_name, "Erin")
        self.assertEqual(johner.dressage_score, 31.5)
        self.assertEqual(johner.finishing_score, 31.5)

    def test_aachen_live_1658_inserts_lissington_barton_and_revises_torlonia(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1658_HTML, board=board)
        self.assertEqual(len(results), 4)
        leader, lissington, barton, torlonia = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.horse_name, "JL Dublin")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(leader.finishing_score, 26.6)
        self.assertEqual(lissington.rider_name, "Samantha LISSINGTON (NZL)")
        self.assertEqual(lissington.horse_name, "Lucas Stone")
        self.assertEqual(lissington.dressage_score, 29.7)
        self.assertEqual(lissington.finishing_score, 29.7)
        self.assertEqual(barton.rider_name, "Olivia BARTON (AUS)")
        self.assertEqual(barton.horse_name, "APH Sodoku")
        self.assertEqual(barton.dressage_score, 30.6)
        self.assertEqual(barton.finishing_score, 30.6)
        self.assertEqual(torlonia.rider_name, "Paolo TORLONIA (ITA)")
        self.assertEqual(torlonia.horse_name, "Zinny")
        self.assertEqual(torlonia.dressage_score, 40.8)
        self.assertEqual(torlonia.finishing_score, 40.8)

    def test_aachen_live_1720_revises_lindberg_torlonia_and_limaye(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1720_HTML, board=board)
        self.assertEqual(len(results), 4)
        leader, lindberg, torlonia, limaye = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.horse_name, "JL Dublin")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(leader.finishing_score, 26.6)
        self.assertEqual(lindberg.rider_name, "Axel LINDBERG (FIN)")
        self.assertEqual(lindberg.horse_name, "Quelle Bonne")
        self.assertEqual(lindberg.dressage_score, 39.0)
        self.assertEqual(lindberg.finishing_score, 39.0)
        self.assertEqual(torlonia.rider_name, "Paolo TORLONIA (ITA)")
        self.assertEqual(torlonia.horse_name, "Zinny")
        self.assertEqual(torlonia.dressage_score, 41.3)
        self.assertEqual(torlonia.finishing_score, 41.3)
        self.assertEqual(limaye.rider_name, "Ashish LIMAYE (IND)")
        self.assertEqual(limaye.horse_name, "D'Avril du Pinier")
        self.assertEqual(limaye.dressage_score, 44.6)
        self.assertEqual(limaye.finishing_score, 44.6)

    def test_aachen_live_1000_friday_adds_flarup_kaizinger_pawlak_slaoui_pitakanonda(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1000_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 7)
        leader, goury, flarup, kaizinger, pawlak, slaoui, pitakanonda = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.horse_name, "JL Dublin")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(leader.finishing_score, 26.6)
        self.assertEqual(goury.rider_name, "Alexis GOURY (FRA)")
        self.assertEqual(goury.horse_name, "Je'Vall")
        self.assertEqual(goury.dressage_score, 28.5)
        self.assertEqual(flarup.rider_name, "Peter T. FLARUP (DEN)")
        self.assertEqual(flarup.horse_name, "H.Carald Z")
        self.assertEqual(flarup.dressage_score, 31.5)
        self.assertEqual(kaizinger.rider_name, "Balázs KAIZINGER (HUN)")
        self.assertEqual(kaizinger.horse_name, "Clover 15")
        self.assertEqual(kaizinger.dressage_score, 35.3)
        self.assertEqual(pawlak.rider_name, "Joanna PAWLAK (POL)")
        self.assertEqual(pawlak.horse_name, "Armin de Monsieur")
        self.assertEqual(pawlak.dressage_score, 37.2)
        self.assertEqual(slaoui.rider_name, "Noor SLAOUI (MAR)")
        self.assertEqual(slaoui.horse_name, "Legende P")
        self.assertEqual(slaoui.dressage_score, 38.7)
        self.assertEqual(pitakanonda.rider_name, "Weerapat PITAKANONDA (THA)")
        self.assertEqual(pitakanonda.horse_name, "B.Grimm Chateau de Versailles M2S")
        self.assertEqual(pitakanonda.dressage_score, 41.4)

    def test_aachen_live_1007_friday_revises_flarup_and_adds_hua_tian(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1007_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 4)
        leader, hua_tian, flarup, pitakanonda = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.horse_name, "JL Dublin")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(hua_tian.rider_name, "Alex HUA TIAN (CHN)")
        self.assertEqual(hua_tian.horse_name, "Chicko")
        self.assertEqual(hua_tian.dressage_score, 31.9)
        self.assertEqual(flarup.rider_name, "Peter T. FLARUP (DEN)")
        self.assertEqual(flarup.horse_name, "H.Carald Z")
        self.assertEqual(flarup.dressage_score, 35.1)
        self.assertEqual(pitakanonda.rider_name, "Weerapat PITAKANONDA (THA)")
        self.assertEqual(pitakanonda.horse_name, "B.Grimm Chateau de Versailles M2S")
        self.assertEqual(pitakanonda.dressage_score, 41.4)

    def test_aachen_live_1102_friday_adds_spencer_martin_and_revises_hua_tian(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1102_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 6)
        leader, spencer, martin, hua_tian, khoddam, brezina = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.horse_name, "JL Dublin")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(spencer.rider_name, "Monica SPENCER (NZL)")
        self.assertEqual(spencer.horse_name, "Artist")
        self.assertEqual(spencer.dressage_score, 28.9)
        self.assertEqual(martin.rider_name, "Boyd MARTIN (USA)")
        self.assertEqual(martin.horse_name, "Cooley Nutcracker")
        self.assertEqual(martin.dressage_score, 30.9)
        self.assertEqual(hua_tian.rider_name, "Alex HUA TIAN (CHN)")
        self.assertEqual(hua_tian.horse_name, "Chicko")
        self.assertEqual(hua_tian.dressage_score, 32.5)
        self.assertEqual(khoddam.rider_name, "Katrin KHODDAM-HAZRATI (AUT)")
        self.assertEqual(khoddam.horse_name, "Renegade")
        self.assertEqual(khoddam.dressage_score, 38.3)
        self.assertEqual(brezina.rider_name, "Pavel BŘEZINA (CZE)")
        self.assertEqual(brezina.horse_name, "Turin")
        self.assertEqual(brezina.dressage_score, 38.8)

    def test_aachen_live_1105_friday_adds_barrett_into_second(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1105_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 3)
        leader, barrett, spencer = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.horse_name, "JL Dublin")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(barrett.rider_name, "Oliver BARRETT (AUS)")
        self.assertEqual(barrett.horse_name, "Sandhills Briar")
        self.assertEqual(barrett.dressage_score, 26.7)
        self.assertEqual(spencer.rider_name, "Monica SPENCER (NZL)")
        self.assertEqual(spencer.horse_name, "Artist")
        self.assertEqual(spencer.dressage_score, 28.9)

    def test_aachen_live_1105_friday_revises_in_progress_barrett_to_30_2(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1105_BARRETT_REVISED_HTML, board=board)
        self.assertEqual(len(results), 2)
        leader, barrett = results
        self.assertEqual(leader.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(leader.dressage_score, 26.6)
        self.assertEqual(barrett.rider_name, "Oliver BARRETT (AUS)")
        self.assertEqual(barrett.horse_name, "Sandhills Briar")
        self.assertEqual(barrett.dressage_score, 30.2)

    def test_aachen_live_1151_friday_krajewski_leads_and_adds_oconnor_maksud(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1151_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 8)
        (
            krajewski,
            mcewen,
            oconnor,
            maksud,
            barrett,
            romeike,
            parro,
            minder,
        ) = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(mcewen.rider_name, "Tom MCEWEN (GBR)")
        self.assertEqual(mcewen.horse_name, "JL Dublin")
        self.assertEqual(mcewen.dressage_score, 26.6)
        self.assertEqual(oconnor.rider_name, "Austin O'CONNOR (IRL)")
        self.assertEqual(oconnor.horse_name, "Colorado Blue")
        self.assertEqual(oconnor.dressage_score, 29.0)
        self.assertEqual(maksud.rider_name, "Gaspard MAKSUD (FRA)")
        self.assertEqual(maksud.horse_name, "Zaragoza")
        self.assertEqual(maksud.dressage_score, 29.3)
        self.assertEqual(barrett.rider_name, "Oliver BARRETT (AUS)")
        self.assertEqual(barrett.horse_name, "Sandhills Briar")
        self.assertEqual(barrett.dressage_score, 31.7)
        self.assertEqual(romeike.rider_name, "Louise ROMEIKE (SWE)")
        self.assertEqual(romeike.horse_name, "Caspian 15")
        self.assertEqual(romeike.dressage_score, 35.3)
        self.assertEqual(parro.rider_name, "Carlos PARRO (BRA)")
        self.assertEqual(parro.horse_name, "Safira")
        self.assertEqual(parro.dressage_score, 44.2)
        self.assertEqual(minder.rider_name, "Nadja MINDER (SUI)")
        self.assertEqual(minder.horse_name, "Top Job's Jalisco")
        self.assertEqual(minder.dressage_score, 46.5)

    def test_aachen_live_1203_friday_revises_barrett_parro_and_nagura(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1203_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 4)
        krajewski, barrett, nagura, parro = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(barrett.rider_name, "Oliver BARRETT (AUS)")
        self.assertEqual(barrett.horse_name, "Sandhills Briar")
        self.assertEqual(barrett.dressage_score, 31.3)
        self.assertEqual(nagura.rider_name, "Kento NAGURA (JPN)")
        self.assertEqual(nagura.horse_name, "Vinci de la Vigne JRA")
        self.assertEqual(nagura.dressage_score, 33.3)
        self.assertEqual(parro.rider_name, "Carlos PARRO (BRA)")
        self.assertEqual(parro.horse_name, "Safira")
        self.assertEqual(parro.dressage_score, 44.5)

    def test_aachen_live_1301_friday_inserts_collett_second(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1301_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 6)
        krajewski, collett, goss, donckers, harris, cincinnati = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(goss.rider_name, "Georgie GOSS (IRL)")
        self.assertEqual(goss.horse_name, "Kojak")
        self.assertEqual(goss.dressage_score, 31.2)
        self.assertEqual(donckers.rider_name, "Karin DONCKERS (BEL)")
        self.assertEqual(donckers.horse_name, "Leipheimer van't Verahof")
        self.assertEqual(donckers.dressage_score, 31.7)
        self.assertEqual(harris.rider_name, "Caroline HARRIS (GBR)")
        self.assertEqual(harris.horse_name, "D. Day")
        self.assertEqual(harris.dressage_score, 32.6)
        self.assertEqual(cincinnati.rider_name, "Andrea CINCINNATI (ITA)")
        self.assertEqual(cincinnati.horse_name, "Cecelia Lad")
        self.assertEqual(cincinnati.dressage_score, 33.8)

    def test_aachen_live_1324_friday_inserts_wahler_and_revises_marks(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1324_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 6)
        krajewski, collett, wahler, goss, giessen, cincinnati = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(wahler.rider_name, "Christoph WAHLER (GER)")
        self.assertEqual(wahler.horse_name, "D'Accord FRH")
        self.assertEqual(wahler.dressage_score, 29.4)
        self.assertEqual(goss.rider_name, "Georgie GOSS (IRL)")
        self.assertEqual(goss.horse_name, "Kojak")
        self.assertEqual(goss.dressage_score, 31.0)
        self.assertEqual(giessen.rider_name, "Jillian GIESSEN (NED)")
        self.assertEqual(giessen.horse_name, "Seattle Park")
        self.assertEqual(giessen.dressage_score, 33.9)
        self.assertEqual(cincinnati.rider_name, "Andrea CINCINNATI (ITA)")
        self.assertEqual(cincinnati.horse_name, "Cecelia Lad")
        self.assertEqual(cincinnati.dressage_score, 34.1)

    def test_aachen_live_1517_friday_inserts_smith_siegl_coleman_nicolas_tim_price(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1517_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 6)
        krajewski, smith, siegl, coleman, nicolas, tim_price = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(smith.rider_name, "Tamra SMITH (USA)")
        self.assertEqual(smith.horse_name, "Lillet 3")
        self.assertEqual(smith.dressage_score, 27.0)
        self.assertEqual(siegl.rider_name, "Lea SIEGL (AUT)")
        self.assertEqual(siegl.horse_name, "Watermill Giorgio RS")
        self.assertEqual(siegl.dressage_score, 29.2)
        self.assertEqual(coleman.rider_name, "William COLEMAN (USA)")
        self.assertEqual(coleman.horse_name, "Diabolo")
        self.assertEqual(coleman.dressage_score, 30.0)
        self.assertEqual(nicolas.rider_name, "Astier NICOLAS (FRA)")
        self.assertEqual(nicolas.horse_name, "Alertamalib'Or")
        self.assertEqual(nicolas.dressage_score, 30.6)
        self.assertEqual(tim_price.rider_name, "Tim PRICE (NZL)")
        self.assertEqual(tim_price.horse_name, "Falco")
        self.assertEqual(tim_price.dressage_score, 33.7)

    def test_aachen_live_1521_friday_empty_rank_tanaka_settles_at_29_4(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1521_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 3)
        krajewski, smith, tanaka = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(smith.rider_name, "Tamra SMITH (USA)")
        self.assertEqual(smith.horse_name, "Lillet 3")
        self.assertEqual(smith.dressage_score, 27.0)
        self.assertEqual(tanaka.rider_name, "Toshiyuki TANAKA (JPN)")
        self.assertEqual(tanaka.horse_name, "Jefferson JRA")
        self.assertEqual(tanaka.dressage_score, 29.4)

    def test_aachen_live_1611_friday_inserts_touzaint_hoy_and_empty_rank_vogg(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1611_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 6)
        krajewski, vogg, touzaint, hoy, carvalho, mccarthy = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(vogg.rider_name, "Felix VOGG (SUI)")
        self.assertEqual(vogg.horse_name, "Frieda")
        self.assertEqual(vogg.dressage_score, 25.0)
        self.assertEqual(touzaint.rider_name, "Nicolas TOUZAINT (FRA)")
        self.assertEqual(touzaint.horse_name, "Diabolo Menthe")
        self.assertEqual(touzaint.dressage_score, 26.7)
        self.assertEqual(hoy.rider_name, "Andrew HOY (AUS)")
        self.assertEqual(hoy.horse_name, "Vassily de Lassos")
        self.assertEqual(hoy.dressage_score, 26.9)
        self.assertEqual(carvalho.rider_name, "Marcio CARVALHO JORGE (BRA)")
        self.assertEqual(carvalho.horse_name, "Royal Encounter")
        self.assertEqual(carvalho.dressage_score, 31.2)
        self.assertEqual(mccarthy.rider_name, "Padraig MCCARTHY (IRL)")
        self.assertEqual(mccarthy.horse_name, "MGH Zabaione")
        self.assertEqual(mccarthy.dressage_score, 32.8)

    def test_aachen_live_1615_friday_empty_rank_vogg_settles_at_29_3(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1615_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 4)
        krajewski, touzaint, hoy, vogg = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(touzaint.rider_name, "Nicolas TOUZAINT (FRA)")
        self.assertEqual(touzaint.horse_name, "Diabolo Menthe")
        self.assertEqual(touzaint.dressage_score, 26.7)
        self.assertEqual(hoy.rider_name, "Andrew HOY (AUS)")
        self.assertEqual(hoy.horse_name, "Vassily de Lassos")
        self.assertEqual(hoy.dressage_score, 26.9)
        self.assertEqual(vogg.rider_name, "Felix VOGG (SUI)")
        self.assertEqual(vogg.horse_name, "Frieda")
        self.assertEqual(vogg.dressage_score, 29.3)

    def test_aachen_live_1620_friday_empty_rank_jung_in_progress(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1620_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 3)
        krajewski, collett, jung = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(jung.rider_name, "Michael JUNG (GER)")
        self.assertEqual(jung.horse_name, "fischerChipmunk FRH")
        self.assertEqual(jung.dressage_score, 23.1)

    def test_aachen_live_1622_friday_empty_rank_jung_settles_at_23_0(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1622_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 3)
        krajewski, collett, jung = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(jung.rider_name, "Michael JUNG (GER)")
        self.assertEqual(jung.horse_name, "fischerChipmunk FRH")
        self.assertEqual(jung.dressage_score, 23.0)

    def test_aachen_live_1657_friday_inserts_canter_andersen_panizzon_de_liedekerke_de_jong(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1657_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 8)
        (
            krajewski,
            collett,
            jung,
            canter,
            andersen,
            panizzon,
            de_liedekerke,
            de_jong,
        ) = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(jung.rider_name, "Michael JUNG (GER)")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(canter.rider_name, "Rosalind CANTER (GBR)")
        self.assertEqual(canter.horse_name, "Lordships Graffalo")
        self.assertEqual(canter.dressage_score, 23.4)
        self.assertEqual(andersen.rider_name, "Frida ANDERSEN (SWE)")
        self.assertEqual(andersen.horse_name, "Box Leo")
        self.assertEqual(andersen.dressage_score, 32.2)
        self.assertEqual(panizzon.rider_name, "Vittoria PANIZZON (ITA)")
        self.assertEqual(panizzon.horse_name, "DHI Jackpot")
        self.assertEqual(panizzon.dressage_score, 32.9)
        self.assertEqual(de_liedekerke.rider_name, "Lara DE LIEDEKERKE-MEIER (BEL)")
        self.assertEqual(de_liedekerke.horse_name, "Kiarado d'Arville")
        self.assertEqual(de_liedekerke.dressage_score, 33.2)
        self.assertEqual(de_jong.rider_name, "Sanne DE JONG (NED)")
        self.assertEqual(de_jong.horse_name, "Enjoy")
        self.assertEqual(de_jong.dressage_score, 37.5)

    def test_aachen_live_1723_friday_rank_header_keeps_dressage_close(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1723_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 4)
        krajewski, collett, jung, canter = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(jung.rider_name, "Michael JUNG (GER)")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(canter.rider_name, "Rosalind CANTER (GBR)")
        self.assertEqual(canter.horse_name, "Lordships Graffalo")
        self.assertEqual(canter.dressage_score, 23.4)
        self.assertTrue(all(result.show_jumping_penalties == 0.0 for result in results))
        self.assertTrue(
            all(
                result.cross_country_jump_penalties == 0.0
                and result.cross_country_time_penalties == 0.0
                for result in results
            )
        )

    def test_aachen_live_1900_friday_officializes_dressage_rank_header(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1900_FRIDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 14 2026  7:00PM")
        self.assertEqual(parser.header_cells[0], "Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1900_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 5)
        krajewski, collett, jung, canter, panizzon = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(jung.rider_name, "Michael JUNG (GER)")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(canter.rider_name, "Rosalind CANTER (GBR)")
        self.assertEqual(canter.horse_name, "Lordships Graffalo")
        self.assertEqual(canter.dressage_score, 23.4)
        self.assertEqual(panizzon.rider_name, "Vittoria PANIZZON (ITA)")
        self.assertEqual(panizzon.horse_name, "DHI Jackpot")
        self.assertEqual(panizzon.dressage_score, 32.9)
        self.assertTrue(all(result.show_jumping_penalties == 0.0 for result in results))
        self.assertTrue(
            all(
                result.cross_country_jump_penalties == 0.0
                and result.cross_country_time_penalties == 0.0
                for result in results
            )
        )

    def test_aachen_live_1922_friday_publishes_xc_start_times(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1922_FRIDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 14 2026  7:22PM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1922_FRIDAY_HTML, board=board)
        self.assertEqual(len(results), 5)
        krajewski, collett, jung, canter, panizzon = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.rider_name, "Laura COLLETT (GBR)")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(jung.rider_name, "Michael JUNG (GER)")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(canter.rider_name, "Rosalind CANTER (GBR)")
        self.assertEqual(canter.horse_name, "Lordships Graffalo")
        self.assertEqual(canter.dressage_score, 23.4)
        self.assertEqual(panizzon.rider_name, "Vittoria PANIZZON (ITA)")
        self.assertEqual(panizzon.horse_name, "DHI Jackpot")
        self.assertEqual(panizzon.dressage_score, 32.9)
        self.assertTrue(all(result.show_jumping_penalties == 0.0 for result in results))
        self.assertTrue(
            all(
                result.cross_country_jump_penalties == 0.0
                and result.cross_country_time_penalties == 0.0
                for result in results
            )
        )

    def test_aachen_live_0854_saturday_skips_wdbxc_before_cross_country(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_0854_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  8:54AM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_0854_SATURDAY_HTML, board=board)
        self.assertEqual(len(results), 5)
        rider_names = [result.rider_name for result in results]
        self.assertNotIn("Sanna SILTAKORPI (FIN)", rider_names)
        self.assertNotIn("Florinoor HOOGLAND (NED)", rider_names)
        krajewski, collett, jung, canter, panizzon = results
        self.assertEqual(krajewski.rider_name, "Julia KRAJEWSKI (GER)")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(canter.dressage_score, 23.4)
        self.assertEqual(panizzon.rider_name, "Vittoria PANIZZON (ITA)")
        self.assertEqual(panizzon.dressage_score, 32.9)
        self.assertTrue(
            all(
                result.cross_country_jump_penalties == 0.0
                and result.cross_country_time_penalties == 0.0
                for result in results
            )
        )

    def test_aachen_live_1002_saturday_records_in_progress_cross_country(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1002_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026 10:02AM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1002_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 5)
        self.assertNotIn("Clarke JOHNSTONE (NZL)", rider_names)
        self.assertNotIn("Noor SLAOUI (MAR)", rider_names)
        self.assertNotIn("Sanna SILTAKORPI (FIN)", rider_names)
        self.assertNotIn("Florinoor HOOGLAND (NED)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        krajewski = by_rider["Julia KRAJEWSKI (GER)"]
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(krajewski.finishing_score, 22.0)
        self.assertEqual(krajewski.cross_country_jump_penalties, 0.0)
        self.assertEqual(krajewski.cross_country_time_penalties, 0.0)
        hill = by_rider["Sophia HILL (AUS)"]
        self.assertEqual(hill.horse_name, "Humble Glory")
        self.assertEqual(hill.dressage_score, 37.6)
        self.assertEqual(hill.cross_country_jump_penalties, 0.0)
        self.assertEqual(hill.cross_country_time_penalties, 0.0)
        self.assertEqual(hill.finishing_score, 37.6)
        godel = by_rider["Robin GODEL (SUI)"]
        self.assertEqual(godel.horse_name, "Grandeur de Lully CH")
        self.assertEqual(godel.dressage_score, 30.1)
        # Live Faults cells carry T-Faults while Time stays an elapsed clock.
        self.assertEqual(godel.cross_country_jump_penalties, 10.4)
        self.assertEqual(godel.cross_country_time_penalties, 0.0)
        self.assertEqual(godel.finishing_score, 40.5)
        self.assertEqual(by_rider["Laura COLLETT (GBR)"].dressage_score, 22.8)
        self.assertEqual(by_rider["Vittoria PANIZZON (ITA)"].dressage_score, 32.9)

    def test_aachen_live_1103_saturday_records_more_cross_country(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1103_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026 11:03AM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1103_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 5)
        self.assertNotIn("Gemma STEVENS (GBR)", rider_names)
        self.assertNotIn("Francesco AONDIO BERTERO (ITA)", rider_names)
        self.assertNotIn("Senne VERVAECKE (BEL)", rider_names)
        self.assertNotIn("Sanna SILTAKORPI (FIN)", rider_names)
        self.assertNotIn("Florinoor HOOGLAND (NED)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        krajewski = by_rider["Julia KRAJEWSKI (GER)"]
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(krajewski.finishing_score, 22.0)
        self.assertEqual(krajewski.cross_country_jump_penalties, 0.0)
        self.assertEqual(krajewski.cross_country_time_penalties, 0.0)
        samran = by_rider["Korntawat SAMRAN (THA)"]
        self.assertEqual(samran.horse_name, "B.Grimm Carouzo Bois Marotin")
        self.assertEqual(samran.dressage_score, 34.2)
        self.assertEqual(samran.cross_country_jump_penalties, 1.2)
        self.assertEqual(samran.cross_country_time_penalties, 0.0)
        self.assertEqual(samran.finishing_score, 35.4)
        hill = by_rider["Sophia HILL (AUS)"]
        self.assertEqual(hill.horse_name, "Humble Glory")
        self.assertEqual(hill.dressage_score, 37.6)
        self.assertEqual(hill.cross_country_jump_penalties, 0.0)
        self.assertEqual(hill.cross_country_time_penalties, 0.0)
        self.assertEqual(hill.finishing_score, 37.6)
        godel = by_rider["Robin GODEL (SUI)"]
        self.assertEqual(godel.horse_name, "Grandeur de Lully CH")
        self.assertEqual(godel.dressage_score, 30.1)
        self.assertEqual(godel.cross_country_jump_penalties, 10.4)
        self.assertEqual(godel.cross_country_time_penalties, 0.0)
        self.assertEqual(godel.finishing_score, 40.5)
        self.assertEqual(by_rider["Laura COLLETT (GBR)"].dressage_score, 22.8)

    def test_aachen_live_1203_saturday_records_johner_lead_and_new_el_xc(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1203_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026 12:03PM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1203_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 7)
        self.assertNotIn("Caroline PAMUKCU (USA)", rider_names)
        self.assertNotIn("Sam WOODS (AUS)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        krajewski = by_rider["Julia KRAJEWSKI (GER)"]
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(krajewski.finishing_score, 22.0)
        self.assertEqual(krajewski.cross_country_jump_penalties, 0.0)
        self.assertEqual(krajewski.cross_country_time_penalties, 0.0)
        johner = by_rider["Mélody JOHNER (SUI)"]
        self.assertEqual(johner.horse_name, "Erin")
        self.assertEqual(johner.dressage_score, 31.5)
        self.assertEqual(johner.cross_country_jump_penalties, 0.0)
        self.assertEqual(johner.cross_country_time_penalties, 0.0)
        self.assertEqual(johner.finishing_score, 31.5)
        hansen = by_rider["Malin HANSEN-HOTOPP (GER)"]
        self.assertEqual(hansen.horse_name, "Carlitos Quidditch K")
        self.assertEqual(hansen.dressage_score, 28.6)
        self.assertEqual(hansen.cross_country_jump_penalties, 3.2)
        self.assertEqual(hansen.cross_country_time_penalties, 0.0)
        self.assertEqual(hansen.finishing_score, 31.8)
        clark = by_rider["Aoife CLARK (IRL)"]
        self.assertEqual(clark.horse_name, "Full Monty de Lacense")
        self.assertEqual(clark.dressage_score, 31.5)
        self.assertEqual(clark.cross_country_jump_penalties, 1.2)
        self.assertEqual(clark.finishing_score, 32.7)
        benitez = by_rider["Esteban BENITEZ VALLE (ESP)"]
        self.assertEqual(benitez.horse_name, "Utrera AA 35 1")
        self.assertEqual(benitez.dressage_score, 33.3)
        self.assertEqual(benitez.cross_country_jump_penalties, 0.0)
        self.assertEqual(benitez.finishing_score, 33.3)
        goury = by_rider["Alexis GOURY (FRA)"]
        self.assertEqual(goury.horse_name, "Je'Vall")
        self.assertEqual(goury.dressage_score, 28.5)
        self.assertEqual(goury.cross_country_jump_penalties, 6.4)
        self.assertEqual(goury.finishing_score, 34.9)
        mcewen = by_rider["Tom MCEWEN (GBR)"]
        self.assertEqual(mcewen.horse_name, "JL Dublin")
        self.assertEqual(mcewen.dressage_score, 26.6)
        self.assertEqual(mcewen.cross_country_jump_penalties, 11.0)
        self.assertEqual(mcewen.finishing_score, 37.6)

    def test_aachen_live_1408_saturday_records_collett_after_xc_lead(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1408_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  2:08PM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1408_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 10)
        self.assertNotIn("Oliver BARRETT (AUS)", rider_names)
        self.assertNotIn("Nadja MINDER (SUI)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        jung = by_rider["Michael JUNG (GER)"]
        self.assertEqual(jung.horse_name, "fischerChipmunk FRH")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(jung.cross_country_jump_penalties, 0.0)
        self.assertEqual(jung.finishing_score, 23.0)
        collett = by_rider["Laura COLLETT (GBR)"]
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(collett.cross_country_jump_penalties, 0.8)
        self.assertEqual(collett.cross_country_time_penalties, 0.0)
        self.assertEqual(collett.finishing_score, 23.6)
        mcewen = by_rider["Tom MCEWEN (GBR)"]
        self.assertEqual(mcewen.horse_name, "JL Dublin")
        self.assertEqual(mcewen.dressage_score, 26.6)
        self.assertEqual(mcewen.cross_country_jump_penalties, 2.0)
        self.assertEqual(mcewen.finishing_score, 28.6)
        giessen = by_rider["Jillian GIESSEN (NED)"]
        self.assertEqual(giessen.horse_name, "Seattle Park")
        self.assertEqual(giessen.dressage_score, 33.9)
        self.assertEqual(giessen.cross_country_jump_penalties, 0.8)
        self.assertEqual(giessen.finishing_score, 34.7)
        krajewski = by_rider["Julia KRAJEWSKI (GER)"]
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(krajewski.cross_country_jump_penalties, 13.6)
        self.assertEqual(krajewski.finishing_score, 35.6)
        donckers = by_rider["Karin DONCKERS (BEL)"]
        self.assertEqual(donckers.horse_name, "Leipheimer van't Verahof")
        self.assertEqual(donckers.dressage_score, 31.7)
        self.assertEqual(donckers.cross_country_jump_penalties, 18.8)
        self.assertEqual(donckers.finishing_score, 50.5)

    def test_aachen_live_1506_saturday_records_hoy_xc_and_new_el(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1506_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  3:06PM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1506_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 10)
        self.assertNotIn("Toshiyuki TANAKA (JPN)", rider_names)
        self.assertNotIn("Fouaad MIRZA (IND)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        jung = by_rider["Michael JUNG (GER)"]
        self.assertEqual(jung.horse_name, "fischerChipmunk FRH")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(jung.cross_country_jump_penalties, 0.0)
        self.assertEqual(jung.finishing_score, 23.0)
        collett = by_rider["Laura COLLETT (GBR)"]
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(collett.cross_country_jump_penalties, 0.8)
        self.assertEqual(collett.finishing_score, 23.6)
        wahler = by_rider["Christoph WAHLER (GER)"]
        self.assertEqual(wahler.horse_name, "D'Accord FRH")
        self.assertEqual(wahler.dressage_score, 29.4)
        self.assertEqual(wahler.cross_country_jump_penalties, 0.0)
        self.assertEqual(wahler.finishing_score, 29.4)
        nicolas = by_rider["Astier NICOLAS (FRA)"]
        self.assertEqual(nicolas.horse_name, "Alertamalib'Or")
        self.assertEqual(nicolas.dressage_score, 30.3)
        self.assertEqual(nicolas.cross_country_jump_penalties, 0.8)
        self.assertEqual(nicolas.finishing_score, 31.1)
        hoy = by_rider["Andrew HOY (AUS)"]
        self.assertEqual(hoy.horse_name, "Vassily de Lassos")
        self.assertEqual(hoy.dressage_score, 26.9)
        self.assertEqual(hoy.cross_country_jump_penalties, 4.8)
        self.assertEqual(hoy.finishing_score, 31.7)
        smith = by_rider["Tamra SMITH (USA)"]
        self.assertEqual(smith.horse_name, "Lillet 3")
        self.assertEqual(smith.dressage_score, 27.0)
        self.assertEqual(smith.cross_country_jump_penalties, 8.0)
        self.assertEqual(smith.finishing_score, 35.0)
        siegl = by_rider["Lea SIEGL (AUT)"]
        self.assertEqual(siegl.horse_name, "Watermill Giorgio RS")
        self.assertEqual(siegl.dressage_score, 29.2)
        self.assertEqual(siegl.cross_country_jump_penalties, 18.4)
        self.assertEqual(siegl.finishing_score, 47.6)

    def test_aachen_live_1600_saturday_records_after_xc_leaders_and_new_rt(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1600_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  4:00PM")
        self.assertEqual(parser.header_cells[0], "Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1600_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 9)
        self.assertNotIn("Francesco AONDIO BERTERO (ITA)", rider_names)
        self.assertNotIn("Paolo TORLONIA (ITA)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        jung = by_rider["Michael JUNG (GER)"]
        self.assertEqual(jung.horse_name, "fischerChipmunk FRH")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(jung.cross_country_jump_penalties, 0.0)
        self.assertEqual(jung.finishing_score, 23.0)
        canter = by_rider["Rosalind CANTER (GBR)"]
        self.assertEqual(canter.horse_name, "Lordships Graffalo")
        self.assertEqual(canter.dressage_score, 23.4)
        self.assertEqual(canter.cross_country_jump_penalties, 0.0)
        self.assertEqual(canter.finishing_score, 23.4)
        collett = by_rider["Laura COLLETT (GBR)"]
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(collett.cross_country_jump_penalties, 0.8)
        self.assertEqual(collett.finishing_score, 23.6)
        maksud = by_rider["Gaspard MAKSUD (FRA)"]
        self.assertEqual(maksud.horse_name, "Zaragoza")
        self.assertEqual(maksud.dressage_score, 29.3)
        self.assertEqual(maksud.cross_country_jump_penalties, 1.6)
        self.assertEqual(maksud.finishing_score, 30.9)
        vogg = by_rider["Felix VOGG (SUI)"]
        self.assertEqual(vogg.horse_name, "Frieda")
        self.assertEqual(vogg.dressage_score, 29.3)
        self.assertEqual(vogg.cross_country_jump_penalties, 5.2)
        self.assertEqual(vogg.finishing_score, 34.5)
        touzaint = by_rider["Nicolas TOUZAINT (FRA)"]
        self.assertEqual(touzaint.horse_name, "Diabolo Menthe")
        self.assertEqual(touzaint.dressage_score, 26.7)
        self.assertEqual(touzaint.cross_country_jump_penalties, 21.4)
        self.assertEqual(touzaint.finishing_score, 48.1)

    def test_aachen_live_1659_saturday_keeps_after_xc_field_before_jumping(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1659_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  4:59PM")
        self.assertEqual(parser.header_cells[0], "Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1659_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 9)
        self.assertNotIn("Francesco AONDIO BERTERO (ITA)", rider_names)
        self.assertNotIn("Paolo TORLONIA (ITA)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        jung = by_rider["Michael JUNG (GER)"]
        self.assertEqual(jung.horse_name, "fischerChipmunk FRH")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(jung.show_jumping_penalties, 0.0)
        self.assertEqual(jung.cross_country_jump_penalties, 0.0)
        self.assertEqual(jung.finishing_score, 23.0)
        canter = by_rider["Rosalind CANTER (GBR)"]
        self.assertEqual(canter.horse_name, "Lordships Graffalo")
        self.assertEqual(canter.dressage_score, 23.4)
        self.assertEqual(canter.show_jumping_penalties, 0.0)
        self.assertEqual(canter.finishing_score, 23.4)
        collett = by_rider["Laura COLLETT (GBR)"]
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(collett.cross_country_jump_penalties, 0.8)
        self.assertEqual(collett.show_jumping_penalties, 0.0)
        self.assertEqual(collett.finishing_score, 23.6)
        maksud = by_rider["Gaspard MAKSUD (FRA)"]
        self.assertEqual(maksud.horse_name, "Zaragoza")
        self.assertEqual(maksud.dressage_score, 29.3)
        self.assertEqual(maksud.cross_country_jump_penalties, 1.6)
        self.assertEqual(maksud.finishing_score, 30.9)
        vogg = by_rider["Felix VOGG (SUI)"]
        self.assertEqual(vogg.horse_name, "Frieda")
        self.assertEqual(vogg.dressage_score, 29.3)
        self.assertEqual(vogg.cross_country_jump_penalties, 5.2)
        self.assertEqual(vogg.finishing_score, 34.5)
        touzaint = by_rider["Nicolas TOUZAINT (FRA)"]
        self.assertEqual(touzaint.horse_name, "Diabolo Menthe")
        self.assertEqual(touzaint.dressage_score, 26.7)
        self.assertEqual(touzaint.cross_country_jump_penalties, 21.4)
        self.assertEqual(touzaint.finishing_score, 48.1)
        self.assertTrue(all(result.show_jumping_penalties == 0.0 for result in results))

    def test_aachen_live_1933_saturday_skips_wdbsj_withdrawals_before_jumping(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1933_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  7:33PM")
        self.assertEqual(parser.header_cells[0], "Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1933_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 6)
        self.assertNotIn("Kento NAGURA (JPN)", rider_names)
        self.assertNotIn("Ryuzo KITAJIMA (JPN)", rider_names)
        self.assertNotIn("Francesco AONDIO BERTERO (ITA)", rider_names)
        self.assertNotIn("Paolo TORLONIA (ITA)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        jung = by_rider["Michael JUNG (GER)"]
        self.assertEqual(jung.horse_name, "fischerChipmunk FRH")
        self.assertEqual(jung.dressage_score, 23.0)
        self.assertEqual(jung.show_jumping_penalties, 0.0)
        self.assertEqual(jung.cross_country_jump_penalties, 0.0)
        self.assertEqual(jung.finishing_score, 23.0)
        canter = by_rider["Rosalind CANTER (GBR)"]
        self.assertEqual(canter.horse_name, "Lordships Graffalo")
        self.assertEqual(canter.finishing_score, 23.4)
        collett = by_rider["Laura COLLETT (GBR)"]
        self.assertEqual(collett.cross_country_jump_penalties, 0.8)
        self.assertEqual(collett.finishing_score, 23.6)
        maksud = by_rider["Gaspard MAKSUD (FRA)"]
        self.assertEqual(maksud.cross_country_jump_penalties, 1.6)
        self.assertEqual(maksud.finishing_score, 30.9)
        vogg = by_rider["Felix VOGG (SUI)"]
        self.assertEqual(vogg.cross_country_jump_penalties, 5.2)
        self.assertEqual(vogg.finishing_score, 34.5)
        touzaint = by_rider["Nicolas TOUZAINT (FRA)"]
        self.assertEqual(touzaint.cross_country_jump_penalties, 21.4)
        self.assertEqual(touzaint.finishing_score, 48.1)
        self.assertTrue(all(result.show_jumping_penalties == 0.0 for result in results))

    def test_aachen_live_1354_saturday_records_krajewski_xc_and_new_el(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1354_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  1:54PM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1354_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 12)
        self.assertNotIn("Oliver BARRETT (AUS)", rider_names)
        self.assertNotIn("Nadja MINDER (SUI)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        collett = by_rider["Laura COLLETT (GBR)"]
        self.assertEqual(collett.horse_name, "London 52")
        self.assertEqual(collett.dressage_score, 22.8)
        self.assertEqual(collett.cross_country_jump_penalties, 0.0)
        self.assertEqual(collett.finishing_score, 22.8)
        mcewen = by_rider["Tom MCEWEN (GBR)"]
        self.assertEqual(mcewen.horse_name, "JL Dublin")
        self.assertEqual(mcewen.dressage_score, 26.6)
        self.assertEqual(mcewen.cross_country_jump_penalties, 2.0)
        self.assertEqual(mcewen.finishing_score, 28.6)
        maksud = by_rider["Gaspard MAKSUD (FRA)"]
        self.assertEqual(maksud.horse_name, "Zaragoza")
        self.assertEqual(maksud.dressage_score, 29.3)
        self.assertEqual(maksud.cross_country_jump_penalties, 1.6)
        self.assertEqual(maksud.finishing_score, 30.9)
        johner = by_rider["Mélody JOHNER (SUI)"]
        self.assertEqual(johner.horse_name, "Erin")
        self.assertEqual(johner.dressage_score, 31.5)
        self.assertEqual(johner.cross_country_jump_penalties, 0.0)
        self.assertEqual(johner.finishing_score, 31.5)
        donckers = by_rider["Karin DONCKERS (BEL)"]
        self.assertEqual(donckers.horse_name, "Leipheimer van't Verahof")
        self.assertEqual(donckers.dressage_score, 31.7)
        self.assertEqual(donckers.cross_country_jump_penalties, 0.0)
        self.assertEqual(donckers.finishing_score, 31.7)
        spencer = by_rider["Monica SPENCER (NZL)"]
        self.assertEqual(spencer.horse_name, "Artist")
        self.assertEqual(spencer.dressage_score, 28.9)
        self.assertEqual(spencer.cross_country_jump_penalties, 4.8)
        self.assertEqual(spencer.finishing_score, 33.7)
        krajewski = by_rider["Julia KRAJEWSKI (GER)"]
        self.assertEqual(krajewski.horse_name, "Uelzener's Nickel")
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(krajewski.cross_country_jump_penalties, 13.6)
        self.assertEqual(krajewski.cross_country_time_penalties, 0.0)
        self.assertEqual(krajewski.finishing_score, 35.6)
        giessen = by_rider["Jillian GIESSEN (NED)"]
        self.assertEqual(giessen.horse_name, "Seattle Park")
        self.assertEqual(giessen.dressage_score, 33.9)
        self.assertEqual(giessen.cross_country_jump_penalties, 18.0)
        self.assertEqual(giessen.finishing_score, 51.9)
        phoenix = by_rider["Jessica PHOENIX (CAN)"]
        self.assertEqual(phoenix.horse_name, "Fluorescent Adolescent")
        self.assertEqual(phoenix.dressage_score, 35.1)
        self.assertEqual(phoenix.cross_country_jump_penalties, 12.0)
        self.assertEqual(phoenix.finishing_score, 47.1)
        benitez = by_rider["Esteban BENITEZ VALLE (ESP)"]
        self.assertEqual(benitez.horse_name, "Utrera AA 35 1")
        self.assertEqual(benitez.dressage_score, 33.3)
        self.assertEqual(benitez.cross_country_jump_penalties, 50.0)
        self.assertEqual(benitez.finishing_score, 83.3)

    def test_aachen_live_1304_saturday_records_mcewen_lead_and_new_el_xc(self):
        parser = _LeaderboardParser()
        parser.feed(AACHEN_LIVE_1304_SATURDAY_HTML)
        self.assertEqual(parser.last_update, "Aug 15 2026  1:04PM")
        self.assertEqual(parser.header_cells[0], "Start TimeCross/ Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
            event_name="Aachen · CH-M-C",
            level="CH-M-C",
            event_date=date(2026, 8, 11),
            country="GER",
        )
        results = parse_leaderboard_results(AACHEN_LIVE_1304_SATURDAY_HTML, board=board)
        rider_names = [result.rider_name for result in results]
        self.assertEqual(len(results), 9)
        self.assertNotIn("Peter T. FLARUP (DEN)", rider_names)
        self.assertNotIn("Joanna PAWLAK (POL)", rider_names)
        self.assertNotIn("Paolo TORLONIA (ITA)", rider_names)
        self.assertNotIn("Weerapat PITAKANONDA (THA)", rider_names)
        by_rider = {result.rider_name: result for result in results}
        krajewski = by_rider["Julia KRAJEWSKI (GER)"]
        self.assertEqual(krajewski.dressage_score, 22.0)
        self.assertEqual(krajewski.finishing_score, 22.0)
        self.assertEqual(krajewski.cross_country_jump_penalties, 0.0)
        self.assertEqual(krajewski.cross_country_time_penalties, 0.0)
        mcewen = by_rider["Tom MCEWEN (GBR)"]
        self.assertEqual(mcewen.horse_name, "JL Dublin")
        self.assertEqual(mcewen.dressage_score, 26.6)
        self.assertEqual(mcewen.cross_country_jump_penalties, 2.0)
        self.assertEqual(mcewen.cross_country_time_penalties, 0.0)
        self.assertEqual(mcewen.finishing_score, 28.6)
        spencer = by_rider["Monica SPENCER (NZL)"]
        self.assertEqual(spencer.horse_name, "Artist")
        self.assertEqual(spencer.dressage_score, 28.9)
        self.assertEqual(spencer.cross_country_jump_penalties, 0.0)
        self.assertEqual(spencer.finishing_score, 28.9)
        johner = by_rider["Mélody JOHNER (SUI)"]
        self.assertEqual(johner.horse_name, "Erin")
        self.assertEqual(johner.dressage_score, 31.5)
        self.assertEqual(johner.cross_country_jump_penalties, 0.0)
        self.assertEqual(johner.finishing_score, 31.5)
        hansen = by_rider["Malin HANSEN-HOTOPP (GER)"]
        self.assertEqual(hansen.horse_name, "Carlitos Quidditch K")
        self.assertEqual(hansen.dressage_score, 28.6)
        self.assertEqual(hansen.cross_country_jump_penalties, 3.2)
        self.assertEqual(hansen.finishing_score, 31.8)
        clark = by_rider["Aoife CLARK (IRL)"]
        self.assertEqual(clark.horse_name, "Full Monty de Lacense")
        self.assertEqual(clark.dressage_score, 31.5)
        self.assertEqual(clark.cross_country_jump_penalties, 1.2)
        self.assertEqual(clark.finishing_score, 32.7)
        goury = by_rider["Alexis GOURY (FRA)"]
        self.assertEqual(goury.horse_name, "Je'Vall")
        self.assertEqual(goury.dressage_score, 28.5)
        self.assertEqual(goury.cross_country_jump_penalties, 6.4)
        self.assertEqual(goury.finishing_score, 34.9)
        phoenix = by_rider["Jessica PHOENIX (CAN)"]
        self.assertEqual(phoenix.horse_name, "Fluorescent Adolescent")
        self.assertEqual(phoenix.dressage_score, 35.1)
        self.assertEqual(phoenix.cross_country_jump_penalties, 12.0)
        self.assertEqual(phoenix.finishing_score, 47.1)
        benitez = by_rider["Esteban BENITEZ VALLE (ESP)"]
        self.assertEqual(benitez.horse_name, "Utrera AA 35 1")
        self.assertEqual(benitez.dressage_score, 33.3)
        self.assertEqual(benitez.cross_country_jump_penalties, 59.0)
        self.assertEqual(benitez.finishing_score, 92.3)

    def test_hambach_boards_cover_three_august_classes(self):
        boards = hambach_aug_2026_boards()
        self.assertEqual(len(boards), 3)
        self.assertEqual(
            [board.level for board in boards],
            ["CCI3*-S", "CCI2*-S", "CCI1*-Intro"],
        )
        self.assertTrue(all(board.event_date == date(2026, 8, 21) for board in boards))
        self.assertTrue(all(board.country == "GER" for board in boards))

    def test_hambach_dressage_scores_are_parsed(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/hambach/leaderboard01.html",
            event_name="Hambach · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 8, 21),
            country="GER",
        )
        results = parse_leaderboard_results(HAMBACH_DRESSAGE_HTML, board=board)
        self.assertEqual(len(results), 2)
        leader, second = results
        self.assertEqual(leader.rider_name, "Anna SIEMER (GER)")
        self.assertEqual(leader.horse_name, "Grazia K")
        self.assertEqual(leader.dressage_score, 30.8)
        self.assertEqual(leader.finishing_score, 30.8)
        self.assertEqual(leader.event_name, "Hambach · CCI3*-S")
        self.assertEqual(second.rider_name, "Hanne HENNING (GER)")
        self.assertEqual(second.horse_name, "Sicherlich Wilde Hilde")
        self.assertEqual(second.dressage_score, 31.6)

    def test_hambach_horse_names_starting_with_el_are_not_treated_as_eliminations(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/hambach/leaderboard01.html",
            event_name="Hambach · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 8, 21),
            country="GER",
        )
        results = parse_leaderboard_results(HAMBACH_ELIOPE_HTML, board=board)
        self.assertEqual(len(results), 1)
        eliope = results[0]
        self.assertEqual(eliope.rider_name, "Anna SIEMER (GER)")
        self.assertEqual(eliope.horse_name, "Eliope")
        self.assertEqual(eliope.dressage_score, 31.9)
        self.assertEqual(eliope.finishing_score, 31.9)

    def test_hambach_cci3_716pm_after_xc_rank_header(self):
        parser = _LeaderboardParser()
        parser.feed(HAMBACH_CCI3_AFTER_XC_716PM_HTML)
        self.assertEqual(parser.last_update, "Aug 22 2026  7:16PM")
        self.assertEqual(parser.header_cells[0], "Rank")
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/hambach/leaderboard01.html",
            event_name="Hambach · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 8, 21),
            country="GER",
        )
        results = parse_leaderboard_results(HAMBACH_CCI3_AFTER_XC_716PM_HTML, board=board)
        self.assertEqual(len(results), 5)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.horse_name, "La Duma")
        self.assertEqual(leader.rider_name, "Sabrina MERTENS (GER)")
        self.assertEqual(leader.dressage_score, 28.2)
        self.assertEqual(leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(leader.cross_country_time_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 28.2)
        ready = by_horse["Ready To Go Nrw"]
        self.assertEqual(ready.finishing_score, 30.4)
        diamar = by_horse["Diamar 2"]
        self.assertEqual(diamar.dressage_score, 28.8)
        self.assertEqual(diamar.cross_country_jump_penalties, 23.8)
        self.assertEqual(diamar.cross_country_time_penalties, 0.0)
        self.assertEqual(diamar.finishing_score, 52.6)
        kiss = by_horse["Kiss Me"]
        self.assertEqual(kiss.rider_name, "Anna SIEMER (GER)")
        self.assertEqual(kiss.dressage_score, 24.8)
        self.assertEqual(kiss.cross_country_jump_penalties, 42.8)
        self.assertEqual(kiss.cross_country_time_penalties, 0.0)
        self.assertEqual(kiss.finishing_score, 67.6)
        shakira = by_horse["Shakira"]
        self.assertEqual(shakira.cross_country_jump_penalties, 106.0)
        self.assertEqual(shakira.finishing_score, 131.8)

    def test_hambach_intro_start_list_without_dressage_yields_no_scored_rows(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/hambach/leaderboard03.html",
            event_name="Hambach · CCI1*-Intro",
            level="CCI1*-Intro",
            event_date=date(2026, 8, 21),
            country="GER",
        )
        results = parse_leaderboard_results(HAMBACH_INTRO_START_LIST_HTML, board=board)
        self.assertEqual(results, [])

    def test_segersjo_boards_cover_three_august_classes(self):
        boards = segersjo_aug_2026_boards()
        self.assertEqual(len(boards), 3)
        self.assertEqual(
            [board.level for board in boards],
            ["CCI3*-S", "CH-EU-J-CCI2*-L", "CH-EU-Y-CCI3*-L"],
        )
        self.assertEqual(
            [board.url.rsplit("/", 1)[-1] for board in boards],
            ["leaderboard01.html", "leaderboard11.html", "leaderboard61.html"],
        )
        self.assertTrue(all(board.event_date == date(2026, 8, 26) for board in boards))
        self.assertTrue(all(board.country == "SWE" for board in boards))

    def test_segersjo_start_list_without_dressage_yields_no_scored_rows(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard01.html",
            event_name="Segersjö · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(SEGERSJO_START_LIST_HTML, board=board)
        self.assertEqual(results, [])

    def test_segersjo_junior_dressage_scores_are_parsed(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard11.html",
            event_name="Segersjö · CH-EU-J-CCI2*-L",
            level="CH-EU-J-CCI2*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(SEGERSJO_JUNIOR_DRESSAGE_HTML, board=board)
        self.assertEqual(len(results), 2)
        leader, second = results
        self.assertEqual(leader.rider_name, "Eline DE RIDDER (BEL)")
        self.assertEqual(leader.horse_name, "Mandorior")
        self.assertEqual(leader.dressage_score, 31.2)
        self.assertEqual(leader.finishing_score, 31.2)
        self.assertEqual(leader.level, "CH-EU-J-CCI2*-L")
        self.assertEqual(leader.country, "SWE")
        self.assertEqual(second.rider_name, "Tova MADER (SWE)")
        self.assertEqual(second.horse_name, "TJA Morning Star")
        self.assertEqual(second.dressage_score, 33.3)
        self.assertEqual(second.finishing_score, 33.3)

    def test_segersjo_junior_mid_session_scores_include_revised_dressage(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard11.html",
            event_name="Segersjö · CH-EU-J-CCI2*-L",
            level="CH-EU-J-CCI2*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_JUNIOR_DRESSAGE_MID_SESSION_HTML,
            board=board,
        )
        self.assertEqual(len(results), 3)
        leader, second, mandorior = results
        self.assertEqual(leader.rider_name, "Milla STAADE (GER)")
        self.assertEqual(leader.horse_name, "Christ William")
        self.assertEqual(leader.dressage_score, 29.1)
        self.assertEqual(leader.finishing_score, 29.1)
        self.assertEqual(second.rider_name, "Arabella HENDERSON (GBR)")
        self.assertEqual(second.horse_name, "Ex Cavalier's Law")
        self.assertEqual(second.dressage_score, 30.1)
        self.assertEqual(mandorior.rider_name, "Eline DE RIDDER (BEL)")
        self.assertEqual(mandorior.horse_name, "Mandorior")
        self.assertEqual(mandorior.dressage_score, 32.4)
        self.assertEqual(mandorior.finishing_score, 32.4)

    def test_segersjo_junior_later_session_scores_keep_leader_and_revise_mandorior(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard11.html",
            event_name="Segersjö · CH-EU-J-CCI2*-L",
            level="CH-EU-J-CCI2*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_JUNIOR_DRESSAGE_LATER_SESSION_HTML,
            board=board,
        )
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Milla STAADE (GER)")
        self.assertEqual(leader.horse_name, "Christ William")
        self.assertEqual(leader.dressage_score, 29.1)
        self.assertEqual(leader.finishing_score, 29.1)
        self.assertEqual(by_horse["Ex Cavalier's Law"].dressage_score, 30.1)
        self.assertEqual(by_horse["Chantilly 38"].rider_name, "Jona Isabell HEINE (GER)")
        self.assertEqual(by_horse["Chantilly 38"].dressage_score, 31.7)
        self.assertEqual(by_horse["Mandorior"].rider_name, "Eline DE RIDDER (BEL)")
        self.assertEqual(by_horse["Mandorior"].dressage_score, 32.1)
        self.assertEqual(by_horse["Mandorior"].finishing_score, 32.1)
        self.assertNotIn("Gaiete d'Agenais", by_horse)

    def test_segersjo_junior_late_morning_scores_promote_new_leader(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard11.html",
            event_name="Segersjö · CH-EU-J-CCI2*-L",
            level="CH-EU-J-CCI2*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_JUNIOR_DRESSAGE_LATE_MORNING_HTML,
            board=board,
        )
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Annabel RIDGWAY (GBR)")
        self.assertEqual(leader.horse_name, "Emerald Katie")
        self.assertEqual(leader.dressage_score, 27.9)
        self.assertEqual(leader.finishing_score, 27.9)
        self.assertEqual(by_horse["Christ William"].dressage_score, 29.1)
        self.assertEqual(by_horse["Allnightparty"].rider_name, "Lukas Wilhelm SÜHLING (GER)")
        self.assertEqual(by_horse["Allnightparty"].dressage_score, 28.0)
        self.assertEqual(by_horse["Gaiete d'Agenais"].rider_name, "Tifaniie VILLETON (FRA)")
        self.assertEqual(by_horse["Gaiete d'Agenais"].dressage_score, 30.2)
        self.assertNotIn("CSF Hi Spec", by_horse)

    def test_segersjo_junior_midday_scores_promote_allnightparty_and_complete_first_half(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard11.html",
            event_name="Segersjö · CH-EU-J-CCI2*-L",
            level="CH-EU-J-CCI2*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_JUNIOR_DRESSAGE_MIDDAY_HTML,
            board=board,
        )
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Lukas Wilhelm SÜHLING (GER)")
        self.assertEqual(leader.horse_name, "Allnightparty")
        self.assertEqual(leader.dressage_score, 27.5)
        self.assertEqual(leader.finishing_score, 27.5)
        self.assertEqual(by_horse["Emerald Katie"].rider_name, "Annabel RIDGWAY (GBR)")
        self.assertEqual(by_horse["Emerald Katie"].dressage_score, 27.9)
        self.assertEqual(by_horse["Christ William"].dressage_score, 29.1)
        self.assertEqual(by_horse["CSF Hi Spec"].rider_name, "Camille Lasse WEISS (SUI)")
        self.assertEqual(by_horse["CSF Hi Spec"].dressage_score, 39.1)
        self.assertNotIn("Duvibis Mister", by_horse)

    def test_segersjo_yr_opening_dressage_scores_are_parsed(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
            event_name="Segersjö · CH-EU-Y-CCI3*-L",
            level="CH-EU-Y-CCI3*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_YR_DRESSAGE_OPENING_HTML,
            board=board,
        )
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Jago JACKSON (GBR)")
        self.assertEqual(leader.horse_name, "Kinda Brunette")
        self.assertEqual(leader.dressage_score, 31.6)
        self.assertEqual(leader.finishing_score, 31.6)
        self.assertEqual(by_horse["Quincy VDB"].rider_name, "Lander VAN DEN BROECK (BEL)")
        self.assertEqual(by_horse["Quincy VDB"].dressage_score, 32.0)
        self.assertEqual(by_horse["Calypso"].rider_name, "Silva KELLY (GER)")
        self.assertEqual(by_horse["Calypso"].dressage_score, 32.2)
        self.assertEqual(by_horse["Finsceal Endeavour"].rider_name, "Amelia MCCARTHY (IRL)")
        self.assertEqual(by_horse["Finsceal Endeavour"].dressage_score, 47.2)
        self.assertNotIn("La Diva", by_horse)

    def test_segersjo_yr_midafternoon_scores_promote_dexter_and_score_la_diva(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
            event_name="Segersjö · CH-EU-Y-CCI3*-L",
            level="CH-EU-Y-CCI3*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_YR_DRESSAGE_MIDAFTERNOON_HTML,
            board=board,
        )
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Jeanne BRUNEL (FRA)")
        self.assertEqual(leader.horse_name, "Dexter Z")
        self.assertEqual(leader.dressage_score, 30.9)
        self.assertEqual(leader.finishing_score, 30.9)
        self.assertEqual(by_horse["La Diva"].rider_name, "Liv Noe HARTMANN (GER)")
        self.assertEqual(by_horse["La Diva"].dressage_score, 31.4)
        self.assertEqual(by_horse["Kinda Brunette"].rider_name, "Jago JACKSON (GBR)")
        self.assertEqual(by_horse["Kinda Brunette"].dressage_score, 31.6)
        self.assertEqual(by_horse["Ashwood Iron Lady"].rider_name, "Ciara O'CONNOR (IRL)")
        self.assertEqual(by_horse["Ashwood Iron Lady"].dressage_score, 32.7)
        self.assertNotIn("DSP Descansado", by_horse)

    def test_segersjo_yr_late_afternoon_scores_promote_descansado(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
            event_name="Segersjö · CH-EU-Y-CCI3*-L",
            level="CH-EU-Y-CCI3*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_YR_DRESSAGE_LATE_AFTERNOON_HTML,
            board=board,
        )
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Carl VOIGT (GER)")
        self.assertEqual(leader.horse_name, "DSP Descansado")
        self.assertEqual(leader.dressage_score, 23.6)
        self.assertEqual(leader.finishing_score, 23.6)
        self.assertEqual(by_horse["Elixir de Sienne"].rider_name, "Aline TEILLARD (FRA)")
        self.assertEqual(by_horse["Elixir de Sienne"].dressage_score, 28.3)
        self.assertEqual(by_horse["Stillbrook Aoife"].rider_name, "Molly O'CONNOR (IRL)")
        self.assertEqual(by_horse["Stillbrook Aoife"].dressage_score, 30.3)
        self.assertEqual(by_horse["Dexter Z"].rider_name, "Jeanne BRUNEL (FRA)")
        self.assertEqual(by_horse["Dexter Z"].dressage_score, 30.9)
        self.assertNotIn("Rohan van het Avenhof", by_horse)

    def test_segersjo_yr_early_evening_scores_insert_barratt_and_el_sovski(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
            event_name="Segersjö · CH-EU-Y-CCI3*-L",
            level="CH-EU-Y-CCI3*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_YR_DRESSAGE_EARLY_EVENING_HTML,
            board=board,
        )
        self.assertEqual(len(results), 5)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Carl VOIGT (GER)")
        self.assertEqual(leader.horse_name, "DSP Descansado")
        self.assertEqual(leader.dressage_score, 23.6)
        self.assertEqual(leader.finishing_score, 23.6)
        self.assertEqual(by_horse["Ride For Thais Chaman Dumontceau"].rider_name, "Elizabeth BARRATT (GBR)")
        self.assertEqual(by_horse["Ride For Thais Chaman Dumontceau"].dressage_score, 24.8)
        self.assertEqual(by_horse["El Sovski"].rider_name, "Filip STRZYZEWSKI (POL)")
        self.assertEqual(by_horse["El Sovski"].dressage_score, 27.8)
        self.assertEqual(by_horse["Elixir de Sienne"].rider_name, "Aline TEILLARD (FRA)")
        self.assertEqual(by_horse["Elixir de Sienne"].dressage_score, 28.8)
        self.assertEqual(by_horse["Königsblauer"].rider_name, "Ella KRUEGER (GER)")
        self.assertEqual(by_horse["Königsblauer"].dressage_score, 29.1)
        self.assertNotIn("Agatha Raisin", by_horse)

    def test_segersjo_yr_evening_scores_insert_hjoptimus_and_skip_withdrawn_agatha(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
            event_name="Segersjö · CH-EU-Y-CCI3*-L",
            level="CH-EU-Y-CCI3*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_YR_DRESSAGE_EVENING_HTML,
            board=board,
        )
        self.assertEqual(len(results), 5)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Carl VOIGT (GER)")
        self.assertEqual(leader.horse_name, "DSP Descansado")
        self.assertEqual(leader.dressage_score, 23.6)
        self.assertEqual(leader.finishing_score, 23.6)
        self.assertEqual(by_horse["Hjoptimus"].rider_name, "Mathies RÜDER (GER)")
        self.assertEqual(by_horse["Hjoptimus"].dressage_score, 23.7)
        self.assertEqual(by_horse["Ride For Thais Chaman Dumontceau"].rider_name, "Elizabeth BARRATT (GBR)")
        self.assertEqual(by_horse["Ride For Thais Chaman Dumontceau"].dressage_score, 24.8)
        self.assertEqual(by_horse["Juna R"].rider_name, "Eleonora FAVA (ITA)")
        self.assertEqual(by_horse["Juna R"].dressage_score, 29.0)
        self.assertEqual(by_horse["This Ones On You"].rider_name, "Joshua LEVETT (GBR)")
        self.assertEqual(by_horse["This Ones On You"].dressage_score, 30.9)
        self.assertNotIn("Agatha Raisin", by_horse)

    def test_segersjo_yr_late_evening_scores_revise_stroke_of_genius(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
            event_name="Segersjö · CH-EU-Y-CCI3*-L",
            level="CH-EU-Y-CCI3*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(
            SEGERSJO_YR_DRESSAGE_LATE_EVENING_HTML,
            board=board,
        )
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Carl VOIGT (GER)")
        self.assertEqual(leader.horse_name, "DSP Descansado")
        self.assertEqual(leader.dressage_score, 23.6)
        self.assertEqual(leader.finishing_score, 23.6)
        self.assertEqual(by_horse["Hjoptimus"].rider_name, "Mathies RÜDER (GER)")
        self.assertEqual(by_horse["Hjoptimus"].dressage_score, 23.7)
        self.assertEqual(by_horse["Ride For Thais Chaman Dumontceau"].rider_name, "Elizabeth BARRATT (GBR)")
        self.assertEqual(by_horse["Ride For Thais Chaman Dumontceau"].dressage_score, 24.8)
        self.assertEqual(by_horse["Stroke Of Genius"].rider_name, "Anna NANGLE (IRL)")
        self.assertEqual(by_horse["Stroke Of Genius"].dressage_score, 38.5)
        self.assertEqual(by_horse["Stroke Of Genius"].finishing_score, 38.5)
        self.assertNotIn("Agatha Raisin", by_horse)

    def test_segersjo_cci3_saturday_xc_skips_eliminations_and_keeps_mid_round(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard01.html",
            event_name="Segersjö · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(SEGERSJO_CCI3_SATURDAY_XC_HTML, board=board)
        self.assertEqual(len(results), 4)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.rider_name, "Niklas LINDBÄCK (SWE)")
        self.assertEqual(leader.horse_name, "A Star Is Born Vuo")
        self.assertEqual(leader.dressage_score, 34.1)
        self.assertEqual(leader.cross_country_jump_penalties, 0.0)
        self.assertEqual(leader.finishing_score, 34.1)
        mid_round = by_horse["Condor Da Carma"]
        self.assertEqual(mid_round.rider_name, "Martina ANDERSSON (SWE)")
        self.assertEqual(mid_round.cross_country_jump_penalties, 0.0)
        self.assertEqual(mid_round.cross_country_time_penalties, 0.0)
        self.assertEqual(mid_round.finishing_score, 35.7)
        crottys = by_horse["Crottys Rock"]
        self.assertEqual(crottys.rider_name, "Anna NILSSON (SWE)")
        self.assertEqual(crottys.dressage_score, 33.7)
        self.assertEqual(crottys.cross_country_jump_penalties, 5.6)
        self.assertEqual(crottys.cross_country_time_penalties, 0.0)
        self.assertEqual(crottys.finishing_score, 39.3)
        canela = by_horse["Canela"]
        self.assertEqual(canela.rider_name, "Jenny GLEBENIUS (SWE)")
        self.assertEqual(canela.cross_country_jump_penalties, 0.0)
        self.assertEqual(canela.finishing_score, 40.7)
        self.assertNotIn("Flanders", by_horse)

    def test_segersjo_yr_juna_r_xc_correction_is_parsed(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
            event_name="Segersjö · CH-EU-Y-CCI3*-L",
            level="CH-EU-Y-CCI3*-L",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(SEGERSJO_YR_JUNA_R_XC_CORRECTION_HTML, board=board)
        self.assertEqual(len(results), 3)
        by_horse = {result.horse_name: result for result in results}
        self.assertEqual(by_horse["DSP Descansado"].finishing_score, 23.6)
        calypso = by_horse["Calypso"]
        self.assertEqual(calypso.rider_name, "Silva KELLY (GER)")
        self.assertEqual(calypso.dressage_score, 32.2)
        self.assertEqual(calypso.cross_country_jump_penalties, 18.4)
        self.assertEqual(calypso.finishing_score, 50.6)
        juna = by_horse["Juna R"]
        self.assertEqual(juna.rider_name, "Eleonora FAVA (ITA)")
        self.assertEqual(juna.dressage_score, 29.0)
        self.assertEqual(juna.cross_country_jump_penalties, 51.2)
        self.assertEqual(juna.cross_country_time_penalties, 0.0)
        self.assertEqual(juna.finishing_score, 80.2)

    def test_segersjo_cci3_sunday_sj_complete_promotes_zixten_and_skips_el_sj(self):
        board = RechenstelleBoard(
            url="https://live.rechenstelle.de/2026/segersjo/leaderboard01.html",
            event_name="Segersjö · CCI3*-S",
            level="CCI3*-S",
            event_date=date(2026, 8, 26),
            country="SWE",
        )
        results = parse_leaderboard_results(SEGERSJO_CCI3_SUNDAY_SJ_COMPLETE_HTML, board=board)
        self.assertEqual(len(results), 3)
        by_horse = {result.horse_name: result for result in results}
        leader = results[0]
        self.assertEqual(leader.horse_name, "Zixten af Tollstad")
        self.assertEqual(leader.rider_name, "Katrin NORLING (SWE)")
        self.assertEqual(leader.dressage_score, 34.4)
        self.assertEqual(leader.show_jumping_penalties, 0.0)
        self.assertEqual(leader.cross_country_jump_penalties, 4.0)
        self.assertEqual(leader.finishing_score, 38.4)
        star = by_horse["A Star Is Born Vuo"]
        self.assertEqual(star.rider_name, "Niklas LINDBÄCK (SWE)")
        self.assertEqual(star.dressage_score, 34.1)
        self.assertEqual(star.show_jumping_penalties, 4.0)
        self.assertEqual(star.cross_country_jump_penalties, 1.2)
        self.assertEqual(star.finishing_score, 39.3)
        canela = by_horse["Canela"]
        self.assertEqual(canela.rider_name, "Jenny GLEBENIUS (SWE)")
        self.assertEqual(canela.show_jumping_penalties, 0.0)
        self.assertEqual(canela.finishing_score, 40.7)
        self.assertNotIn("Joli Harlem LVST", by_horse)


if __name__ == "__main__":
    unittest.main()
