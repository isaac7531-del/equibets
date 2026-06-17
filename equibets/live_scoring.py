"""Live score feed helpers for current eventing results."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from equibets.results import EventingResult, consolidate_results


DEFAULT_LIVE_SCORE_FILE = Path(__file__).resolve().parents[1] / "public" / "live_scores.json"


def current_event_window(
    today: date | None = None,
    *,
    lookback_days: int = 2,
    lookahead_days: int = 3,
) -> tuple[date, date]:
    """Return the date range to refresh for events that may still be changing."""

    if lookback_days < 0 or lookahead_days < 0:
        raise ValueError("lookback_days and lookahead_days must be non-negative")

    anchor = today or datetime.now(timezone.utc).date()
    return anchor - timedelta(days=lookback_days), anchor + timedelta(days=lookahead_days)


def build_live_score_feed(
    results: Iterable[EventingResult],
    *,
    window_start: date | None = None,
    window_end: date | None = None,
    updated_at: datetime | None = None,
    source_id: str = "data_fei",
) -> dict[str, object]:
    """Build a JSON-serializable live scoring feed grouped by event and level."""

    consolidated = [
        result
        for result in consolidate_results(list(results))
        if _within_window(result.event_date, window_start, window_end)
    ]
    scoreboards = _scoreboards(consolidated)
    timestamp = (updated_at or datetime.now(timezone.utc)).replace(microsecond=0)

    return {
        "version": 1,
        "source_id": source_id,
        "updated_at": timestamp.isoformat(),
        "window_start": window_start.isoformat() if window_start else None,
        "window_end": window_end.isoformat() if window_end else None,
        "event_count": len(scoreboards),
        "score_count": len(consolidated),
        "events": scoreboards,
    }


def save_live_score_feed(
    results: Sequence[EventingResult],
    path: Path | str = DEFAULT_LIVE_SCORE_FILE,
    *,
    window_start: date | None = None,
    window_end: date | None = None,
    updated_at: datetime | None = None,
    source_id: str = "data_fei",
) -> dict[str, object]:
    """Write the live score feed and return the payload that was saved."""

    payload = build_live_score_feed(
        results,
        window_start=window_start,
        window_end=window_end,
        updated_at=updated_at,
        source_id=source_id,
    )
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as feed_file:
        json.dump(payload, feed_file, indent=2, sort_keys=True)
        feed_file.write("\n")
    return payload


def _scoreboards(results: Sequence[EventingResult]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, date, str], list[EventingResult]] = {}
    for result in results:
        grouped.setdefault((result.event_name, result.event_date, result.level), []).append(result)

    scoreboards: list[dict[str, object]] = []
    for (event_name, event_date, level), event_results in grouped.items():
        ranked_results = sorted(
            event_results,
            key=lambda result: (
                result.finishing_score,
                result.rider_name.lower(),
                result.horse_name.lower(),
            ),
        )
        entries = [_entry_payload(result, rank) for rank, result in enumerate(ranked_results, start=1)]
        leader = entries[0] if entries else None
        country = _first_known_country(ranked_results)
        latest_collected_at = max(result.collected_at for result in ranked_results)
        scoreboards.append(
            {
                "event_name": event_name,
                "event_date": event_date.isoformat(),
                "level": level,
                "country": country,
                "latest_collected_at": latest_collected_at.isoformat(),
                "entry_count": len(entries),
                "leader": leader,
                "entries": entries,
            }
        )

    return sorted(
        scoreboards,
        key=lambda event: (
            str(event["event_date"]),
            str(event["event_name"]).lower(),
            str(event["level"]).lower(),
        ),
        reverse=True,
    )


def _entry_payload(result: EventingResult, rank: int) -> dict[str, object]:
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


def _within_window(result_date: date, window_start: date | None, window_end: date | None) -> bool:
    if window_start and result_date < window_start:
        return False
    if window_end and result_date > window_end:
        return False
    return True


def _first_known_country(results: Sequence[EventingResult]) -> str:
    for result in results:
        if result.country and result.country != "Unknown":
            return result.country
    return "Unknown"
