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
class CoverageTargets:
    """Countries and eventing levels the source registry is intended to cover."""

    countries: tuple[str, ...]
    national_event_levels: tuple[str, ...]
    fei_international_event_levels: tuple[str, ...]
    event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            national_event_levels=_string_tuple(values, "national_event_levels"),
            fei_international_event_levels=_string_tuple(
                values,
                "fei_international_event_levels",
            ),
            event_levels=_string_tuple(values, "event_levels"),
        )


@dataclass(frozen=True)
class EventSourceRegistry:
    """Configured event-results source registry."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full source registry, including coverage targets."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    sources = tuple(
        sorted(
            (
                EventSource.from_mapping(_mapping_value(item, "sources item"))
                for item in _required_list(payload, "sources")
            ),
            key=lambda source: (source.priority, source.id != "data_fei", source.id),
        )
    )
    return EventSourceRegistry(
        version=_required_int(payload, "version"),
        primary_source_id=_required_str(payload, "primary_source_id"),
        coverage_goal=_required_str(payload, "coverage_goal"),
        priority_regions=_string_tuple(payload, "priority_regions"),
        coverage_targets=CoverageTargets.from_mapping(
            _required_mapping(payload, "coverage_targets")
        ),
        sources=sources,
    )


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an eventing level while preserving priorities."""

    normalized_level = event_level.lower().replace(" ", "_").replace("-", "_")
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and normalized_level in source.event_levels
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country code or all-country fallback."""

    normalized_country = country.upper()
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and (
            "all_countries" in source.countries
            or "all_fei_member_nations" in source.countries
            or normalized_country in source.countries
        )
    ]


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = region.lower().replace(" ", "_")
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
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


def _required_mapping(values: dict[str, object], key: str) -> dict[str, object]:
    value = values.get(key)
    return _mapping_value(value, key)


def _mapping_value(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _required_list(values: dict[str, object], key: str) -> list[object]:
    value = values.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
