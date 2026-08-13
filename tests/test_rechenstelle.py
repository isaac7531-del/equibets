"""Tests for Rechenstelle live leaderboard parsing."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timezone

from equibets.rechenstelle import RechenstelleBoard, parse_leaderboard_results


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


if __name__ == "__main__":
    unittest.main()
