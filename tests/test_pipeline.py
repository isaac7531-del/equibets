import unittest
from datetime import date, datetime, timezone

from equibets.fei_bot import FeiEvent
from equibets.pipeline import FeiEventingPipeline, previous_12_month_window
from equibets.results import EventingResult


class FakeBot:
    def __init__(self):
        self.form_fields = None

    def search_calendar(self, *, start_date, end_date, form_fields=None):
        self.form_fields = form_fields
        return [
            FeiEvent(
                source_event_id="event-1",
                name="Badminton Horse Trials",
                url="https://data.fei.org/Calendar/EventDetail.aspx?event=1",
                start_date=start_date,
                end_date=end_date,
                country="GBR",
                level="CCI5*-L",
                venue="Badminton",
            )
        ]

    def collect_event(self, event, *, collected_at):
        return [
            EventingResult(
                source_id="data_fei",
                source_record_id="result-1",
                source_priority=0,
                rider_name="Alex Rider",
                horse_name="Pocket Rocket",
                event_name=event.name,
                event_date=event.start_date,
                level=event.level,
                country=event.country,
                dressage_score=30.0,
                show_jumping_penalties=4.0,
                cross_country_jump_penalties=0.0,
                cross_country_time_penalties=1.2,
                collected_at=collected_at,
                rider_fei_id="1001",
                horse_fei_id="H100",
                source_url="https://data.fei.org/Result/ResultList.aspx?p=abc",
                event_url=event.url,
                venue=event.venue,
            )
        ], 1

    def collect_horse_history(self, **kwargs):
        return [], [], 1


class FakeStore:
    def __init__(self):
        self.events = []
        self.results = []
        self.predictions = []
        self.logs = []

    def initialize(self):
        pass

    def upsert_event(self, event):
        self.events.append(event)

    def upsert_class(self, event, level, result_page_url):
        return 1

    def upsert_result(self, result, *, event=None, class_id=None):
        self.results.append(result)

    def link_history(self, result, *, history_type):
        pass

    def upsert_prediction(self, evidence):
        self.predictions.append(evidence)

    def log(self, run_id, target_type, status, message="", target_url=""):
        self.logs.append((target_type, status, message, target_url))

    def commit(self):
        pass


class PipelineTests(unittest.TestCase):
    def test_previous_12_month_window_uses_today_as_end(self):
        start_date, end_date = previous_12_month_window(date(2026, 7, 1))

        self.assertEqual(start_date, date(2025, 7, 1))
        self.assertEqual(end_date, date(2026, 7, 1))

    def test_pipeline_passes_calendar_overrides_and_saves_prediction(self):
        bot = FakeBot()
        store = FakeStore()

        summary = FeiEventingPipeline(
            bot,
            store,
            form_fields={"ctl00$Main$ResultStatus": "With results"},
        ).run(start_date=date(2026, 5, 1), end_date=date(2026, 5, 5))

        self.assertEqual(bot.form_fields, {"ctl00$Main$ResultStatus": "With results"})
        self.assertEqual(summary.events_opened, 1)
        self.assertEqual(summary.combinations_saved, 1)
        self.assertEqual(summary.result_rows_saved, 1)
        self.assertEqual(len(store.results), 1)
        self.assertEqual(len(store.predictions), 1)
        self.assertEqual(store.logs[-1][1], "completed")


if __name__ == "__main__":
    unittest.main()
