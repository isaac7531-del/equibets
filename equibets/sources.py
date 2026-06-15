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
    """Countries and event levels the registry is expected to cover."""

    countries: tuple[str, ...]
    domestic_event_levels: tuple[str, ...]
    international_event_levels: tuple[str, ...]

    @property
    def all_event_levels(self) -> tuple[str, ...]:
        """Return every configured event level with duplicates removed."""

        return tuple(
            dict.fromkeys(
                (*self.domestic_event_levels, *self.international_event_levels)
            )
        )

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            domestic_event_levels=_string_tuple(values, "domestic_event_levels"),
            international_event_levels=_string_tuple(
                values,
                "international_event_levels",
            ),
        )


@dataclass(frozen=True)
class EventSourceRegistry:
    """Loaded source registry, sorted by source priority."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        source_values = values.get("sources")
        if not isinstance(source_values, list):
            raise ValueError("sources must be a list of source mappings")

        coverage_target_values = values.get("coverage_targets")
        if not isinstance(coverage_target_values, dict):
            raise ValueError("coverage_targets must be an object")
        if not all(isinstance(item, dict) for item in source_values):
            raise ValueError("sources must contain only source mappings")

        primary_source_id = _required_str(values, "primary_source_id")
        sources = sorted(
            (EventSource.from_mapping(item) for item in source_values),
            key=lambda source: (
                source.priority,
                source.id != primary_source_id,
                source.id,
            ),
        )

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=primary_source_id,
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(coverage_target_values),
            sources=tuple(sources),
        )

    def sources_for_region(
        self, region: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = _normalize_token(region)
        return [
            source
            for source in self.sources
            if _has_status(source, include_planned)
            and (
                "global" in source.regions
                or normalized_region
                in {_normalize_token(item) for item in source.regions}
            )
        ]

    def sources_for_country(
        self, country: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return exact-country and all-country sources for an FEI country code."""

        normalized_country = country.strip().upper().replace(" ", "_")
        return [
            source
            for source in self.sources
            if _has_status(source, include_planned)
            and (
                "all_fei_member_nations" in source.countries
                or normalized_country
                in {item.strip().upper().replace(" ", "_") for item in source.countries}
            )
        ]

    def sources_for_event_level(
        self, event_level: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources configured to collect a given event level."""

        normalized_event_level = _normalize_token(event_level)
        return [
            source
            for source in self.sources
            if _has_status(source, include_planned)
            and normalized_event_level
            in {_normalize_token(item) for item in source.event_levels}
        ]


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full event-results source registry."""

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
    """Return sources covering a country while preserving global priorities."""

    return load_event_source_registry(path).sources_for_country(
        country,
        include_planned=include_planned,
    )


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level while preserving global priorities."""

    return load_event_source_registry(path).sources_for_event_level(
        event_level,
        include_planned=include_planned,
    )


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    return load_event_source_registry(path).sources_for_region(
        region,
        include_planned=include_planned,
    )


def _has_status(source: EventSource, include_planned: bool) -> bool:
    statuses = {"active", "planned"} if include_planned else {"active"}
    return source.status in statuses


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


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
