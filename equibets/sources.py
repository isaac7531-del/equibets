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

    if not isinstance(payload, dict):
        raise ValueError("event source registry must be a JSON object")

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

    return [
        source
        for source in load_event_sources(path)
        if _has_allowed_status(source, include_planned)
        and _covers_event_level(source, event_level)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a country code and optional eventing level."""

    normalized_country = _normalized_country(country)

    return [
        source
        for source in load_event_sources(path)
        if _has_allowed_status(source, include_planned)
        and _covers_country(source, normalized_country)
        and _covers_optional_event_level(source, level)
    ]


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a region and optional eventing level."""

    normalized_region = _normalized_region(region)

    return [
        source
        for source in load_event_sources(path)
        if _has_allowed_status(source, include_planned)
        and _covers_region(source, normalized_region)
        and _covers_optional_event_level(source, level)
    ]


def _has_allowed_status(source: EventSource, include_planned: bool) -> bool:
    statuses = {"active", "planned"} if include_planned else {"active"}
    return source.status in statuses


def _covers_country(source: EventSource, normalized_country: str) -> bool:
    countries = {_normalized_country(country) for country in source.countries}
    country_wildcards = {"ALL_COUNTRIES", "ALL_FEI_MEMBER_NATIONS"}
    return bool(countries & country_wildcards) or normalized_country in countries


def _covers_region(source: EventSource, normalized_region: str) -> bool:
    return "global" in source.regions or normalized_region in source.regions


def _covers_optional_event_level(source: EventSource, event_level: str | None) -> bool:
    return event_level is None or _covers_event_level(source, event_level)


def _covers_event_level(source: EventSource, event_level: str) -> bool:
    return _normalized_event_level(event_level) in {
        _normalized_event_level(level) for level in source.event_levels
    }


def _normalized_country(country: str) -> str:
    return country.strip().upper().replace("-", "_").replace(" ", "_")


def _normalized_region(region: str) -> str:
    return region.strip().lower().replace("-", "_").replace(" ", "_")


def _normalized_event_level(event_level: str) -> str:
    normalized = (
        event_level.strip()
        .lower()
        .replace("*", "")
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )
    while "__" in normalized:
        normalized = normalized.replace("__", "_")

    aliases = {
        "cci1intro": "cci1_intro",
        "cci1_intro": "cci1_intro",
        "cci2_l": "cci2_long",
        "cci2_long": "cci2_long",
        "cci2_s": "cci2_short",
        "cci2_short": "cci2_short",
        "cci3_l": "cci3_long",
        "cci3_long": "cci3_long",
        "cci3_s": "cci3_short",
        "cci3_short": "cci3_short",
        "cci4_l": "cci4_long",
        "cci4_long": "cci4_long",
        "cci4_s": "cci4_short",
        "cci4_short": "cci4_short",
        "cci5_l": "cci5_long",
        "cci5_long": "cci5_long",
        "championships": "championship",
    }
    return aliases.get(normalized, normalized)


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
