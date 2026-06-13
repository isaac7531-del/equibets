"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader coverage.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"


@dataclass(frozen=True)
class CoverageTargets:
    """Coverage goals that every source entry is measured against."""

    countries: tuple[str, ...]
    regions: tuple[str, ...]
    national_event_levels: tuple[str, ...]
    international_event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            regions=_string_tuple(values, "regions"),
            national_event_levels=_string_tuple(values, "national_event_levels"),
            international_event_levels=_string_tuple(
                values, "international_event_levels"
            ),
        )

    @property
    def event_levels(self) -> tuple[str, ...]:
        return self.national_event_levels + self.international_event_levels


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
    def from_mapping(cls, values: Mapping[str, object]) -> "EventSource":
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
    """Versioned event-source registry with declared coverage targets."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "EventSourceRegistry":
        sources = tuple(
            sorted(
                (
                    EventSource.from_mapping(item)
                    for item in _mapping_sequence(values, "sources")
                ),
                key=_source_sort_key,
            )
        )
        registry = cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            sources=sources,
        )
        _validate_registry(registry)
        return registry


def load_event_source_registry(
    path: Path | str = DATA_FILE,
) -> EventSourceRegistry:
    """Load and validate the versioned event-source registry."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, Mapping):
        raise ValueError("event source registry must be a JSON object")
    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_event_level(
    level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources that cover an event level, preserving source priority."""

    normalized_level = _normalize_identifier(level)
    statuses = _allowed_statuses(include_planned)
    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and normalized_level in source.event_levels
    ]


def sources_for_country(
    country: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country, optionally constrained by event level."""

    normalized_country = _normalize_country(country)
    normalized_level = _normalize_identifier(level) if level is not None else None
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and _source_matches_country(source, normalized_country)
        and _source_matches_level(source, normalized_level)
    ]


def sources_for_region(
    region: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = _normalize_identifier(region)
    normalized_level = _normalize_identifier(level) if level is not None else None
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
        and _source_matches_level(source, normalized_level)
    ]


def _allowed_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _source_matches_country(source: EventSource, country: str) -> bool:
    return country in source.countries or "all_fei_member_nations" in source.countries


def _source_matches_level(source: EventSource, level: str | None) -> bool:
    return level is None or level in source.event_levels


def _source_sort_key(source: EventSource) -> tuple[int, bool, str]:
    return (source.priority, source.id != "data_fei", source.id)


def _validate_registry(registry: EventSourceRegistry) -> None:
    if registry.version < 2:
        raise ValueError("event source registry version must be at least 2")

    source_ids = [source.id for source in registry.sources]
    duplicate_ids = _duplicates(source_ids)
    if duplicate_ids:
        raise ValueError(f"duplicate source ids: {', '.join(duplicate_ids)}")
    if registry.primary_source_id not in source_ids:
        raise ValueError("primary_source_id must match a configured source")

    target_regions = set(registry.coverage_targets.regions)
    target_levels = set(registry.coverage_targets.event_levels)
    national_levels = set(registry.coverage_targets.national_event_levels)
    international_levels = set(registry.coverage_targets.international_event_levels)

    for source in registry.sources:
        if source.priority < 0:
            raise ValueError(f"{source.id} priority must be non-negative")
        if source.scope not in {"international", "national"}:
            raise ValueError(f"{source.id} has unsupported scope {source.scope!r}")
        if source.status not in {"active", "planned"}:
            raise ValueError(f"{source.id} has unsupported status {source.status!r}")
        if "eventing" not in source.disciplines:
            raise ValueError(f"{source.id} must include eventing discipline")
        if not set(source.event_levels).issubset(target_levels):
            raise ValueError(f"{source.id} contains event levels outside coverage targets")
        if source.scope == "national" and not set(source.event_levels).issubset(
            national_levels
        ):
            raise ValueError(f"{source.id} national source includes non-national levels")
        if source.scope == "international" and not set(source.event_levels).issubset(
            international_levels
        ):
            raise ValueError(
                f"{source.id} international source includes non-international levels"
            )
        if not all(
            region == "global" or region in target_regions
            for region in source.regions
        ):
            raise ValueError(f"{source.id} contains regions outside coverage targets")
        if not all(
            _is_country_code(country) or _is_country_group(country)
            for country in source.countries
        ):
            raise ValueError(f"{source.id} contains invalid country coverage values")

    primary_source = next(
        source for source in registry.sources if source.id == registry.primary_source_id
    )
    if set(primary_source.event_levels) != international_levels:
        raise ValueError("primary source must cover every international event level")


def _duplicates(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        if item in seen:
            duplicates.add(item)
        seen.add(item)
    return sorted(duplicates)


def _is_country_code(value: str) -> bool:
    return len(value) == 3 and value.isalpha() and value.isupper()


def _is_country_group(value: str) -> bool:
    return value.startswith("all_fei_") and value.endswith("_member_nations")


def _normalize_country(value: str) -> str:
    normalized = _normalize_identifier(value)
    if _is_country_group(normalized):
        return normalized
    return normalized.upper()


def _normalize_identifier(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_").replace("/", "_")


def _required_str(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(values: Mapping[str, object], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be null or a non-empty string")
    return value


def _required_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _required_mapping(values: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = values.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


def _mapping_sequence(
    values: Mapping[str, object], key: str
) -> tuple[Mapping[str, object], ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, Mapping)):
        raise ValueError(f"{key} must be a list of objects")

    items = tuple(value)
    if not all(isinstance(item, Mapping) for item in items):
        raise ValueError(f"{key} must contain only objects")
    return items


def _string_tuple(values: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
