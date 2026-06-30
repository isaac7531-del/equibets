import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.events import UpcomingEvent, UpcomingEventStore, consolidate_upcoming_events
from equibets.upcoming_events import collect_fei_upcoming_events
from equibets.fei_bot import CALENDAR_SEARCH_URL


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


def upcoming(**overrides):
    values = {
        "source_id": "data_fei",
        "source_event_id": "fei-abc",
        "source_priority": 0,
        "name": "Badminton Horse Trials",
        "start_date": date(2026, 5, 1),
        "end_date": date(2026, 5, 5),
        "country": "GBR",
        "discipline": "Eventing",
        "level": "CCI5*-L",
        "source_url": "https://data.fei.org/Calendar/EventDetail.aspx?event=abc",
        "collected_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return UpcomingEvent(**values)


class UpcomingEventTests(unittest.TestCase):
    def test_consolidation_keeps_higher_priority_duplicate_event(self):
        national = upcoming(
            source_id="british_eventing",
            source_event_id="be-1",
            source_priority=20,
            collected_at=datetime(2026, 1, 3, tzinfo=timezone.utc),
        )
        fei = upcoming()

        consolidated = consolidate_upcoming_events([national, fei])

        self.assertEqual(len(consolidated), 1)
        self.assertEqual(consolidated[0].source_id, "data_fei")

    def test_store_merges_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "upcoming_events.json"
            store = UpcomingEventStore(path)
            merged = store.merge([upcoming()])
            store.save(merged)
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(payload["version"], 1)
        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["name"], "Badminton Horse Trials")

    def test_fei_upcoming_refresh_searches_calendar_without_result_status(self):
        client = FakeClient(
            {
                ("GET", CALENDAR_SEARCH_URL): calendar_search_form_html(),
                ("POST", CALENDAR_SEARCH_URL): calendar_results_html(),
            }
        )

        events = collect_fei_upcoming_events(
            client,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 31),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "Badminton Horse Trials")
        post_data = client.requests[1][2]
        self.assertEqual(post_data["ctl00$Main$DateStart"], "01/05/2026")
        self.assertEqual(post_data["ctl00$Main$DateEnd"], "31/05/2026")
        self.assertEqual(post_data["ctl00$Main$Discipline"], "Eventing")
        self.assertEqual(post_data["ctl00$Main$ResultStatus"], "")


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
    return """
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


if __name__ == "__main__":
    unittest.main()
