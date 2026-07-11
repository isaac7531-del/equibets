"""Refresh result data for events that are happening now."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from .compliance import DATA_FILE as COMPLIANCE_FILE
from .compliance import require_source_approval
from .events import DEFAULT_UPCOMING_EVENTS_FILE, UpcomingEvent, UpcomingEventStore
from .fei_bot import (
    DEFAULT_RESULTS_FILE,
    FeiBrowserClient,
    FeiCrawlSummary,
    FeiDataBot,
    FeiEvent,
    FeiHttpClient,
    FeiResultStore,
    FeiVerifier,
    _build_client,
    _date_arg,
    _env_value,
    _key_values,
)
from .results import EventingResult


@dataclass(frozen=True)
class CurrentEventRefreshSummary:
    """Counts reported by the current-event refresh."""

    upcoming_events_considered: int
    active_events_found: int
    search_events_found: int
    events_opened: int
    result_pages_opened: int
    results_collected: int
    results_verified: int
    results_rejected: int


def active_events(events: Sequence[UpcomingEvent], on_date: date) -> list[UpcomingEvent]:
    """Return FEI calendar events whose date range includes ``on_date``."""

    return [
        event
        for event in events
        if event.source_id == "data_fei" and event.start_date <= on_date <= (event.end_date or event.start_date)
    ]


def collect_current_event_results(
    client: FeiHttpClient | FeiBrowserClient,
    *,
    upcoming_events: Sequence[UpcomingEvent],
    on_date: date,
    form_fields: Mapping[str, str] | None = None,
    max_events: int | None = None,
    raw_dir: Path | str | None = None,
    search_past_days: int = 3,
    verifier: FeiVerifier | None = None,
    verify: str = "none",
) -> tuple[list[EventingResult], CurrentEventRefreshSummary]:
    """Collect FEI results for active events and recent result searches."""

    bot = FeiDataBot(client, verifier=verifier, raw_dir=raw_dir)
    active_fei_events = [_from_upcoming_event(event) for event in active_events(upcoming_events, on_date)]
    search_events: list[FeiEvent] = []
    if search_past_days > 0:
        search_start = on_date - timedelta(days=search_past_days - 1)
        search_events = bot.search_calendar(
            start_date=search_start,
            end_date=on_date,
            form_fields=form_fields,
            result_status="With results",
        )

    events_to_open = _dedupe_events([*active_fei_events, *search_events])
    results, crawl_summary = bot.collect_events(events_to_open, max_events=max_events, verify=verify)
    return results, _summary(
        upcoming_events_considered=len(upcoming_events),
        active_events_found=len(active_fei_events),
        search_events_found=len(search_events),
        crawl_summary=crawl_summary,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh FEI results for events happening now")
    parser.add_argument("--current-date", type=_date_arg, default=date.today(), help="Date to treat as today, YYYY-MM-DD")
    parser.add_argument(
        "--upcoming-events",
        type=Path,
        default=DEFAULT_UPCOMING_EVENTS_FILE,
        help="Normalized upcoming event JSON store",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS_FILE, help="JSON result store path")
    parser.add_argument(
        "--search-past-days",
        type=int,
        default=3,
        help="Calendar result-search window ending on current date; use 0 to skip search",
    )
    parser.add_argument("--form-field", action="append", default=[], help="Extra FEI search form value as name=value")
    parser.add_argument("--raw-dir", type=Path, help="Optional directory for raw FEI HTML responses")
    parser.add_argument("--max-events", type=int, help="Maximum current/search events to open")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Delay between FEI requests in seconds")
    parser.add_argument("--driver", choices=("auto", "browser", "http"), default="auto", help="FEI page driver")
    parser.add_argument("--headful", action="store_true", help="Show the browser window for manual login/debugging")
    parser.add_argument("--browser-executable", help="Chrome/Chromium executable for the browser driver")
    parser.add_argument("--storage-state", type=Path, help="Persist Playwright cookies/session state")
    parser.add_argument("--challenge-wait", type=float, default=10.0, help="Seconds to wait for FEI JS challenges")
    parser.add_argument("--cookie", help="FEI session cookie header")
    parser.add_argument("--cookie-env", default="FEI_COOKIE", help="Environment variable containing FEI cookie")
    parser.add_argument("--compliance-policy", type=Path, default=COMPLIANCE_FILE, help="Source compliance policy JSON")
    parser.add_argument("--verify", choices=("none", "warn", "require"), default="none")
    parser.add_argument("--dry-run", action="store_true", help="Collect and summarize without writing output")
    args = parser.parse_args(argv)

    require_source_approval("data_fei", "results", path=args.compliance_policy)
    upcoming_events = UpcomingEventStore(args.upcoming_events).load()
    cookie = args.cookie or _env_value(args.cookie_env)
    client = _build_client(args, cookie)
    verifier = FeiVerifier(client) if args.verify != "none" else None

    try:
        results, summary = collect_current_event_results(
            client,
            upcoming_events=upcoming_events,
            on_date=args.current_date,
            form_fields=_key_values(args.form_field),
            max_events=args.max_events,
            raw_dir=args.raw_dir,
            search_past_days=args.search_past_days,
            verifier=verifier,
            verify=args.verify,
        )
    finally:
        if hasattr(client, "close"):
            client.close()

    if not args.dry_run:
        store = FeiResultStore(args.output)
        merged = store.merge(results)
        store.save(merged)
        written = len(merged)
    else:
        written = 0

    print(
        "Current event result refresh complete: "
        f"upcoming_events_considered={summary.upcoming_events_considered}, "
        f"active_events_found={summary.active_events_found}, "
        f"search_events_found={summary.search_events_found}, "
        f"events_opened={summary.events_opened}, "
        f"result_pages_opened={summary.result_pages_opened}, "
        f"results_collected={summary.results_collected}, "
        f"results_verified={summary.results_verified}, "
        f"results_rejected={summary.results_rejected}, "
        f"results_in_store={written}"
    )
    return 0


def _from_upcoming_event(event: UpcomingEvent) -> FeiEvent:
    return FeiEvent(
        source_event_id=event.source_event_id,
        name=event.name,
        url=event.source_url,
        start_date=event.start_date,
        end_date=event.end_date,
        country=event.country,
        discipline=event.discipline,
        level=event.level,
    )


def _dedupe_events(events: Sequence[FeiEvent]) -> list[FeiEvent]:
    selected: dict[str, FeiEvent] = {}
    for event in events:
        selected.setdefault(event.url, event)
    return list(selected.values())


def _summary(
    *,
    upcoming_events_considered: int,
    active_events_found: int,
    search_events_found: int,
    crawl_summary: FeiCrawlSummary,
) -> CurrentEventRefreshSummary:
    return CurrentEventRefreshSummary(
        upcoming_events_considered=upcoming_events_considered,
        active_events_found=active_events_found,
        search_events_found=search_events_found,
        events_opened=crawl_summary.events_opened,
        result_pages_opened=crawl_summary.result_pages_opened,
        results_collected=crawl_summary.results_collected,
        results_verified=crawl_summary.results_verified,
        results_rejected=crawl_summary.results_rejected,
    )


if __name__ == "__main__":
    raise SystemExit(main())
