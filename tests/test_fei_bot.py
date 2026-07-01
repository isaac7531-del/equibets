import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from equibets.fei_bot import (
    CALENDAR_SEARCH_URL,
    HORSE_SEARCH_URL,
    PERSON_SEARCH_URL,
    FeiDataBot,
    FeiEvent,
    FeiResultStore,
    FeiVerifier,
    extract_form_fields,
    parse_calendar_events,
    parse_eventing_results,
    parse_result_links,
)


EVENT_URL = urljoin(CALENDAR_SEARCH_URL, "/Calendar/EventDetail.aspx?event=abc")
RESULT_URL = urljoin(CALENDAR_SEARCH_URL, "/Calendar/Results.aspx?event=abc")


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.requests = []

    def get(self, url):
        self.requests.append(("GET", url, None))
        return self.pages[("GET", url)]

    def post(self, url, data):
        self.requests.append(("POST", url, dict(data)))
        return self.pages[("POST", url)]


class FeiBotTests(unittest.TestCase):
    def test_extract_form_fields_preserves_aspnet_state(self):
        html = """
        <form>
          <input type="hidden" name="__VIEWSTATE" value="state-value" />
          <input type="text" name="ctl00$Main$DateStart" />
          <select name="ctl00$Main$Discipline">
            <option value="">-</option>
            <option value="3" selected>Eventing</option>
          </select>
        </form>
        """

        fields = extract_form_fields(html)

        self.assertEqual(fields["__VIEWSTATE"], "state-value")
        self.assertEqual(fields["ctl00$Main$DateStart"], "")
        self.assertEqual(fields["ctl00$Main$Discipline"], "3")

    def test_parse_calendar_events_discovers_event_detail_links(self):
        events = parse_calendar_events(calendar_results_html())

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Badminton Horse Trials")
        self.assertEqual(events[0].url, EVENT_URL)
        self.assertEqual(events[0].country, "GBR")
        self.assertEqual(events[0].level, "CCI5*-L")

    def test_parse_calendar_events_prefers_event_detail_over_show_detail(self):
        events = parse_calendar_events(calendar_results_with_show_and_event_links())

        self.assertEqual(len(events), 2)
        self.assertTrue(all("EventDetail.aspx" in event.url for event in events))
        self.assertFalse(any("ShowDetail.aspx" in event.url for event in events))
        self.assertEqual(events[0].name, "Strzegom Horse Trials")
        self.assertEqual(events[0].level, "CCI4*-L")
        self.assertEqual(events[1].level, "CCI3*-L")

    def test_parse_result_links_finds_result_pages_from_event_detail(self):
        links = parse_result_links(event_detail_html(), EVENT_URL)

        self.assertEqual(links, [RESULT_URL])

    def test_parse_eventing_results_normalizes_phase_scores(self):
        event = FeiEvent(
            source_event_id="abc",
            name="Badminton Horse Trials",
            url=EVENT_URL,
            start_date=datetime(2026, 5, 1).date(),
            country="GBR",
            level="CCI5*-L",
        )

        results = parse_eventing_results(
            result_page_html(),
            event,
            RESULT_URL,
            datetime(2026, 5, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].rider_name, "Alex Rider")
        self.assertEqual(results[0].horse_name, "Pocket Rocket")
        self.assertEqual(results[0].finishing_score, 35.8)
        self.assertEqual(results[0].source_id, "data_fei")

    def test_parse_live_fei_result_headers(self):
        event = FeiEvent(
            source_event_id="abc",
            name="Quillota",
            url=EVENT_URL,
            start_date=datetime(2025, 12, 18).date(),
            country="CHI",
            level="CCI3*-S",
        )

        results = parse_eventing_results(
            live_result_page_html(),
            event,
            RESULT_URL,
            datetime(2026, 5, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].dressage_score, 37.6)
        self.assertEqual(results[0].show_jumping_penalties, 8.0)
        self.assertEqual(results[0].show_jumping_time_penalties, 0.0)
        self.assertEqual(results[0].cross_country_jump_penalties, 0.0)
        self.assertEqual(results[0].cross_country_time_penalties, 10.0)
        self.assertEqual(results[0].finishing_score, 55.6)
        self.assertEqual(results[0].rider_fei_id, "10000001")
        self.assertEqual(results[0].horse_fei_id, "107BH10")
        self.assertEqual(results[0].placing, "2")
        self.assertEqual(results[0].source_url, RESULT_URL)
        self.assertEqual(results[1].status, "eliminated")
        self.assertEqual(results[1].horse_fei_id, "107BH17")

    def test_bot_submits_calendar_opens_event_and_result_pages(self):
        client = FakeClient(
            {
                ("GET", CALENDAR_SEARCH_URL): calendar_search_form_html(),
                ("POST", CALENDAR_SEARCH_URL): calendar_results_html(),
                ("GET", EVENT_URL): event_detail_html(),
                ("GET", RESULT_URL): result_page_html(),
            }
        )
        bot = FeiDataBot(client)

        results, summary = bot.collect(
            start_date=datetime(2026, 5, 1).date(),
            end_date=datetime(2026, 5, 5).date(),
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(summary.events_found, 1)
        self.assertEqual(summary.result_pages_opened, 2)
        post_data = client.requests[1][2]
        self.assertEqual(post_data["ctl00$Main$DateStart"], "01/05/2026")
        self.assertEqual(post_data["ctl00$Main$DateEnd"], "05/05/2026")
        self.assertEqual(post_data["ctl00$Main$Discipline"], "Eventing")

    def test_verifier_checks_person_and_horse_search_pages(self):
        client = FakeClient(
            {
                ("GET", PERSON_SEARCH_URL): search_form_html(),
                ("POST", PERSON_SEARCH_URL): "<table><tr><td>Alex Rider</td></tr></table>",
                ("GET", HORSE_SEARCH_URL): search_form_html(),
                ("POST", HORSE_SEARCH_URL): "<table><tr><td>Pocket Rocket</td></tr></table>",
            }
        )
        verifier = FeiVerifier(client)

        self.assertTrue(verifier.verify_person("Alex Rider"))
        self.assertTrue(verifier.verify_horse("Pocket Rocket"))

    def test_result_store_merges_and_writes_json(self):
        event = FeiEvent(
            source_event_id="abc",
            name="Badminton Horse Trials",
            url=EVENT_URL,
            start_date=datetime(2026, 5, 1).date(),
            country="GBR",
            level="CCI5*-L",
        )
        result = parse_eventing_results(
            result_page_html(),
            event,
            RESULT_URL,
            datetime(2026, 5, 2, tzinfo=timezone.utc),
        )[0]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fei_results.json"
            store = FeiResultStore(path)
            merged = store.merge([result])
            store.save(merged)

            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["source_id"], "data_fei")
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["rider_name"], "Alex Rider")
        self.assertEqual(payload["results"][0]["dressage_score"], 30.2)
        self.assertEqual(payload["results"][0]["source_url"], RESULT_URL)


def calendar_search_form_html():
    return """
    <form>
      <input type="hidden" name="__VIEWSTATE" value="state-value" />
      <input type="text" name="ctl00$Main$DateStart" />
      <input type="text" name="ctl00$Main$DateEnd" />
      <input type="text" name="ctl00$Main$Discipline" />
      <input type="submit" name="ctl00$Main$SearchButton" value="Search" />
    </form>
    """


def calendar_results_html():
    return f"""
    <table>
      <tr>
        <th>Date</th>
        <th>Show Name</th>
        <th>Country</th>
        <th>Discipline</th>
        <th>Level</th>
      </tr>
      <tr>
        <td>2026-05-01</td>
        <td><a href="/Calendar/EventDetail.aspx?event=abc">Badminton Horse Trials</a></td>
        <td>GBR</td>
        <td>Eventing</td>
        <td>CCI5*-L</td>
      </tr>
    </table>
    """


def calendar_results_with_show_and_event_links():
    return """
    <table>
      <tr>
        <th>Date</th>
        <th>Show Name</th>
        <th>Country</th>
        <th>Events</th>
      </tr>
      <tr>
        <td>2026-06-26</td>
        <td><a href="/Calendar/ShowDetail.aspx?p=show">Strzegom Horse Trials</a></td>
        <td>POL</td>
        <td>
          <a href="/Calendar/EventDetail.aspx?p=cci4">CCI4*-L</a>
          <a href="/Calendar/EventDetail.aspx?p=cci3">CCI3*-L</a>
        </td>
      </tr>
    </table>
    """


def event_detail_html():
    return """
    <html>
      <body>
        <a href="/Calendar/Results.aspx?event=abc">Results</a>
      </body>
    </html>
    """


def result_page_html():
    return """
    <table>
      <tr>
        <th>Athlete</th>
        <th>Horse</th>
        <th>Dressage</th>
        <th>Show Jumping</th>
        <th>XC Jump</th>
        <th>XC Time</th>
        <th>Country</th>
        <th>Level</th>
      </tr>
      <tr>
        <td>Alex Rider</td>
        <td>Pocket Rocket</td>
        <td>30.2</td>
        <td>4.0</td>
        <td>0.0</td>
        <td>1.6</td>
        <td>GBR</td>
        <td>CCI5*-L</td>
      </tr>
    </table>
    """


def live_result_page_html():
    return """
    <table>
      <tr>
        <th>Pos</th>
        <th>FEI ID</th>
        <th>Athlete</th>
        <th>FEI ID</th>
        <th>Horse</th>
        <th>Studbook</th>
        <th>MER</th>
        <th>D</th>
        <th>XC Obs</th>
        <th>XC Tim</th>
        <th>J Obs</th>
        <th>J Tim</th>
        <th>Prize Money</th>
        <th>Score</th>
      </tr>
      <tr>
        <td>2</td>
        <td>10000001</td>
        <td>Juan CANALES ZENTENO (CHI)</td>
        <td>107BH10</td>
        <td>TINQUILCO</td>
        <td></td>
        <td></td>
        <td>37.6</td>
        <td>0</td>
        <td>10</td>
        <td>8</td>
        <td>0</td>
        <td></td>
        <td>55.6</td>
      </tr>
      <tr>
        <td>EL</td>
        <td>10000002</td>
        <td>Eliminated Rider</td>
        <td>107BH17</td>
        <td>ALL RED</td>
        <td></td>
        <td></td>
        <td>43.2</td>
        <td>0</td>
        <td>19.2</td>
        <td></td>
        <td></td>
        <td></td>
        <td>2nd HI</td>
      </tr>
    </table>
    """


def search_form_html():
    return """
    <form>
      <input type="hidden" name="__VIEWSTATE" value="state-value" />
      <input type="text" name="ctl00$Main$Name" />
      <input type="submit" name="ctl00$Main$SearchButton" value="Search" />
    </form>
    """


if __name__ == "__main__":
    unittest.main()
