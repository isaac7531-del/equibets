"""Build and publish current-event live scoring feeds."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from equibets.fei_bot import (
    DEFAULT_RESULTS_FILE,
    FeiDataBot,
    FeiResultStore,
    FeiVerifier,
    _build_client,
    _date_arg,
    _env_value,
    _key_values,
)
from equibets.results import EventingResult, consolidate_results


DEFAULT_LIVE_SCORES_FILE = Path(__file__).resolve().parents[1] / "public" / "current_event_scores.json"
DEFAULT_LOOKBACK_DAYS = 4
DEFAULT_LOOKAHEAD_DAYS = 1


def current_event_window(
    today: date | None = None,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    lookahead_days: int = DEFAULT_LOOKAHEAD_DAYS,
) -> tuple[date, date]:
    """Return the date window used for current multi-day event refreshes."""

    if lookback_days < 0:
        raise ValueError("lookback_days must be non-negative")
    if lookahead_days < 0:
        raise ValueError("lookahead_days must be non-negative")

    anchor = today or date.today()
    return anchor - timedelta(days=lookback_days), anchor + timedelta(days=lookahead_days)


def build_live_scoring_feed(
    results: Iterable[EventingResult],
    *,
    start_date: date,
    end_date: date,
    updated_at: datetime | None = None,
    crawl_summary: object | None = None,
) -> dict[str, object]:
    """Group current results into ranked event leaderboards."""

    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    refreshed_at = _utc_datetime(updated_at)
    current_results = [
        result
        for result in consolidate_results(list(results))
        if start_date <= result.event_date <= end_date
    ]
    grouped_results: dict[tuple[str, date, str, str], list[EventingResult]] = defaultdict(list)
    for result in current_results:
        grouped_results[(result.event_name, result.event_date, result.level, result.country)].append(result)

    events = [
        _event_leaderboard(event_name, event_date, level, country, event_results)
        for (event_name, event_date, level, country), event_results in grouped_results.items()
    ]
    events.sort(key=lambda item: (item["event_date"], item["event_name"], item["level"], item["country"]))

    summary = {
        "result_count": len(current_results),
        "leaderboard_count": len(events),
    }
    if crawl_summary is not None:
        summary.update(
            {
                "events_found": getattr(crawl_summary, "events_found", 0),
                "events_opened": getattr(crawl_summary, "events_opened", 0),
                "result_pages_opened": getattr(crawl_summary, "result_pages_opened", 0),
                "results_collected": getattr(crawl_summary, "results_collected", 0),
                "results_verified": getattr(crawl_summary, "results_verified", 0),
                "results_rejected": getattr(crawl_summary, "results_rejected", 0),
            }
        )

    return {
        "version": 1,
        "feed_type": "current_event_live_scoring",
        "updated_at": refreshed_at.isoformat(),
        "date_window": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "source_ids": sorted({result.source_id for result in current_results}),
        "summary": summary,
        "events": events,
    }


def write_live_scoring_feed(path: Path | str, feed: Mapping[str, object]) -> None:
    """Write a live scoring feed as stable JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as feed_file:
        json.dump(feed, feed_file, indent=2, sort_keys=True)
        feed_file.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh current-event FEI live scoring")
    parser.add_argument("--start-date", type=_date_arg, help="Current-event window start date, YYYY-MM-DD")
    parser.add_argument("--end-date", type=_date_arg, help="Current-event window end date, YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--lookahead-days", type=int, default=DEFAULT_LOOKAHEAD_DAYS)
    parser.add_argument("--event-url", action="append", default=[], help="Specific FEI event/result URL to open")
    parser.add_argument("--form-field", action="append", default=[], help="Extra FEI search form value as name=value")
    parser.add_argument("--results-store", type=Path, default=DEFAULT_RESULTS_FILE, help="Merged FEI result store path")
    parser.add_argument("--output", type=Path, default=DEFAULT_LIVE_SCORES_FILE, help="Live scoring JSON feed path")
    parser.add_argument("--raw-dir", type=Path, help="Optional directory for raw FEI HTML responses")
    parser.add_argument("--max-events", type=int, help="Maximum events to open")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Delay between FEI requests in seconds")
    parser.add_argument("--driver", choices=("auto", "browser", "http"), default="auto", help="FEI page driver")
    parser.add_argument("--headful", action="store_true", help="Show the browser window for manual login/debugging")
    parser.add_argument("--browser-executable", help="Chrome/Chromium executable for the browser driver")
    parser.add_argument("--storage-state", type=Path, help="Persist Playwright cookies/session state")
    parser.add_argument("--challenge-wait", type=float, default=10.0, help="Seconds to wait for FEI JS challenges")
    parser.add_argument("--cookie", help="FEI session cookie header")
    parser.add_argument("--cookie-env", default="FEI_COOKIE", help="Environment variable containing FEI cookie")
    parser.add_argument("--verify", choices=("none", "warn", "require"), default="none")
    parser.add_argument("--dry-run", action="store_true", help="Collect and summarize without writing output")
    args = parser.parse_args(argv)

    start_date, end_date = _resolve_date_window(args)
    cookie = args.cookie or _env_value(args.cookie_env)
    client = _build_client(args, cookie)
    verifier = FeiVerifier(client) if args.verify != "none" else None
    bot = FeiDataBot(client, verifier=verifier, raw_dir=args.raw_dir)
    form_fields = _key_values(args.form_field)

    try:
        results, crawl_summary = bot.collect(
            start_date=start_date,
            end_date=end_date,
            event_urls=args.event_url,
            form_fields=form_fields,
            max_events=args.max_events,
            verify=args.verify,
        )
    finally:
        if hasattr(client, "close"):
            client.close()

    store = FeiResultStore(args.results_store)
    merged_results = store.merge(results)
    feed = build_live_scoring_feed(
        merged_results,
        start_date=start_date,
        end_date=end_date,
        crawl_summary=crawl_summary,
    )

    if not args.dry_run:
        store.save(merged_results)
        write_live_scoring_feed(args.output, feed)

    summary = feed["summary"]
    print(
        "Live scoring refresh complete: "
        f"window={start_date.isoformat()}..{end_date.isoformat()}, "
        f"events_found={summary.get('events_found', 0)}, "
        f"results_collected={summary.get('results_collected', 0)}, "
        f"live_results={summary['result_count']}, "
        f"leaderboards={summary['leaderboard_count']}"
    )
    return 0


def _resolve_date_window(args: argparse.Namespace) -> tuple[date, date]:
    if args.start_date and args.end_date:
        return args.start_date, args.end_date
    if args.start_date:
        return args.start_date, args.start_date + timedelta(days=args.lookahead_days)
    if args.end_date:
        return args.end_date - timedelta(days=args.lookback_days), args.end_date
    return current_event_window(
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
    )


def _event_leaderboard(
    event_name: str,
    event_date: date,
    level: str,
    country: str,
    results: Sequence[EventingResult],
) -> dict[str, object]:
    leaders = _ranked_entries(results)
    return {
        "event_key": "::".join((_slug(event_name), event_date.isoformat(), _slug(level), _slug(country))),
        "event_name": event_name,
        "event_date": event_date.isoformat(),
        "level": level,
        "country": country,
        "leader_count": len(leaders),
        "leaders": leaders,
    }


def _ranked_entries(results: Sequence[EventingResult]) -> list[dict[str, object]]:
    sorted_results = sorted(
        results,
        key=lambda result: (
            result.finishing_score,
            result.rider_name.casefold(),
            result.horse_name.casefold(),
            result.source_record_id,
        ),
    )
    entries: list[dict[str, object]] = []
    previous_score: float | None = None
    current_rank = 0
    for index, result in enumerate(sorted_results, start=1):
        if previous_score is None or result.finishing_score != previous_score:
            current_rank = index
            previous_score = result.finishing_score
        entries.append(_leader_entry(result, current_rank))
    return entries


def _leader_entry(result: EventingResult, rank: int) -> dict[str, object]:
    return {
        "rank": rank,
        "rider_name": result.rider_name,
        "horse_name": result.horse_name,
        "finishing_score": result.finishing_score,
        "dressage_score": result.dressage_score,
        "show_jumping_penalties": result.show_jumping_penalties,
        "cross_country_jump_penalties": result.cross_country_jump_penalties,
        "cross_country_time_penalties": result.cross_country_time_penalties,
        "source_id": result.source_id,
        "source_record_id": result.source_record_id,
        "collected_at": result.collected_at.isoformat(),
    }


def _utc_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
