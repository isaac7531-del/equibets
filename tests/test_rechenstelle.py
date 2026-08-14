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


if __name__ == "__main__":
    unittest.main()
