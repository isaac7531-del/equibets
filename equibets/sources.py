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
ALL_COUNTRY_WILDCARDS = {"all_countries", "all_fei_member_nations"}
ALL_EVENTING_LEVELS = "all_eventing_levels"


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
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region and optional level."""

    normalized_region = region.lower().replace(" ", "_")
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
        and _source_covers_level(source, level)
    ]


def sources_for_country(
    country: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country and optional level."""

    normalized_country = country.upper().replace(" ", "_")
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and _source_covers_country(source, normalized_country)
        and _source_covers_level(source, level)
    ]


def _source_covers_country(source: EventSource, country: str) -> bool:
    countries = {_normalize_country(item) for item in source.countries}
    return country in countries or bool(countries & ALL_COUNTRY_WILDCARDS)


def _source_covers_level(source: EventSource, level: str | None) -> bool:
    if level is None:
        return True

    normalized_level = level.lower().replace(" ", "_")
    levels = {item.lower().replace(" ", "_") for item in source.event_levels}
    return normalized_level in levels or ALL_EVENTING_LEVELS in levels


def _normalize_country(country: str) -> str:
    normalized = country.strip()
    if normalized in ALL_COUNTRY_WILDCARDS:
        return normalized
    return normalized.upper().replace(" ", "_")


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
