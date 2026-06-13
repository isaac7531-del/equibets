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
COUNTRY_WILDCARDS = {"all_countries"}
LEVEL_WILDCARDS = {"all_eventing_levels"}


@dataclass(frozen=True)
class CoverageTargets:
    """Country and event-level coverage declared by the source registry."""

    countries: tuple[str, ...]
    event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            event_levels=_string_tuple(values, "event_levels"),
        )


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


@dataclass(frozen=True)
class EventSourceRegistry:
    """Loaded event-results source registry and its coverage metadata."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    priority_regions: tuple[str, ...]
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        coverage_targets = values.get("coverage_targets")
        if not isinstance(coverage_targets, dict):
            raise ValueError("coverage_targets must be an object")

        source_values = values.get("sources")
        if not isinstance(source_values, Iterable) or isinstance(
            source_values, (str, bytes)
        ):
            raise ValueError("sources must be a list of source objects")

        sources = []
        for source_value in source_values:
            if not isinstance(source_value, dict):
                raise ValueError("sources must contain only objects")
            sources.append(EventSource.from_mapping(source_value))

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(coverage_targets),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=tuple(sorted(sources, key=_source_sort_key)),
        )


def load_event_source_registry(
    path: Path | str = DATA_FILE,
) -> EventSourceRegistry:
    """Load the full event source registry including coverage metadata."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, dict):
        raise ValueError("event source registry must be an object")

    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a region and optional event level."""

    normalized_region = region.lower().replace(" ", "_")

    return [
        source
        for source in load_event_sources(path)
        if _has_allowed_status(source, include_planned)
        and _covers_region(source, normalized_region)
        and _covers_level(source, level)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a country and optional event level."""

    normalized_country = _normalize_country(country)

    return [
        source
        for source in load_event_sources(path)
        if _has_allowed_status(source, include_planned)
        and _covers_country(source, normalized_country)
        and _covers_level(source, level)
    ]


def _source_sort_key(source: EventSource) -> tuple[int, bool, str]:
    return (source.priority, source.id != "data_fei", source.id)


def _has_allowed_status(source: EventSource, include_planned: bool) -> bool:
    statuses = {"active", "planned"} if include_planned else {"active"}
    return source.status in statuses


def _covers_region(source: EventSource, normalized_region: str) -> bool:
    return "global" in source.regions or normalized_region in source.regions


def _covers_country(source: EventSource, normalized_country: str) -> bool:
    countries = {_normalize_country(country) for country in source.countries}
    wildcards = {_normalize_country(wildcard) for wildcard in COUNTRY_WILDCARDS}
    return bool(countries & wildcards) or normalized_country in countries


def _covers_level(source: EventSource, level: str | None) -> bool:
    if level is None:
        return True

    levels = {_normalize_level(item) for item in source.event_levels}
    wildcards = {_normalize_level(wildcard) for wildcard in LEVEL_WILDCARDS}
    return bool(levels & wildcards) or _normalize_level(level) in levels


def _normalize_country(country: str) -> str:
    return country.upper().replace(" ", "_").replace("-", "_")


def _normalize_level(level: str) -> str:
    return level.lower().replace(" ", "_").replace("-", "_")


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
