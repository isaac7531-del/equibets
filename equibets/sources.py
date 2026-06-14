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
    """Country and level coverage promised by the source registry."""

    countries: tuple[str, ...]
    national_event_levels: tuple[str, ...]
    international_event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            national_event_levels=_string_tuple(values, "national_event_levels"),
            international_event_levels=_string_tuple(values, "international_event_levels"),
        )

    @property
    def all_event_levels(self) -> tuple[str, ...]:
        """Return every configured national and international event level."""

        return self.national_event_levels + self.international_event_levels


@dataclass(frozen=True)
class EventSourceRegistry:
    """Versioned event-result source configuration."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in _mapping_list(values, "sources")),
                key=lambda source: (source.priority, source.id != "data_fei", source.id),
            )
        )
        primary_source_id = _required_str(values, "primary_source_id")
        if primary_source_id not in {source.id for source in sources}:
            raise ValueError("primary_source_id must refer to a configured source")
        if len({source.id for source in sources}) != len(sources):
            raise ValueError("source ids must be unique")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=primary_source_id,
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            sources=sources,
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the versioned event-source registry."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, dict):
        raise ValueError("event source registry must be a JSON object")
    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources that explicitly cover a country or all FEI nations."""

    normalized_country = country.strip().upper()
    statuses = _statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and (
            "all_fei_member_nations" in source.countries
            or normalized_country in source.countries
        )
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources that cover a specific event level."""

    normalized_level = _normalize_event_level(event_level)
    statuses = _statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and (
            normalized_level in source.event_levels
            or (normalized_level in {"national", "regional"} and source.scope == "national")
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
    statuses = _statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
    ]


def _statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


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
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _mapping_list(values: dict[str, object], key: str) -> tuple[dict[str, object], ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of objects")

    items = tuple(value)
    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"{key} must contain only objects")
    return items


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _normalize_event_level(event_level: str) -> str:
    normalized = event_level.strip().lower()
    normalized = normalized.replace("*", "_star")
    for separator in (" ", "-", "/"):
        normalized = normalized.replace(separator, "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")

    return {
        "cci1_star_intro": "cci1_intro",
        "cci1_introductory": "cci1_intro",
        "cci2_star_s": "cci2_star_short",
        "cci2_star_l": "cci2_star_long",
        "cci3_star_s": "cci3_star_short",
        "cci3_star_l": "cci3_star_long",
        "cci4_star_s": "cci4_star_short",
        "cci4_star_l": "cci4_star_long",
        "cci5_star_l": "cci5_star_long",
        "one_star": "national_one_star",
        "two_star": "national_two_star",
        "three_star": "national_three_star",
        "four_star": "national_four_star",
        "five_star": "national_five_star",
    }.get(normalized, normalized)
