"""Build frontend live-score snapshots from collected eventing results."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence

from equibets.results import EventingResult, consolidate_results


DEFAULT_LIVE_SCORE_FILE = Path(__file__).resolve().parents[1] / "src" / "data" / "live_scores.json"


def build_live_score_payload(
    results: Sequence[EventingResult],
    *,
    window_start: date,
    window_end: date,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Build a ranked current-event payload for the React app."""

    generated_at = generated_at or datetime.now(timezone.utc).replace(microsecond=0)
    current_results = [
        result
        for result in consolidate_results(list(results))
        if window_start <= result.event_date <= window_end and not result.is_user_entered
    ]

    grouped_results: dict[tuple[str, date, str, str], list[EventingResult]] = defaultdict(list)
    for result in current_results:
        grouped_results[(result.event_name, result.event_date, result.level, result.country)].append(result)

    events = [
        _event_payload(event_key, event_results)
        for event_key, event_results in grouped_results.items()
    ]
    events.sort(
        key=lambda event: (
            str(event["event_date"]),
            str(event["event_name"]).lower(),
            str(event["level"]).lower(),
        )
    )

    return {
        "version": 1,
        "source_id": "data_fei",
        "generated_at": generated_at.isoformat(),
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "event_count": len(events),
        "result_count": sum(int(event["result_count"]) for event in events),
        "events": events,
    }


def save_live_score_payload(
    results: Sequence[EventingResult],
    path: Path | str = DEFAULT_LIVE_SCORE_FILE,
    *,
    window_start: date,
    window_end: date,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Write a live-score payload and return the JSON-compatible data."""

    payload = build_live_score_payload(
        results,
        window_start=window_start,
        window_end=window_end,
        generated_at=generated_at,
    )
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
    return payload


def _event_payload(
    event_key: tuple[str, date, str, str],
    event_results: Sequence[EventingResult],
) -> dict[str, object]:
    event_name, event_date, level, country = event_key
    ranked_results = _rank_results(event_results)
    leader = ranked_results[0] if ranked_results else None

    return {
        "event_name": event_name,
        "event_date": event_date.isoformat(),
        "level": level,
        "country": country,
        "result_count": len(ranked_results),
        "leader": leader,
        "results": ranked_results,
    }


def _rank_results(event_results: Sequence[EventingResult]) -> list[dict[str, object]]:
    sorted_results = sorted(
        event_results,
        key=lambda result: (
            result.finishing_score,
            result.rider_name.lower(),
            result.horse_name.lower(),
        ),
    )

    ranked: list[dict[str, object]] = []
    previous_score: float | None = None
    current_rank = 0
    for index, result in enumerate(sorted_results, start=1):
        if result.finishing_score != previous_score:
            current_rank = index
            previous_score = result.finishing_score
        ranked.append(_result_payload(result, current_rank))
    return ranked


def _result_payload(result: EventingResult, rank: int) -> dict[str, object]:
    return {
        "rank": rank,
        "rider_name": result.rider_name,
        "horse_name": result.horse_name,
        "total_penalties": result.finishing_score,
        "dressage_score": result.dressage_score,
        "show_jumping_penalties": result.show_jumping_penalties,
        "cross_country_jump_penalties": result.cross_country_jump_penalties,
        "cross_country_time_penalties": result.cross_country_time_penalties,
        "source_id": result.source_id,
        "source_record_id": result.source_record_id,
        "collected_at": result.collected_at.isoformat(),
    }
