"""Daily FEI Eventing collection pipeline."""

from __future__ import annotations

import argparse
import os
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from equibets.database import PostgresStore
from equibets.fei_bot import FeiBrowserClient, FeiDataBot, FeiEvent, FeiHttpClient, _build_client, _env_value, _key_values
from equibets.results import EventingResult, build_prediction_evidence, consolidate_results


@dataclass(frozen=True)
class PipelineSummary:
    run_id: str
    events_found: int
    events_opened: int
    combinations_saved: int
    result_rows_saved: int
    horse_histories_saved: int
    combination_histories_saved: int
    predictions_saved: int
    failures: int


class FeiEventingPipeline:
    """Orchestrates calendar crawl, horse-history enrichment, and predictions."""

    def __init__(
        self,
        bot: FeiDataBot,
        store: PostgresStore,
        *,
        form_fields: Mapping[str, str] | None = None,
    ) -> None:
        self.bot = bot
        self.store = store
        self.form_fields = form_fields

    def run(
        self,
        *,
        start_date: date,
        end_date: date,
        event_urls: Sequence[str] = (),
        max_events: int | None = None,
        max_history_pages: int | None = None,
    ) -> PipelineSummary:
        run_id = uuid.uuid4().hex
        self.store.initialize()
        collected_at = datetime.now(timezone.utc).replace(microsecond=0)
        failures = 0
        events = self._events(start_date, end_date, event_urls)
        if max_events is not None:
            events = events[:max_events]

        all_results: list[EventingResult] = []
        horse_history_count = 0
        combination_history_count = 0
        combinations_seen: set[tuple[str, str]] = set()
        history_targets_seen: set[tuple[str, str, str]] = set()

        for event in events:
            self.store.upsert_event(event)
            try:
                event_results, _ = self.bot.collect_event(event, collected_at=collected_at)
            except Exception as exc:
                failures += 1
                self.store.log(run_id, "event", "failed", str(exc), event.url)
                continue

            for result in consolidate_results(event_results):
                class_id = self.store.upsert_class(event, result.level, result.source_url)
                self.store.upsert_result(result, event=event, class_id=class_id)
                all_results.append(result)
                combinations_seen.add((result.rider_name, result.horse_name))

            for result in event_results:
                history_target = (result.horse_fei_id or result.horse_name, result.rider_fei_id or result.rider_name, result.rider_name)
                if history_target in history_targets_seen:
                    continue
                history_targets_seen.add(history_target)
                try:
                    horse_history, combination_history, _ = self.bot.collect_horse_history(
                        horse_name=result.horse_name,
                        horse_fei_id=result.horse_fei_id,
                        rider_name=result.rider_name,
                        collected_at=collected_at,
                        max_pages=max_history_pages,
                    )
                except Exception as exc:
                    failures += 1
                    self.store.log(run_id, "horse", "failed", str(exc), result.source_url)
                    continue

                for history_result in consolidate_results(horse_history):
                    self.store.upsert_result(history_result)
                    self.store.link_history(history_result, history_type="horse")
                    all_results.append(history_result)
                    combinations_seen.add((history_result.rider_name, history_result.horse_name))
                    horse_history_count += 1
                for history_result in consolidate_results(combination_history):
                    self.store.link_history(history_result, history_type="combination")
                    combination_history_count += 1

        predictions_saved = self._save_predictions(all_results)
        self.store.log(
            run_id,
            "pipeline",
            "completed",
            f"events={len(events)} results={len(all_results)} predictions={predictions_saved} failures={failures}",
        )
        self.store.commit()
        return PipelineSummary(
            run_id=run_id,
            events_found=len(events),
            events_opened=len(events),
            combinations_saved=len(combinations_seen),
            result_rows_saved=len(all_results),
            horse_histories_saved=horse_history_count,
            combination_histories_saved=combination_history_count,
            predictions_saved=predictions_saved,
            failures=failures,
        )

    def _events(self, start_date: date, end_date: date, event_urls: Sequence[str]) -> list[FeiEvent]:
        if event_urls:
            return [
                FeiEvent(
                    source_event_id=url.rsplit("=", 1)[-1] if "=" in url else uuid.uuid5(uuid.NAMESPACE_URL, url).hex[:16],
                    name=url.rsplit("/", 1)[-1] or url,
                    url=url,
                    start_date=start_date,
                    end_date=end_date,
                )
                for url in event_urls
            ]
        return self.bot.search_calendar(start_date=start_date, end_date=end_date, form_fields=self.form_fields)

    def _save_predictions(self, results: list[EventingResult]) -> int:
        saved = 0
        seen: set[tuple[str, str, str]] = set()
        for result in consolidate_results(results):
            key = (result.rider_name, result.horse_name, result.level)
            if key in seen:
                continue
            seen.add(key)
            try:
                evidence = build_prediction_evidence(results, result.rider_name, result.horse_name, target_level=result.level)
            except ValueError:
                continue
            self.store.upsert_prediction(evidence)
            saved += 1
        return saved


def previous_12_month_window(today: date | None = None) -> tuple[date, date]:
    end_date = today or date.today()
    return end_date - timedelta(days=365), end_date


def run_daily_pipeline(
    *,
    database_url: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    event_urls: Sequence[str] = (),
    max_events: int | None = None,
    max_history_pages: int | None = None,
    raw_dir: Path | None = None,
    client: FeiHttpClient | FeiBrowserClient | None = None,
    form_fields: Mapping[str, str] | None = None,
) -> PipelineSummary:
    start, end = previous_12_month_window()
    client = client or FeiHttpClient(cookie=os.environ.get("FEI_COOKIE"))
    bot = FeiDataBot(client, raw_dir=raw_dir)
    store = PostgresStore.connect(database_url)
    return FeiEventingPipeline(bot, store, form_fields=form_fields).run(
        start_date=start_date or start,
        end_date=end_date or end,
        event_urls=event_urls,
        max_events=max_events,
        max_history_pages=max_history_pages,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the daily FEI Eventing PostgreSQL pipeline")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--event-url", action="append", default=[])
    parser.add_argument("--max-events", type=int)
    parser.add_argument("--max-history-pages", type=int)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--rate-limit", type=float, default=1.0)
    parser.add_argument("--driver", choices=("auto", "browser", "http"), default="auto")
    parser.add_argument("--headful", action="store_true")
    parser.add_argument("--browser-executable")
    parser.add_argument("--storage-state", type=Path)
    parser.add_argument("--challenge-wait", type=float, default=10.0)
    parser.add_argument("--cookie")
    parser.add_argument("--cookie-env", default="FEI_COOKIE")
    parser.add_argument("--form-field", action="append", default=[])
    args = parser.parse_args(argv)
    if not args.database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")

    cookie = args.cookie or _env_value(args.cookie_env)
    client = _build_client(args, cookie)
    bot = FeiDataBot(client, raw_dir=args.raw_dir)
    form_fields = _key_values(args.form_field)
    try:
        summary = FeiEventingPipeline(bot, PostgresStore.connect(args.database_url), form_fields=form_fields).run(
            start_date=args.start_date or previous_12_month_window()[0],
            end_date=args.end_date or previous_12_month_window()[1],
            event_urls=args.event_url,
            max_events=args.max_events,
            max_history_pages=args.max_history_pages,
        )
    finally:
        if hasattr(client, "close"):
            client.close()
    print(
        "FEI daily pipeline complete: "
        f"run_id={summary.run_id}, events={summary.events_opened}, "
        f"combinations={summary.combinations_saved}, results={summary.result_rows_saved}, "
        f"horse_history={summary.horse_histories_saved}, "
        f"combination_history={summary.combination_histories_saved}, predictions={summary.predictions_saved}, "
        f"failures={summary.failures}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
