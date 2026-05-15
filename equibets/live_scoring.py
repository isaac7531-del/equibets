"""Build live current-event scoreboards from refreshed eventing results."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from equibets.results import EventingResult, consolidate_results, load_results


DEFAULT_FEI_RESULTS_FILE = Path(__file__).resolve().parents[1] / "data" / "fei_results.json"
DEFAULT_LIVE_SCORE_FILE = Path(__file__).resolve().parents[1] / "data" / "live_scores.json"


@dataclass(frozen=True)
class LiveScoreWindow:
    """Inclusive event-date window used for a live scoring refresh."""

    start_date: date
    end_date: date


@dataclass(frozen=True)
class LiveScoreRow:
    """A ranked current-event result row."""

    rank: int
    rider_name: str
    horse_name: str
    event_name: str
    event_date: date
    level: str
    country: str
    dressage_score: float
    show_jumping_penalties: float
    cross_country_jump_penalties: float
    cross_country_time_penalties: float
    total_penalties: float
    source_id: str
    collected_at: datetime


def current_event_window(
    on_date: date,
    *,
    lookback_days: int = 3,
    lookahead_days: int = 1,
) -> LiveScoreWindow:
    """Return the current-event window for a scheduled refresh."""

    if lookback_days < 0 or lookahead_days < 0:
        raise ValueError("lookback_days and lookahead_days must be non-negative")

    return LiveScoreWindow(
        start_date=on_date - timedelta(days=lookback_days),
        end_date=on_date + timedelta(days=lookahead_days),
    )


def build_live_score_rows(
    results: Iterable[EventingResult],
    window: LiveScoreWindow,
) -> list[LiveScoreRow]:
    """Filter consolidated results to current events and rank each competition."""

    current_results = [
        result
        for result in consolidate_results(list(results))
        if window.start_date <= result.event_date <= window.end_date
    ]

    grouped_results: dict[tuple[date, str, str, str], list[EventingResult]] = defaultdict(list)
    for result in current_results:
        grouped_results[(result.event_date, result.event_name, result.level, result.country)].append(result)

    rows: list[LiveScoreRow] = []
    for event_results in grouped_results.values():
        ranked_results = sorted(
            event_results,
            key=lambda result: (
                result.finishing_score,
                result.dressage_score,
                result.cross_country_time_penalties,
                result.rider_name,
                result.horse_name,
            ),
        )
        for rank, result in enumerate(ranked_results, start=1):
            rows.append(
                LiveScoreRow(
                    rank=rank,
                    rider_name=result.rider_name,
                    horse_name=result.horse_name,
                    event_name=result.event_name,
                    event_date=result.event_date,
                    level=result.level,
                    country=result.country,
                    dressage_score=result.dressage_score,
                    show_jumping_penalties=result.show_jumping_penalties,
                    cross_country_jump_penalties=result.cross_country_jump_penalties,
                    cross_country_time_penalties=result.cross_country_time_penalties,
                    total_penalties=result.finishing_score,
                    source_id=result.source_id,
                    collected_at=result.collected_at,
                )
            )

    return sorted(rows, key=lambda row: (row.event_date, row.event_name, row.level, row.rank))


def build_live_score_report(
    results: Iterable[EventingResult],
    *,
    generated_at: datetime,
    on_date: date,
    lookback_days: int = 3,
    lookahead_days: int = 1,
) -> dict[str, object]:
    """Create a JSON-serializable live scoring report."""

    window = current_event_window(
        on_date,
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
    )
    rows = build_live_score_rows(results, window)
    grouped_rows: dict[tuple[date, str, str, str], list[LiveScoreRow]] = defaultdict(list)
    for row in rows:
        grouped_rows[(row.event_date, row.event_name, row.level, row.country)].append(row)

    latest_collected_at = max((row.collected_at for row in rows), default=None)
    events = [
        {
            "event_name": event_name,
            "event_date": event_date.isoformat(),
            "level": level,
            "country": country,
            "result_count": len(event_rows),
            "results": [_row_to_mapping(row) for row in event_rows],
        }
        for (event_date, event_name, level, country), event_rows in sorted(grouped_rows.items())
    ]

    return {
        "version": 1,
        "generated_at": generated_at.replace(microsecond=0).isoformat(),
        "on_date": on_date.isoformat(),
        "window": {
            "start_date": window.start_date.isoformat(),
            "end_date": window.end_date.isoformat(),
            "lookback_days": lookback_days,
            "lookahead_days": lookahead_days,
        },
        "latest_collected_at": latest_collected_at.isoformat() if latest_collected_at else None,
        "event_count": len(events),
        "result_count": len(rows),
        "events": events,
    }


def load_result_files(paths: Sequence[Path]) -> list[EventingResult]:
    """Load all existing JSON result files in project result format."""

    results: list[EventingResult] = []
    for path in paths:
        if path.exists():
            results.extend(load_results(path))
    return results


def save_live_score_report(report: dict[str, object], path: Path) -> None:
    """Write a live scoring report to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as live_score_file:
        json.dump(report, live_score_file, indent=2, sort_keys=True)
        live_score_file.write("\n")


def refresh_fei_results(args: argparse.Namespace, window: LiveScoreWindow) -> tuple[int, int]:
    """Pull current FEI results for the scoreboard window."""

    from equibets.fei_bot import (
        FeiBrowserClient,
        FeiDataBot,
        FeiHttpClient,
        FeiResultStore,
        FeiVerifier,
    )

    cookie = args.cookie or os.environ.get(args.cookie_env)
    if args.refresh_driver == "http":
        client = FeiHttpClient(cookie=cookie, rate_limit_seconds=args.rate_limit)
    else:
        client = FeiBrowserClient(
            cookie=cookie,
            headless=not args.headful,
            executable_path=args.browser_executable,
            storage_state=args.storage_state,
            challenge_wait_seconds=args.challenge_wait,
        )

    verifier = FeiVerifier(client) if args.verify != "none" else None
    bot = FeiDataBot(client, verifier=verifier, raw_dir=args.raw_dir)
    try:
        results, summary = bot.collect(
            start_date=window.start_date,
            end_date=window.end_date,
            max_events=args.max_events,
            verify=args.verify,
        )
    finally:
        if hasattr(client, "close"):
            client.close()

    store = FeiResultStore(args.fei_output)
    merged = store.merge(results)
    store.save(merged)
    return summary.results_collected, len(merged)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh current-event results and write live scores")
    parser.add_argument("--on-date", type=_date_arg, default=date.today(), help="Scoring date, YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, default=3, help="Days before on-date to include")
    parser.add_argument("--lookahead-days", type=int, default=1, help="Days after on-date to include")
    parser.add_argument(
        "--results-file",
        action="append",
        type=Path,
        default=[],
        help="Existing result JSON file to include; can be repeated",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_LIVE_SCORE_FILE, help="Live score JSON output")
    parser.add_argument("--refresh-fei", action="store_true", help="Search FEI current events before scoring")
    parser.add_argument("--fei-output", type=Path, default=DEFAULT_FEI_RESULTS_FILE, help="Merged FEI result store")
    parser.add_argument("--raw-dir", type=Path, help="Optional directory for raw FEI HTML responses")
    parser.add_argument("--max-events", type=int, help="Maximum FEI events to open")
    parser.add_argument("--refresh-driver", choices=("browser", "http"), default="browser", help="FEI page driver")
    parser.add_argument("--headful", action="store_true", help="Show the browser window for manual login/debugging")
    parser.add_argument("--browser-executable", help="Chrome/Chromium executable for the browser driver")
    parser.add_argument("--storage-state", type=Path, help="Persist Playwright cookies/session state")
    parser.add_argument("--challenge-wait", type=float, default=10.0, help="Seconds to wait for FEI JS challenges")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Delay between FEI HTTP requests in seconds")
    parser.add_argument("--cookie", help="FEI session cookie header")
    parser.add_argument("--cookie-env", default="FEI_COOKIE", help="Environment variable containing FEI cookie")
    parser.add_argument("--verify", choices=("none", "warn", "require"), default="none")
    args = parser.parse_args(argv)

    window = current_event_window(
        args.on_date,
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
    )
    collected = None
    merged_count = None
    result_paths = [*args.results_file]

    if args.refresh_fei:
        collected, merged_count = refresh_fei_results(args, window)
        result_paths.append(args.fei_output)
    elif not result_paths:
        result_paths.append(args.fei_output)

    report = build_live_score_report(
        load_result_files(result_paths),
        generated_at=datetime.now(timezone.utc),
        on_date=args.on_date,
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
    )
    save_live_score_report(report, args.output)

    refresh_summary = ""
    if collected is not None:
        refresh_summary = f", fei_results_collected={collected}, fei_results_in_store={merged_count}"
    print(
        "Live scoring complete: "
        f"events={report['event_count']}, "
        f"results={report['result_count']}, "
        f"output={args.output}{refresh_summary}"
    )
    return 0


def _row_to_mapping(row: LiveScoreRow) -> dict[str, object]:
    return {
        "rank": row.rank,
        "rider_name": row.rider_name,
        "horse_name": row.horse_name,
        "event_name": row.event_name,
        "event_date": row.event_date.isoformat(),
        "level": row.level,
        "country": row.country,
        "dressage_score": row.dressage_score,
        "show_jumping_penalties": row.show_jumping_penalties,
        "cross_country_jump_penalties": row.cross_country_jump_penalties,
        "cross_country_time_penalties": row.cross_country_time_penalties,
        "total_penalties": row.total_penalties,
        "source_id": row.source_id,
        "collected_at": row.collected_at.isoformat(),
    }


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected date as YYYY-MM-DD") from exc


if __name__ == "__main__":
    raise SystemExit(main())
