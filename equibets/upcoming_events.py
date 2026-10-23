"""Collect upcoming public eventing calendar events."""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .compliance import DATA_FILE as COMPLIANCE_FILE
from .compliance import require_source_approval
from .events import DEFAULT_UPCOMING_EVENTS_FILE, UpcomingEvent, UpcomingEventStore
from .fei_bot import (
    FeiBrowserClient,
    FeiDataBot,
    FeiEvent,
    FeiHttpClient,
)


def collect_fei_upcoming_events(
    client: FeiHttpClient | FeiBrowserClient,
    *,
    start_date: date,
    end_date: date,
    form_fields: Mapping[str, str] | None = None,
) -> list[UpcomingEvent]:
    """Collect upcoming FEI calendar rows without opening result pages."""

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    bot = FeiDataBot(client)
    events = bot.search_calendar(
        start_date=start_date,
        end_date=end_date,
        form_fields=form_fields,
        result_status=None,
    )
    return [_from_fei_event(event, collected_at) for event in events if event.start_date]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect upcoming eventing calendar events")
    parser.add_argument("--start-date", type=_date_arg, help="Calendar start date, YYYY-MM-DD")
    parser.add_argument("--end-date", type=_date_arg, help="Calendar end date, YYYY-MM-DD")
    parser.add_argument("--days-ahead", type=int, default=120, help="Days ahead to collect when end date is omitted")
    parser.add_argument("--form-field", action="append", default=[], help="Extra FEI search form value as name=value")
    parser.add_argument("--output", type=Path, default=DEFAULT_UPCOMING_EVENTS_FILE, help="JSON event store path")
    parser.add_argument("--driver", choices=("browser", "http"), default="browser", help="FEI page driver")
    parser.add_argument("--headful", action="store_true", help="Show the browser window for manual login/debugging")
    parser.add_argument("--storage-state", type=Path, help="Persist Playwright cookies/session state")
    parser.add_argument("--cookie", help="FEI session cookie header")
    parser.add_argument("--cookie-env", default="FEI_COOKIE", help="Environment variable containing FEI cookie")
    parser.add_argument("--compliance-policy", type=Path, default=COMPLIANCE_FILE, help="Source compliance policy JSON")
    parser.add_argument("--dry-run", action="store_true", help="Collect and summarize without writing output")
    args = parser.parse_args(argv)

    start_date = args.start_date or date.today()
    end_date = args.end_date or start_date + timedelta(days=args.days_ahead)
    require_source_approval("data_fei", "calendar", path=args.compliance_policy)
    cookie = args.cookie or os.environ.get(args.cookie_env)
    client = _build_client(args, cookie)

    try:
        events = collect_fei_upcoming_events(
            client,
            start_date=start_date,
            end_date=end_date,
            form_fields=_key_values(args.form_field),
        )
    finally:
        if hasattr(client, "close"):
            client.close()

    if not args.dry_run:
        store = UpcomingEventStore(args.output)
        merged = store.merge(events)
        store.save(merged)
        written = len(merged)
    else:
        written = 0

    print(
        "Upcoming event refresh complete: "
        f"events_collected={len(events)}, "
        f"events_in_store={written}, "
        f"window={start_date.isoformat()}..{end_date.isoformat()}"
    )
    return 0


def _from_fei_event(event: FeiEvent, collected_at: datetime) -> UpcomingEvent:
    return UpcomingEvent(
        source_id="data_fei",
        source_event_id=event.source_event_id,
        source_priority=0,
        name=event.name,
        start_date=event.start_date or collected_at.date(),
        end_date=event.end_date,
        country=event.country or "Unknown",
        discipline=event.discipline or "Eventing",
        level=event.level or "Unknown",
        source_url=event.url,
        collected_at=collected_at,
    )


def _build_client(args: argparse.Namespace, cookie: str | None) -> FeiHttpClient | FeiBrowserClient:
    if args.driver == "http":
        return FeiHttpClient(cookie=cookie)
    return FeiBrowserClient(
        cookie=cookie,
        headless=not args.headful,
        storage_state=args.storage_state,
    )


def _key_values(items: Sequence[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"Expected name=value form field, got {item!r}")
        key, value = item.split("=", 1)
        values[key] = value
    return values


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


if __name__ == "__main__":
    raise SystemExit(main())
