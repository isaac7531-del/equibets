import unittest
from datetime import date, datetime, timezone
from urllib.parse import urljoin

from equibets.current_events import active_events, collect_current_event_results
from equibets.events import UpcomingEvent
from equibets.fei_bot import CALENDAR_SEARCH_URL


EVENT_URL = urljoin(CALENDAR_SEARCH_URL, "/Calendar/EventDetail.aspx?event=abc")
SEARCH_EVENT_URL = urljoin(CALENDAR_SEARCH_URL, "/Calendar/EventDetail.aspx?event=search")
RESULT_URL = urljoin(CALENDAR_SEARCH_URL, "/Calendar/Results.aspx?event=abc")
SEARCH_RESULT_URL = urljoin(CALENDAR_SEARCH_URL, "/Calendar/Results.aspx?event=search")


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


class CurrentEventRefreshTests(unittest.TestCase):
    def test_active_events_selects_fei_events_in_date_range(self):
        events = [
            upcoming(
                name="In Progress",
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 12),
            ),
            upcoming(
                source_id="british_eventing",
                name="National Event",
                source_event_id="be-1",
                start_date=date(2026, 7, 10),
                end_date=date(2026, 7, 12),
            ),
            upcoming(
                name="Future Event",
                source_event_id="future",
                start_date=date(2026, 8, 1),
                end_date=date(2026, 8, 2),
            ),
        ]

        selected = active_events(events, date(2026, 7, 11))

        self.assertEqual([event.name for event in selected], ["In Progress"])

    def test_current_event_refresh_combines_active_events_and_recent_search_results(self):
        client = FakeClient(
            {
                ("GET", CALENDAR_SEARCH_URL): calendar_search_form_html(),
                ("POST", CALENDAR_SEARCH_URL): calendar_results_html(),
                ("GET", EVENT_URL): event_detail_html(RESULT_URL),
                ("GET", RESULT_URL): result_page_html("Alex Rider", "Pocket Rocket", "35.8"),
                ("GET", SEARCH_EVENT_URL): event_detail_html(SEARCH_RESULT_URL),
                ("GET", SEARCH_RESULT_URL): result_page_html("Mia Hughes", "Atlas Bay", "31.2"),
            }
        )

        results, summary = collect_current_event_results(
            client,
            upcoming_events=[upcoming()],
            on_date=date(2026, 7, 11),
            search_past_days=2,
        )

        self.assertEqual(summary.active_events_found, 1)
        self.assertEqual(summary.search_events_found, 1)
        self.assertEqual(summary.events_opened, 2)
        self.assertEqual(summary.results_collected, 2)
        self.assertEqual({result.event_name for result in results}, {"Badminton Horse Trials", "Aachen Live"})
        post_data = client.requests[1][2]
        self.assertEqual(post_data["ctl00$Main$DateStart"], "10/07/2026")
        self.assertEqual(post_data["ctl00$Main$DateEnd"], "11/07/2026")
        self.assertEqual(post_data["ctl00$Main$ResultStatus"], "With results")


def upcoming(**overrides):
    values = {
        "source_id": "data_fei",
        "source_event_id": "fei-abc",
        "source_priority": 0,
        "name": "Badminton Horse Trials",
        "start_date": date(2026, 7, 10),
        "end_date": date(2026, 7, 12),
        "country": "GBR",
        "discipline": "Eventing",
        "level": "CCI5*-L",
        "source_url": EVENT_URL,
        "collected_at": datetime(2026, 7, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return UpcomingEvent(**values)


def calendar_search_form_html():
    return """
    <form>
      <input type="hidden" name="__VIEWSTATE" value="state-value" />
      <input type="text" name="ctl00$Main$DateStart" />
      <input type="text" name="ctl00$Main$DateEnd" />
      <input type="text" name="ctl00$Main$Discipline" />
      <input type="text" name="ctl00$Main$ResultStatus" />
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
        <td>2026-07-11</td>
        <td><a href="{SEARCH_EVENT_URL}">Aachen Live</a></td>
        <td>GER</td>
        <td>Eventing</td>
        <td>CCI4*-S</td>
      </tr>
    </table>
    """


def event_detail_html(result_url):
    return f"""
    <html>
      <body>
        <a href="{result_url}">Results</a>
      </body>
    </html>
    """


def result_page_html(rider, horse, score):
    return f"""
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
        <td>{rider}</td>
        <td>{horse}</td>
        <td>{score}</td>
        <td>0</td>
        <td>0</td>
        <td>0</td>
        <td>GBR</td>
        <td>CCI5*-L</td>
      </tr>
    </table>
    """


if __name__ == "__main__":
    unittest.main()
