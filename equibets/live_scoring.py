"""Current-event live scoreboards built from normalized eventing results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Sequence

from equibets.results import EventingResult, consolidate_results


DEFAULT_LIVE_SCORES_FILE = Path(__file__).resolve().parents[1] / "public" / "live_scores.json"


@dataclass(frozen=True)
class CurrentEventWindow:
    """Date range used when pulling and displaying current event results."""

    start_date: date
    end_date: date


def current_event_window(
    *,
    today: date | None = None,
    lookback_days: int = 7,
    lookahead_days: int = 1,
) -> CurrentEventWindow:
    """Return a window covering recently completed and in-progress events."""

    if lookback_days < 0:
        raise ValueError("lookback_days must be greater than or equal to 0")
    if lookahead_days < 0:
        raise ValueError("lookahead_days must be greater than or equal to 0")

    current_day = today or datetime.now(timezone.utc).date()
    return CurrentEventWindow(
        start_date=current_day - timedelta(days=lookback_days),
        end_date=current_day + timedelta(days=lookahead_days),
    )


def current_event_results(
    results: Sequence[EventingResult],
    *,
    start_date: date,
    end_date: date,
) -> list[EventingResult]:
    """Filter consolidated results to the current-event window."""

    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    return sorted(
        (
            result
            for result in consolidate_results(list(results))
            if start_date <= result.event_date <= end_date
        ),
        key=lambda result: (
            result.finishing_score,
            result.event_date,
            result.event_name.lower(),
            result.level.lower(),
            result.rider_name.lower(),
            result.horse_name.lower(),
        ),
        reverse=False,
    )


def live_scoreboard_mapping(
    results: Sequence[EventingResult],
    *,
    start_date: date,
    end_date: date,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Build the JSON payload consumed by the frontend live scoring panel."""

    current_results = current_event_results(
        results,
        start_date=start_date,
        end_date=end_date,
    )
    generated = generated_at or datetime.now(timezone.utc).replace(microsecond=0)
    latest_collected_at = _latest_collected_at(current_results)

    return {
        "version": 1,
        "generated_at": _iso_timestamp(generated),
        "window": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "latest_collected_at": _iso_timestamp(latest_collected_at) if latest_collected_at else None,
        "result_count": len(current_results),
        "scores": [_result_mapping(result) for result in current_results],
    }


def save_live_scoreboard(
    results: Sequence[EventingResult],
    path: Path | str = DEFAULT_LIVE_SCORES_FILE,
    *,
    start_date: date,
    end_date: date,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Write the current-event scoreboard JSON and return the payload."""

    payload = live_scoreboard_mapping(
        results,
        start_date=start_date,
        end_date=end_date,
        generated_at=generated_at,
    )
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, sort_keys=True)
        output_file.write("\n")
    return payload


def _result_mapping(result: EventingResult) -> dict[str, object]:
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
        "collected_at": _iso_timestamp(result.collected_at),
    }


def _latest_collected_at(results: Sequence[EventingResult]) -> datetime | None:
    if not results:
        return None
    return max((_utc_datetime(result.collected_at) for result in results), default=None)


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso_timestamp(value: datetime) -> str:
    return _utc_datetime(value).replace(microsecond=0).isoformat()
