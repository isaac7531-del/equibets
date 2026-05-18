"""Live scoring snapshots for current eventing results."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from equibets.results import EventingResult, consolidate_results


DEFAULT_LIVE_SCORES_FILE = (
    Path(__file__).resolve().parents[1] / "public" / "data" / "live_scores.json"
)


def current_event_window(
    today: date | None = None,
    *,
    days_back: int = 7,
    days_forward: int = 1,
) -> tuple[date, date]:
    """Return the rolling date window used for current-event refreshes."""

    if days_back < 0:
        raise ValueError("days_back must be non-negative")
    if days_forward < 0:
        raise ValueError("days_forward must be non-negative")

    anchor = today or datetime.now(timezone.utc).date()
    return anchor - timedelta(days=days_back), anchor + timedelta(days=days_forward)


def build_live_score_payload(
    results: Sequence[EventingResult],
    *,
    window_start: date,
    window_end: date,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Build JSON-ready live scoring data for current event result tables."""

    if window_end < window_start:
        raise ValueError("window_end must be on or after window_start")

    generated = generated_at or datetime.now(timezone.utc).replace(microsecond=0)
    windowed_results = [
        result
        for result in consolidate_results(list(results))
        if window_start <= result.event_date <= window_end
    ]
    sorted_results = sorted(
        windowed_results,
        key=lambda result: (
            result.event_date,
            result.event_name.casefold(),
            result.level.casefold(),
            result.finishing_score,
            result.rider_name.casefold(),
            result.horse_name.casefold(),
        ),
    )

    return {
        "version": 1,
        "generated_at": generated.isoformat(),
        "window": {
            "start_date": window_start.isoformat(),
            "end_date": window_end.isoformat(),
        },
        "result_count": len(sorted_results),
        "source_ids": sorted({result.source_id for result in sorted_results}),
        "results": [_live_result_mapping(result) for result in sorted_results],
    }


def save_live_score_payload(
    results: Sequence[EventingResult],
    *,
    path: Path | str = DEFAULT_LIVE_SCORES_FILE,
    window_start: date,
    window_end: date,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Write live scoring data and return the payload that was saved."""

    payload = build_live_score_payload(
        results,
        window_start=window_start,
        window_end=window_end,
        generated_at=generated_at,
    )
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as live_scores_file:
        json.dump(payload, live_scores_file, indent=2, sort_keys=True)
        live_scores_file.write("\n")
    return payload


def _live_result_mapping(result: EventingResult) -> dict[str, object]:
    return {
        "source_id": result.source_id,
        "source_record_id": result.source_record_id,
        "rider_name": result.rider_name,
        "horse_name": result.horse_name,
        "event_name": result.event_name,
        "event_date": result.event_date.isoformat(),
        "level": result.level,
        "country": result.country,
        "dressage_score": result.dressage_score,
        "show_jumping_penalties": result.show_jumping_penalties,
        "cross_country_jump_penalties": result.cross_country_jump_penalties,
        "cross_country_time_penalties": result.cross_country_time_penalties,
        "finishing_score": result.finishing_score,
        "collected_at": result.collected_at.isoformat(),
        "is_user_entered": result.is_user_entered,
    }
