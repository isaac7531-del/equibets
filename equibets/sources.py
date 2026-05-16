"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader coverage.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"
COUNTRY_WILDCARDS = {"all_countries", "all_fei_member_nations"}
LEVEL_WILDCARDS = {"all_eventing_levels"}


@dataclass(frozen=True)
class EventSource:
    """A configured event-results source."""

    id: str
    name: str
    priority: int
    scope: str
    regions: tuple[str, ...]
    countries: tuple[str, ...]
    disciplines: tuple[str, ...]
    event_levels: tuple[str, ...]
    source_type: str
    base_url: str | None
    status: str
    notes: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSource":
        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            priority=_required_int(values, "priority"),
            scope=_required_str(values, "scope"),
            regions=_string_tuple(values, "regions"),
            countries=_string_tuple(values, "countries"),
            disciplines=_string_tuple(values, "disciplines"),
            event_levels=_string_tuple(values, "event_levels"),
            source_type=_required_str(values, "source_type"),
            base_url=_optional_str(values, "base_url"),
            status=_required_str(values, "status"),
            notes=_required_str(values, "notes"),
        )


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    sources = [EventSource.from_mapping(item) for item in payload["sources"]]
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a region and optional level, preserving priorities."""

    normalized_region = _normalize_token(region)
    normalized_level = _normalize_token(level) if level is not None else None

    return [
        source
        for source in load_event_sources(path)
        if source.status in _statuses(include_planned)
        and ("global" in source.regions or normalized_region in source.regions)
        and _covers_level(source, normalized_level)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a country and optional level, preserving priorities."""

    normalized_country = _normalize_country(country)
    normalized_level = _normalize_token(level) if level is not None else None

    return [
        source
        for source in load_event_sources(path)
        if source.status in _statuses(include_planned)
        and _covers_country(source, normalized_country)
        and _covers_level(source, normalized_level)
    ]


def _statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _covers_country(source: EventSource, normalized_country: str) -> bool:
    for country in source.countries:
        if _normalize_token(country) in COUNTRY_WILDCARDS:
            return True
        if _normalize_country(country) == normalized_country:
            return True
    return False


def _covers_level(source: EventSource, normalized_level: str | None) -> bool:
    if normalized_level is None:
        return True

    return any(
        _normalize_token(level) in LEVEL_WILDCARDS
        or _normalize_token(level) == normalized_level
        for level in source.event_levels
    )


def _normalize_country(country: str) -> str:
    return country.strip().upper().replace(" ", "_").replace("-", "_")


def _normalize_token(token: str) -> str:
    return token.strip().lower().replace(" ", "_").replace("-", "_")


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(values: dict[str, object], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be null or a non-empty string")
    return value


def _required_int(values: dict[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
