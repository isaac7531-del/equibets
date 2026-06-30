"""Build live-scoring snapshots from collected eventing results."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from equibets.results import EventingResult, consolidate_results, load_results


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_FILE = REPO_ROOT / "data" / "fei_results.json"
DEFAULT_LIVE_SCORES_FILE = REPO_ROOT / "src" / "data" / "live_scores.json"
DEFAULT_DAYS_BACK = 7
DEFAULT_DAYS_FORWARD = 2


def current_event_window(
    today: date | None = None,
    *,
    days_back: int = DEFAULT_DAYS_BACK,
    days_forward: int = DEFAULT_DAYS_FORWARD,
) -> tuple[date, date]:
    """Return the rolling date window used for current-event scoring."""

    if days_back < 0 or days_forward < 0:
        raise ValueError("days_back and days_forward must be non-negative")

    anchor_date = today or datetime.now(timezone.utc).date()
    return anchor_date - timedelta(days=days_back), anchor_date + timedelta(days=days_forward)


def load_results_if_present(path: Path | str = DEFAULT_RESULTS_FILE) -> list[EventingResult]:
    """Load results from a store, returning an empty list before the first crawl."""

    result_path = Path(path)
    if not result_path.exists():
        return []
    return load_results(result_path)


def build_live_score_payload(
    results: Iterable[EventingResult],
    *,
    start_date: date,
    end_date: date,
    generated_at: datetime | None = None,
    max_standings_per_event: int | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable live-scoring payload for current events."""

    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    if max_standings_per_event is not None and max_standings_per_event <= 0:
        raise ValueError("max_standings_per_event must be positive")

    consolidated = [
        result
        for result in consolidate_results(list(results))
        if start_date <= result.event_date <= end_date
    ]
    grouped: dict[tuple[str, date, str], list[EventingResult]] = defaultdict(list)
    for result in consolidated:
        grouped[(result.event_name, result.event_date, result.country)].append(result)

    events = [
        _event_payload(key, event_results, max_standings_per_event=max_standings_per_event)
        for key, event_results in grouped.items()
    ]
    events.sort(
        key=lambda event: (event["event_date"], event["event_name"], event["level"], event["country"]),
        reverse=True,
    )

    source_ids = sorted({result.source_id for result in consolidated})
    latest_collected_at = _latest_collected_at(consolidated)
    return {
        "version": 1,
        "generated_at": _datetime_to_iso(generated_at or datetime.now(timezone.utc)),
        "window": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "event_count": len(events),
        "result_count": sum(event["result_count"] for event in events),
        "source_ids": source_ids,
        "latest_collected_at": latest_collected_at,
        "events": events,
    }


def write_live_score_payload(payload: dict[str, Any], path: Path | str = DEFAULT_LIVE_SCORES_FILE) -> None:
    """Write a live-scoring payload as stable, pretty-printed JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, sort_keys=True)
        output_file.write("\n")


def _event_payload(
    key: tuple[str, date, str],
    event_results: list[EventingResult],
    *,
    max_standings_per_event: int | None,
) -> dict[str, Any]:
    event_name, event_date, country = key
    event_standings = _dedupe_event_standings(event_results)
    ordered_results = sorted(
        event_standings,
        key=lambda result: (
            result.finishing_score,
            result.rider_name.lower(),
            result.horse_name.lower(),
            result.source_record_id,
        ),
    )
    visible_results = ordered_results[:max_standings_per_event] if max_standings_per_event else ordered_results

    return {
        "event_name": event_name,
        "event_date": event_date.isoformat(),
        "level": _merge_competition_classes(result.level for result in event_results),
        "country": country,
        "result_count": len(ordered_results),
        "source_ids": sorted({result.source_id for result in ordered_results}),
        "latest_collected_at": _latest_collected_at(ordered_results),
        "standings": _standings_payload(visible_results),
    }


def _dedupe_event_standings(results: Iterable[EventingResult]) -> list[EventingResult]:
    selected: dict[str, EventingResult] = {}
    for result in results:
        existing = selected.get(result.combination_key)
        if existing is None or _is_better_live_result(result, existing):
            selected[result.combination_key] = result
    return list(selected.values())


def _is_better_live_result(candidate: EventingResult, existing: EventingResult) -> bool:
    candidate_score = (
        candidate.finishing_score,
        candidate.source_priority,
        -candidate.collected_at.timestamp(),
        candidate.source_record_id,
    )
    existing_score = (
        existing.finishing_score,
        existing.source_priority,
        -existing.collected_at.timestamp(),
        existing.source_record_id,
    )
    return candidate_score < existing_score


def _merge_competition_classes(levels: Iterable[str]) -> str:
    classes: dict[str, None] = {}
    for level in levels:
        for value in level.split(","):
            competition_class = value.strip()
            if competition_class:
                classes.setdefault(competition_class, None)
    return " , ".join(classes)


def _standings_payload(results: Sequence[EventingResult]) -> list[dict[str, Any]]:
    standings: list[dict[str, Any]] = []
    previous_score: float | None = None
    current_rank = 0
    for index, result in enumerate(results, start=1):
        if previous_score != result.finishing_score:
            current_rank = index
            previous_score = result.finishing_score
        standings.append(
            {
                "rank": current_rank,
                "rider_name": result.rider_name,
                "horse_name": result.horse_name,
                "finishing_score": result.finishing_score,
                "dressage_score": result.dressage_score,
                "show_jumping_penalties": result.show_jumping_penalties,
                "cross_country_penalties": round(
                    result.cross_country_jump_penalties + result.cross_country_time_penalties,
                    1,
                ),
                "source_id": result.source_id,
                "collected_at": _datetime_to_iso(result.collected_at),
            }
        )
    return standings


def _latest_collected_at(results: Iterable[EventingResult]) -> str | None:
    collected_values = [_datetime_to_iso(result.collected_at) for result in results]
    if not collected_values:
        return None
    return max(collected_values)


def _datetime_to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        return value.replace(microsecond=0).isoformat()
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the current-event live-scoring snapshot")
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS_FILE, help="Input eventing results JSON")
    parser.add_argument("--output", type=Path, default=DEFAULT_LIVE_SCORES_FILE, help="Live-score JSON output")
    parser.add_argument("--start-date", type=_date_arg, help="Window start date, YYYY-MM-DD")
    parser.add_argument("--end-date", type=_date_arg, help="Window end date, YYYY-MM-DD")
    parser.add_argument("--days-back", type=int, default=DEFAULT_DAYS_BACK, help="Days before today for the default window")
    parser.add_argument(
        "--days-forward",
        type=int,
        default=DEFAULT_DAYS_FORWARD,
        help="Days after today for the default window",
    )
    parser.add_argument("--max-standings-per-event", type=int, help="Limit standings rows written per event")
    args = parser.parse_args(argv)

    if args.start_date or args.end_date:
        if not args.start_date or not args.end_date:
            raise SystemExit("--start-date and --end-date must be provided together")
        start_date, end_date = args.start_date, args.end_date
    else:
        start_date, end_date = current_event_window(
            days_back=args.days_back,
            days_forward=args.days_forward,
        )

    payload = build_live_score_payload(
        load_results_if_present(args.results),
        start_date=start_date,
        end_date=end_date,
        max_standings_per_event=args.max_standings_per_event,
    )
    write_live_score_payload(payload, args.output)
    print(
        "Live scoring snapshot written: "
        f"events={payload['event_count']}, "
        f"results={payload['result_count']}, "
        f"output={args.output}"
    )
    return 0


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


if __name__ == "__main__":
    raise SystemExit(main())
