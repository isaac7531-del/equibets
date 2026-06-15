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
    """Declared country and event-level goals for the source registry."""

    countries: tuple[str, ...]
    domestic_event_levels: tuple[str, ...]
    international_event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            domestic_event_levels=_string_tuple(values, "domestic_event_levels"),
            international_event_levels=_string_tuple(values, "international_event_levels"),
        )

    @property
    def all_event_levels(self) -> tuple[str, ...]:
        """Return domestic and international levels without duplicates."""

        return _dedupe_preserving_order(
            (*self.domestic_event_levels, *self.international_event_levels)
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
    """Loaded source registry and its declared coverage goals."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    priority_regions: tuple[str, ...]
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        coverage_targets = CoverageTargets.from_mapping(
            _required_mapping(values, "coverage_targets")
        )
        raw_sources = values.get("sources")
        if not isinstance(raw_sources, Iterable) or isinstance(raw_sources, (str, bytes)):
            raise ValueError("sources must be a list of source mappings")

        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in raw_sources if isinstance(item, dict)),
                key=lambda source: (
                    source.priority,
                    source.id != _required_str(values, "primary_source_id"),
                    source.id,
                ),
            )
        )
        if len(sources) != len(tuple(raw_sources)):
            raise ValueError("sources must contain only source mappings")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=coverage_targets,
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=sources,
        )

    def filtered_sources(self, *, include_planned: bool = True) -> tuple[EventSource, ...]:
        """Return sources filtered by active/planned status."""

        statuses = {"active", "planned"} if include_planned else {"active"}
        return tuple(source for source in self.sources if source.status in statuses)

    def sources_for_region(
        self,
        region: str,
        *,
        include_planned: bool = True,
    ) -> tuple[EventSource, ...]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = _normalize_token(region)
        return tuple(
            source
            for source in self.filtered_sources(include_planned=include_planned)
            if "global" in source.regions or normalized_region in source.regions
        )

    def sources_for_country(
        self,
        country: str,
        *,
        include_planned: bool = True,
    ) -> tuple[EventSource, ...]:
        """Return global and country-specific sources for an FEI country code."""

        normalized_country = country.strip().upper()
        return tuple(
            source
            for source in self.filtered_sources(include_planned=include_planned)
            if _source_covers_country(source, normalized_country)
        )

    def sources_for_event_level(
        self,
        event_level: str,
        *,
        include_planned: bool = True,
    ) -> tuple[EventSource, ...]:
        """Return sources configured to collect a normalized event level."""

        normalized_level = _normalize_token(event_level)
        return tuple(
            source
            for source in self.filtered_sources(include_planned=include_planned)
            if normalized_level in source.event_levels
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the source registry sorted by priority, with the primary source first."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with the configured primary source first."""

    return list(load_event_source_registry(path).sources)


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    registry = load_event_source_registry(path)
    return list(registry.sources_for_region(region, include_planned=include_planned))


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return global and country-specific sources for an FEI country code."""

    registry = load_event_source_registry(path)
    return list(registry.sources_for_country(country, include_planned=include_planned))


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources configured to collect a normalized event level."""

    registry = load_event_source_registry(path)
    return list(
        registry.sources_for_event_level(event_level, include_planned=include_planned)
    )


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
        raise ValueError(f"{key} must be a mapping")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _source_covers_country(source: EventSource, country: str) -> bool:
    country_tokens = {configured_country.upper() for configured_country in source.countries}
    return "ALL_FEI_MEMBER_NATIONS" in country_tokens or country in country_tokens


def _dedupe_preserving_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    items: list[str] = []
    for value in values:
        if value not in seen:
            items.append(value)
            seen.add(value)
    return tuple(items)
