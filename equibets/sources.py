"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader coverage.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"
_PRIMARY_SOURCE_ID = "data_fei"
_ALL_COUNTRIES = "all_fei_member_nations"
_ALL_DOMESTIC_LEVELS = "all_national_and_regional_levels"
_ALL_INTERNATIONAL_LEVELS = "all_fei_international_levels"

_EVENT_LEVEL_ALIASES = {
    "cci_intro": "cci_intro",
    "cci1": "cci1_short",
    "cci1_s": "cci1_short",
    "cci1_short": "cci1_short",
    "cci2": "cci2_short",
    "cci2_s": "cci2_short",
    "cci2_short": "cci2_short",
    "cci2_l": "cci2_long",
    "cci2_long": "cci2_long",
    "cci3": "cci3_short",
    "cci3_s": "cci3_short",
    "cci3_short": "cci3_short",
    "cci3_l": "cci3_long",
    "cci3_long": "cci3_long",
    "cci4": "cci4_short",
    "cci4_s": "cci4_short",
    "cci4_short": "cci4_short",
    "cci4_l": "cci4_long",
    "cci4_long": "cci4_long",
    "cci5": "cci5_long",
    "cci5_l": "cci5_long",
    "cci5_long": "cci5_long",
}


@dataclass(frozen=True)
class CoverageTargets:
    """Country and level coverage promised by the source registry."""

    countries: tuple[str, ...]
    domestic_event_levels: tuple[str, ...]
    international_event_levels: tuple[str, ...]

    @property
    def event_levels(self) -> tuple[str, ...]:
        return self.domestic_event_levels + self.international_event_levels

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            domestic_event_levels=_string_tuple(values, "domestic_event_levels"),
            international_event_levels=_string_tuple(values, "international_event_levels"),
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
    """Versioned source registry plus declared coverage targets."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    priority_regions: tuple[str, ...]
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        primary_source_id = _required_str(values, "primary_source_id")
        source_values = values.get("sources")
        if not isinstance(source_values, Iterable) or isinstance(source_values, (str, bytes)):
            raise ValueError("sources must be a list of source mappings")

        sources = tuple(
            sorted(
                (EventSource.from_mapping(_required_mapping(item, "sources item")) for item in source_values),
                key=lambda source: (
                    source.priority,
                    source.id != primary_source_id,
                    source.id,
                ),
            )
        )
        if not any(source.id == primary_source_id for source in sources):
            raise ValueError("primary_source_id must match a configured source")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=primary_source_id,
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values.get("coverage_targets"), "coverage_targets")
            ),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=sources,
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the versioned source registry."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = region.lower().replace(" ", "_")
    statuses = _source_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an FEI country code while preserving priority."""

    normalized_country = _normalize_country(country)
    statuses = _source_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and _source_covers_country(source, normalized_country)
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level token or common FEI level label."""

    registry = load_event_source_registry(path)
    normalized_event_level = _canonical_event_level(event_level)
    statuses = _source_statuses(include_planned)

    return [
        source
        for source in registry.sources
        if source.status in statuses
        and normalized_event_level in _expanded_event_levels(source, registry.coverage_targets)
    ]


def _source_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _source_covers_country(source: EventSource, country: str) -> bool:
    return country in source.countries or _ALL_COUNTRIES in source.countries


def _expanded_event_levels(
    source: EventSource,
    coverage_targets: CoverageTargets,
) -> set[str]:
    event_levels = {_canonical_event_level(level) for level in source.event_levels}
    if _ALL_DOMESTIC_LEVELS in source.event_levels:
        event_levels.update(_canonical_event_level(level) for level in coverage_targets.domestic_event_levels)
    if _ALL_INTERNATIONAL_LEVELS in source.event_levels:
        event_levels.update(
            _canonical_event_level(level) for level in coverage_targets.international_event_levels
        )
    return event_levels


def _canonical_event_level(event_level: str) -> str:
    normalized = _normalize_token(event_level)
    return _EVENT_LEVEL_ALIASES.get(normalized, normalized)


def _normalize_country(country: str) -> str:
    normalized_country = country.strip().upper().replace(" ", "_")
    if not normalized_country:
        raise ValueError("country must be a non-empty string")
    return normalized_country


def _normalize_token(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not normalized:
        raise ValueError("event_level must be a non-empty string")
    return normalized


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


def _required_mapping(value: object, key: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
