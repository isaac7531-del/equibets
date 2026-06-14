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
    """Country and level targets that the source registry is expected to cover."""

    countries: tuple[str, ...]
    national_event_levels: tuple[str, ...]
    international_event_levels: tuple[str, ...]

    @property
    def all_event_levels(self) -> tuple[str, ...]:
        """Return national and international levels in registry order."""

        return self.national_event_levels + self.international_event_levels

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            national_event_levels=_string_tuple(values, "national_event_levels"),
            international_event_levels=_string_tuple(values, "international_event_levels"),
        )


@dataclass(frozen=True)
class EventSourceRegistry:
    """Source registry metadata plus priority-sorted sources."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        sources = [EventSource.from_mapping(item) for item in _mapping_list(values, "sources")]
        sorted_sources = sorted(
            sources,
            key=lambda source: (source.priority, source.id != "data_fei", source.id),
        )

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            sources=tuple(sorted_sources),
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full source registry and coverage targets."""

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

    normalized_region = _normalize_identifier(region)
    statuses = _statuses(include_planned)

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
    """Return global and country-specific sources for an ISO country code."""

    normalized_country = _normalize_country(country)
    statuses = _statuses(include_planned)

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
    """Return sources that cover an event level identifier."""

    normalized_level = _normalize_level(event_level)
    statuses = _statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_level in {_normalize_level(level) for level in source.event_levels}
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


def _statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _source_covers_country(source: EventSource, normalized_country: str) -> bool:
    normalized_source_countries = {_normalize_country(country) for country in source.countries}
    return (
        "ALL_FEI_MEMBER_NATIONS" in normalized_source_countries
        or normalized_country in normalized_source_countries
    )


def _normalize_country(country: str) -> str:
    return country.strip().replace("-", "_").replace(" ", "_").upper()


def _normalize_level(event_level: str) -> str:
    normalized_level = _normalize_identifier(event_level)
    aliases = {
        "cci1_intro": "cci1_intro",
        "cci1": "cci1",
        "cci2_s": "cci2_short",
        "cci2_short": "cci2_short",
        "cci2_l": "cci2_long",
        "cci2_long": "cci2_long",
        "cci3_s": "cci3_short",
        "cci3_short": "cci3_short",
        "cci3_l": "cci3_long",
        "cci3_long": "cci3_long",
        "cci4_s": "cci4_short",
        "cci4_short": "cci4_short",
        "cci4_l": "cci4_long",
        "cci4_long": "cci4_long",
        "cci5_l": "cci5_long",
        "cci5_long": "cci5_long",
    }
    return aliases.get(normalized_level, normalized_level)


def _normalize_identifier(value: str) -> str:
    return "_".join(part for part in re.split(r"[^a-z0-9]+", value.strip().lower()) if part)
