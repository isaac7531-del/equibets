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
class CoverageTargets:
    """The countries and event levels this registry is expected to cover."""

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
    """Versioned event-results source registry."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        raw_sources = values.get("sources")
        if not isinstance(raw_sources, list):
            raise ValueError("sources must be a list")

        raw_coverage_targets = values.get("coverage_targets")
        if not isinstance(raw_coverage_targets, dict):
            raise ValueError("coverage_targets must be an object")

        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in raw_sources),
                key=lambda source: (
                    source.priority,
                    source.id != values.get("primary_source_id"),
                    source.id,
                ),
            )
        )

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(raw_coverage_targets),
            sources=sources,
        )

    def sources_for_region(
        self,
        region: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = _normalize_token(region)
        statuses = _included_statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses
            and ("global" in source.regions or normalized_region in source.regions)
        ]

    def sources_for_country(
        self,
        country: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources explicitly covering a country or all FEI member nations."""

        normalized_country = country.upper()
        statuses = _included_statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses
            and (
                normalized_country in source.countries
                or "all_fei_member_nations" in source.countries
            )
        ]

    def sources_for_event_level(
        self,
        event_level: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources covering an event level while preserving source priority."""

        normalized_event_level = _normalize_token(event_level)
        statuses = _included_statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses and normalized_event_level in source.event_levels
        ]


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the versioned event source registry."""

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

    return load_event_source_registry(path).sources_for_region(
        region,
        include_planned=include_planned,
    )


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


def _included_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_token(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


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
