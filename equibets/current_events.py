"""Current event snapshots and live-scoring search helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "current_events.json"


@dataclass(frozen=True)
class CurrentEventResult:
    """One live row from a current event scoring source."""

    place: str
    start_number: int | None
    rider_name: str
    horse_name: str
    country: str
    dressage_score: float | None
    show_jumping_penalties: float | None
    cross_country_jump_penalties: float | None
    cross_country_time_penalties: float | None
    total_penalties: float | None
    phase: str

    @property
    def live_score(self) -> float | None:
        """Best available score for partially completed current events."""

        return self.total_penalties

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CurrentEventResult":
        return cls(
            place=_required_str(values, "place"),
            start_number=_optional_int(values, "start_number"),
            rider_name=_required_str(values, "rider_name"),
            horse_name=_required_str(values, "horse_name"),
            country=_required_str(values, "country"),
            dressage_score=_optional_number(values, "dressage_score"),
            show_jumping_penalties=_optional_number(values, "show_jumping_penalties"),
            cross_country_jump_penalties=_optional_number(
                values,
                "cross_country_jump_penalties",
            ),
            cross_country_time_penalties=_optional_number(
                values,
                "cross_country_time_penalties",
            ),
            total_penalties=_optional_number(values, "total_penalties"),
            phase=_required_str(values, "phase"),
        )


@dataclass(frozen=True)
class CurrentEvent:
    """A current or upcoming event with pulled live-scoring rows."""

    id: str
    name: str
    country: str
    region: str
    level: str
    start_date: date
    end_date: date
    status: str
    source_id: str
    source_name: str
    source_url: str
    last_checked_at: datetime
    notes: str
    results: tuple[CurrentEventResult, ...]

    @property
    def leader(self) -> CurrentEventResult | None:
        ranked = ranked_live_results(self.results)
        return ranked[0] if ranked else None

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CurrentEvent":
        results = values.get("results", [])
        if not isinstance(results, list):
            raise ValueError("results must be a list")

        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            country=_required_str(values, "country"),
            region=_required_str(values, "region"),
            level=_required_str(values, "level"),
            start_date=date.fromisoformat(_required_str(values, "start_date")),
            end_date=date.fromisoformat(_required_str(values, "end_date")),
            status=_required_str(values, "status"),
            source_id=_required_str(values, "source_id"),
            source_name=_required_str(values, "source_name"),
            source_url=_required_str(values, "source_url"),
            last_checked_at=datetime.fromisoformat(
                _required_str(values, "last_checked_at").replace("Z", "+00:00"),
            ),
            notes=_required_str(values, "notes"),
            results=tuple(CurrentEventResult.from_mapping(item) for item in results),
        )


def load_current_events(path: Path | str = DATA_FILE) -> list[CurrentEvent]:
    """Load the latest pulled current-event snapshot."""

    with Path(path).open(encoding="utf-8") as current_events_file:
        payload = json.load(current_events_file)

    return [
        CurrentEvent.from_mapping(item)
        for item in sorted(
            payload["events"],
            key=lambda event: (event["start_date"], event["name"]),
        )
    ]


def events_with_live_scores(path: Path | str = DATA_FILE) -> list[CurrentEvent]:
    """Return only events that have pulled live scoring rows."""

    return [
        event
        for event in load_current_events(path)
        if event.status == "live" and len(event.results) > 0
    ]


def search_current_events(query: str, path: Path | str = DATA_FILE) -> list[CurrentEvent]:
    """Search current events by event, rider, horse, source, country, or level."""

    normalized_query = query.strip().lower()
    if not normalized_query:
        return load_current_events(path)

    return [
        event
        for event in load_current_events(path)
        if _event_matches(event, normalized_query)
    ]


def ranked_live_results(
    results: tuple[CurrentEventResult, ...] | list[CurrentEventResult],
) -> list[CurrentEventResult]:
    """Rank pulled live rows with available scores first; lower penalties win."""

    return sorted(
        results,
        key=lambda result: (
            result.live_score is None,
            result.live_score if result.live_score is not None else float("inf"),
            result.rider_name,
            result.horse_name,
        ),
    )


def _event_matches(event: CurrentEvent, normalized_query: str) -> bool:
    event_values = (
        event.name,
        event.country,
        event.region,
        event.level,
        event.source_name,
        event.status,
    )
    if any(normalized_query in value.lower() for value in event_values):
        return True

    return any(
        normalized_query in value.lower()
        for result in event.results
        for value in (result.rider_name, result.horse_name, result.country, result.phase)
    )


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_int(values: dict[str, object], key: str) -> int | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer or null")
    return value


def _optional_number(values: dict[str, object], key: str) -> float | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number or null")
    return float(value)
