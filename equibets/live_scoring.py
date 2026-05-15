"""Current-event result search and live leaderboard helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from equibets.results import EventingResult, consolidate_results


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "current_event_results.json"

STATUS_ORDER = {
    "not_started": 0,
    "dressage": 1,
    "show_jumping": 2,
    "cross_country": 3,
    "final": 4,
}


@dataclass(frozen=True)
class LiveEventResult:
    """A normalized result from a current or recently refreshed event feed."""

    result: EventingResult
    status: str
    division: str
    source_url: str | None = None

    @property
    def finishing_score(self) -> float:
        return self.result.finishing_score

    @property
    def is_final(self) -> bool:
        return self.status == "final"

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "LiveEventResult":
        status = _required_str(values, "status")
        if status not in STATUS_ORDER:
            raise ValueError(f"status must be one of {', '.join(STATUS_ORDER)}")

        return cls(
            result=EventingResult.from_mapping(values),
            status=status,
            division=_optional_str(values, "division") or _required_str(values, "level"),
            source_url=_optional_str(values, "source_url"),
        )


@dataclass(frozen=True)
class LiveLeaderboardEntry:
    """One ranked live leaderboard row."""

    rank: int
    live_result: LiveEventResult


@dataclass(frozen=True)
class LiveScoringSnapshot:
    """Searchable live-scoring view assembled from current-event feeds."""

    collected_at: datetime
    source_ids: tuple[str, ...]
    entries: tuple[LiveLeaderboardEntry, ...]


def load_current_event_results(path: Path | str = DATA_FILE) -> list[LiveEventResult]:
    """Load normalized current-event records from JSON."""

    with Path(path).open(encoding="utf-8") as results_file:
        payload = json.load(results_file)

    return [LiveEventResult.from_mapping(item) for item in payload.get("results", [])]


def build_live_leaderboard(results: list[LiveEventResult]) -> tuple[LiveLeaderboardEntry, ...]:
    """Rank live results after deduplicating starts by source priority."""

    consolidated = _consolidate_live_results(results)
    ranked_results = sorted(
        consolidated,
        key=lambda item: (
            item.finishing_score,
            -STATUS_ORDER[item.status],
            item.result.event_date,
            item.result.rider_name,
            item.result.horse_name,
        ),
    )

    return tuple(
        LiveLeaderboardEntry(rank=index + 1, live_result=result)
        for index, result in enumerate(ranked_results)
    )


def search_current_event_results(
    results: list[LiveEventResult],
    search_text: str = "",
    *,
    event_name: str | None = None,
    country: str | None = None,
    status: str | None = None,
) -> list[LiveEventResult]:
    """Filter current-event records by horse, rider, event, country, or status."""

    normalized_search = _slug(search_text)
    normalized_event_name = _slug(event_name or "")
    normalized_country = (country or "").casefold()

    if status is not None and status not in STATUS_ORDER:
        raise ValueError(f"status must be one of {', '.join(STATUS_ORDER)}")

    matches: list[LiveEventResult] = []
    for item in results:
        searchable_text = _slug(
            " ".join(
                [
                    item.result.rider_name,
                    item.result.horse_name,
                    item.result.event_name,
                    item.result.level,
                    item.division,
                    item.result.country,
                ]
            )
        )
        if normalized_search and normalized_search not in searchable_text:
            continue
        if normalized_event_name and normalized_event_name not in _slug(item.result.event_name):
            continue
        if normalized_country and normalized_country != item.result.country.casefold():
            continue
        if status is not None and status != item.status:
            continue
        matches.append(item)

    return matches


def new_results_since(
    results: list[LiveEventResult],
    collected_after: datetime,
) -> list[LiveEventResult]:
    """Return records collected after the caller's last successful refresh."""

    cutoff = _aware_datetime(collected_after)
    return [
        item
        for item in results
        if _aware_datetime(item.result.collected_at) > cutoff
    ]


def pull_live_scoring_snapshot(
    path: Path | str = DATA_FILE,
    *,
    search_text: str = "",
    event_name: str | None = None,
    country: str | None = None,
    status: str | None = None,
    collected_after: datetime | None = None,
) -> LiveScoringSnapshot:
    """Load current-event results and return a filtered live leaderboard."""

    payload = _load_payload(path)
    results = [LiveEventResult.from_mapping(item) for item in payload.get("results", [])]
    if collected_after is not None:
        results = new_results_since(results, collected_after)

    searched_results = search_current_event_results(
        results,
        search_text,
        event_name=event_name,
        country=country,
        status=status,
    )
    return LiveScoringSnapshot(
        collected_at=_payload_collected_at(payload, searched_results),
        source_ids=tuple(sorted({item.result.source_id for item in searched_results})),
        entries=build_live_leaderboard(searched_results),
    )


def _consolidate_live_results(results: list[LiveEventResult]) -> list[LiveEventResult]:
    live_by_source_record: dict[tuple[str, str], LiveEventResult] = {
        (item.result.source_id, item.result.source_record_id): item for item in results
    }
    consolidated_results = consolidate_results([item.result for item in results])
    return [
        live_by_source_record[(item.source_id, item.source_record_id)]
        for item in consolidated_results
    ]


def _load_payload(path: Path | str) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as results_file:
        payload = json.load(results_file)

    if not isinstance(payload, dict):
        raise ValueError("current event payload must be a JSON object")
    return payload


def _payload_collected_at(
    payload: dict[str, object],
    results: list[LiveEventResult],
) -> datetime:
    collected_at = payload.get("collected_at")
    if isinstance(collected_at, str) and collected_at:
        return datetime.fromisoformat(collected_at)
    if results:
        return max(item.result.collected_at for item in results)
    return datetime.now(timezone.utc)


def _aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _optional_str(values: dict[str, object], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be null or a non-empty string")
    return value


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
