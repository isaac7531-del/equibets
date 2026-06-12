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
ALL_COUNTRIES = "all_countries"
ALL_EVENTING_LEVELS = "all_eventing_levels"
ALL_FEI_MEMBER_NATIONS = "all_fei_member_nations"
FEI_INTERNATIONAL = "fei_international"
FEI_LEVEL_PREFIXES = ("CCI", "CIC", "CCIO")


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
    """Return sources covering a region and optional level."""

    normalized_region = region.lower().replace(" ", "_")

    return [
        source
        for source in load_event_sources(path)
        if _status_matches(source, include_planned)
        and ("global" in source.regions or normalized_region in source.regions)
        and _level_matches(source, level)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a country and optional level."""

    normalized_country = country.strip().upper().replace(" ", "_")

    return [
        source
        for source in load_event_sources(path)
        if _status_matches(source, include_planned)
        and _country_matches(source, normalized_country)
        and _level_matches(source, level)
    ]


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


def _status_matches(source: EventSource, include_planned: bool) -> bool:
    statuses = {"active", "planned"} if include_planned else {"active"}
    return source.status in statuses


def _country_matches(source: EventSource, normalized_country: str) -> bool:
    countries = {country.upper() for country in source.countries}
    return (
        ALL_COUNTRIES.upper() in countries
        or ALL_FEI_MEMBER_NATIONS.upper() in countries
        or normalized_country in countries
    )


def _level_matches(source: EventSource, level: str | None) -> bool:
    if level is None:
        return True

    normalized_level = _normalize_level(level)
    levels = {_normalize_level(item) for item in source.event_levels}

    return (
        _normalize_level(ALL_EVENTING_LEVELS) in levels
        or normalized_level in levels
        or (
            _normalize_level(FEI_INTERNATIONAL) in levels
            and _is_fei_international_level(normalized_level)
        )
    )


def _normalize_level(level: str) -> str:
    return level.strip().upper().replace(" ", "_")


def _is_fei_international_level(normalized_level: str) -> bool:
    return (
        normalized_level == _normalize_level(FEI_INTERNATIONAL)
        or normalized_level.startswith(FEI_LEVEL_PREFIXES)
    )
