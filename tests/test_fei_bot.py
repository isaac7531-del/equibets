import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urljoin

from equibets.fei_bot import (
    CALENDAR_SEARCH_URL,
    FeiFormUnavailable,
    HORSE_SEARCH_URL,
    PERSON_SEARCH_URL,
    FeiBrowserClient,
    FeiDataBot,
    FeiEvent,
    FeiResultStore,
    FeiVerifier,
    extract_form_fields,
    main,
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


class FailingVerifier:
    def verify_person(self, name):
        raise RuntimeError("verification search form unavailable")

    def verify_horse(self, name):
        raise RuntimeError("verification search form unavailable")


class FakePastShowsLocator:
    @property
    def first(self):
        return self

    def count(self):
        return 1

    def click(self, timeout):
        raise RuntimeError("click failed")


class FakePastShowsPage:
    url = CALENDAR_SEARCH_URL

    def __init__(self):
        self.evaluate_scripts = []
        self.load_state_waits = []
        self.timeout_waits = []
        self._content = "<html><form></form></html>"

    def locator(self, selector):
        return FakePastShowsLocator()

    def evaluate(self, script):
        self.evaluate_scripts.append(script)
        self._content = calendar_results_html()
        return True

    def wait_for_function(self, script, timeout):
        raise RuntimeError("not selected")

    def wait_for_load_state(self, state, timeout):
        self.load_state_waits.append((state, timeout))

    def wait_for_timeout(self, milliseconds):
        self.timeout_waits.append(milliseconds)

    def content(self):
        return self._content


class NavigatingPastShowsPage(FakePastShowsPage):
    def __init__(self):
        super().__init__()
        self.content_calls = 0

    def content(self):
        self.content_calls += 1
        if self.content_calls == 1:
            raise RuntimeError(
                "Page.content: Unable to retrieve content because the page is navigating and changing the content"
            )
        return super().content()


class FakePastShowsClient(FeiBrowserClient):
    def __init__(self, page):
        self.page = page

    def _ensure_page(self):
        return self.page

    def _wait_after_action(self):
        pass

    def _wait_ready(self):
        pass


class ChallengeCalendarBrowserClient(FeiBrowserClient):
    def __init__(self):
        self.posts = []

    def get(self, url):
        return "<html><title>DataDome</title><body>captcha</body></html>"

    def post(self, url, data, field_intents=()):
        self.posts.append((url, dict(data), field_intents))
        return calendar_results_html()

    def open_past_shows(self):
        raise AssertionError("calendar results should parse without opening past shows")


class FakeFieldElement:
    def __init__(self, info):
        self.info = info

    def evaluate(self, script):
        return self.info


class FakeFieldsLocator:
    def __init__(self, infos):
        self.infos = infos

    def count(self):
        return len(self.infos)

    def nth(self, index):
        return FakeFieldElement(self.infos[index])


class FakeTokenPage:
    def __init__(self, infos):
        self.infos = infos

    def locator(self, selector):
        self.selector = selector
        return FakeFieldsLocator(self.infos)


class TokenFillBrowserClient(FeiBrowserClient):
    def __init__(self, page):
        self.page = page
        self.filled = []

    def _ensure_page(self):
        return self.page

    def _fill_form_field(self, name, value):
        self.filled.append((name, value))
        return True


class UnavailableFormClient:
    def __init__(self):
        self.closed = False
        self.discarded_storage_state = False

    def get(self, url):
        raise FeiFormUnavailable("calendar form unavailable")

    def discard_storage_state_on_close(self):
        self.discarded_storage_state = True

    def close(self):
        self.closed = True


class BlankChallengeLocator:
    def __init__(self, page):
        self.page = page

    def inner_text(self, timeout):
        self.page.inner_text_timeouts.append(timeout)
        return ""


class BlankChallengePage:
    url = CALENDAR_SEARCH_URL

    def __init__(self, clock):
        self.clock = clock
        self.waits = []
        self.inner_text_timeouts = []

    def wait_for_load_state(self, state, timeout):
        self.load_state_timeout = timeout

    def locator(self, selector):
        return BlankChallengeLocator(self)

    def title(self):
        return "fei.org"

    def wait_for_timeout(self, milliseconds):
        self.waits.append(milliseconds)
        self.clock[0] += milliseconds / 1000


class BlankChallengeBrowserClient(FeiBrowserClient):
    def __init__(self, page):
        self.page = page
        self.challenge_wait_seconds = 10.0

    def _ensure_page(self):
        return self.page


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

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].dressage_score, 37.6)
        self.assertEqual(results[0].show_jumping_penalties, 8.0)
        self.assertEqual(results[0].cross_country_jump_penalties, 0.0)
        self.assertEqual(results[0].cross_country_time_penalties, 10.0)
        self.assertEqual(results[0].finishing_score, 55.6)

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

    def test_verify_warn_keeps_results_when_verification_lookup_fails(self):
        client = FakeClient(
            {
                ("GET", CALENDAR_SEARCH_URL): calendar_search_form_html(),
                ("POST", CALENDAR_SEARCH_URL): calendar_results_html(),
                ("GET", EVENT_URL): event_detail_html(),
                ("GET", RESULT_URL): result_page_html(),
            }
        )
        bot = FeiDataBot(client, verifier=FailingVerifier())

        results, summary = bot.collect(
            start_date=datetime(2026, 5, 1).date(),
            end_date=datetime(2026, 5, 5).date(),
            verify="warn",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(summary.results_collected, 1)
        self.assertEqual(summary.results_verified, 0)

    def test_open_past_shows_fallback_submits_postback_form(self):
        page = FakePastShowsPage()
        client = FakePastShowsClient(page)

        html = client.open_past_shows()

        self.assertIn("Badminton Horse Trials", html)
        self.assertEqual(len(page.evaluate_scripts), 1)
        fallback_script = page.evaluate_scripts[0]
        self.assertIn('setHidden("__EVENTTARGET", target)', fallback_script)
        self.assertIn('setHidden("__EVENTARGUMENT", argument)', fallback_script)
        self.assertIn("form.submit()", fallback_script)
        self.assertNotIn("typeof __doPostBack", fallback_script)

    def test_open_past_shows_retries_content_during_navigation(self):
        page = NavigatingPastShowsPage()
        client = FakePastShowsClient(page)

        html = client.open_past_shows()

        self.assertIn("Badminton Horse Trials", html)
        self.assertGreaterEqual(page.content_calls, 2)
        self.assertIn(("domcontentloaded", 10_000), page.load_state_waits)
        self.assertIn(("networkidle", 10_000), page.load_state_waits)
        self.assertIn(500, page.timeout_waits)

    def test_browser_calendar_search_passes_field_intents_after_challenge_page(self):
        client = ChallengeCalendarBrowserClient()
        bot = FeiDataBot(client)

        events = bot.search_calendar(
            start_date=datetime(2026, 6, 22).date(),
            end_date=datetime(2026, 7, 1).date(),
        )

        self.assertEqual(len(events), 1)
        post_url, post_data, field_intents = client.posts[0]
        self.assertEqual(post_url, CALENDAR_SEARCH_URL)
        self.assertEqual(post_data, {})
        self.assertIn(((("date", "start"), ("date", "from")), "22/06/2026"), field_intents)
        self.assertIn(((("date", "end"), ("date", "to")), "01/07/2026"), field_intents)
        self.assertIn(((("discipline",),), "Eventing"), field_intents)

    def test_browser_field_intent_matches_live_form_control_by_alternative_tokens(self):
        page = FakeTokenPage(
            [
                {
                    "name": "__VIEWSTATE",
                    "id": "__VIEWSTATE",
                    "type": "hidden",
                    "tag": "input",
                    "disabled": False,
                    "label": "",
                    "placeholder": "",
                    "aria": "",
                },
                {
                    "name": "ctl00$PlaceHolderMain$DateFrom",
                    "id": "PlaceHolderMain_DateFrom",
                    "type": "text",
                    "tag": "input",
                    "disabled": False,
                    "label": "Date from",
                    "placeholder": "dd/MM/yyyy",
                    "aria": "",
                },
            ]
        )
        client = TokenFillBrowserClient(page)

        matched = client._fill_first_matching_form_field((("date", "start"), ("date", "from")), "22/06/2026")

        self.assertTrue(matched)
        self.assertEqual(client.filled, [("ctl00$PlaceHolderMain$DateFrom", "22/06/2026")])

    def test_wait_ready_caps_blank_chrome_challenge_wait(self):
        clock = [1000.0]
        page = BlankChallengePage(clock)
        client = BlankChallengeBrowserClient(page)

        with patch("equibets.fei_bot.time.monotonic", side_effect=lambda: clock[0]):
            client._wait_ready()

        self.assertEqual(page.load_state_timeout, 10_000)
        self.assertEqual(sum(page.waits), 2000)
        self.assertEqual(page.inner_text_timeouts, [1000, 1000, 1000])

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

    def test_main_live_output_falls_back_to_existing_store_when_form_unavailable(self):
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
            output = Path(tmp) / "fei_results.json"
            live_output = Path(tmp) / "live_scores.json"
            compliance_policy = Path(tmp) / "source_compliance.json"
            compliance_policy.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "sources": [
                            {
                                "source_id": "data_fei",
                                "display_name": "FEI Database",
                                "base_url": "https://data.fei.org/",
                                "robots_url": "https://data.fei.org/robots.txt",
                                "terms_url": "https://inside.fei.org/fei/terms-and-conditions",
                                "approved_for_ingest": True,
                                "raw_storage_allowed": True,
                                "allowed_job_types": ["results"],
                                "reviewed_at": "2026-07-01T00:00:00Z",
                                "reviewed_by": "test",
                                "notes": "Approved only for this CLI fallback test.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            FeiResultStore(output).save([result])
            client = UnavailableFormClient()

            with patch("equibets.fei_bot._build_client", return_value=client):
                exit_code = main(
                    [
                        "--current-events",
                        "--start-date",
                        "2026-05-01",
                        "--end-date",
                        "2026-05-05",
                        "--output",
                        str(output),
                        "--live-output",
                        str(live_output),
                        "--compliance-policy",
                        str(compliance_policy),
                    ]
                )

            payload = json.loads(live_output.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(client.closed)
        self.assertTrue(client.discarded_storage_state)
        self.assertEqual(payload["event_count"], 1)
        self.assertEqual(payload["result_count"], 1)


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
