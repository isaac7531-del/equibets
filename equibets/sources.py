"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader all-country and all-level coverage.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"


@dataclass(frozen=True)
class CoverageTargets:
    """Named coverage goals that sources can reference."""

    countries: tuple[str, ...]
    event_levels: dict[str, tuple[str, ...]]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            event_levels=_string_tuple_mapping(values, "event_levels"),
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
    """Versioned registry of event-result sources and coverage targets."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        coverage_targets = values.get("coverage_targets")
        if not isinstance(coverage_targets, dict):
            raise ValueError("coverage_targets must be an object")

        sources = values.get("sources")
        if not isinstance(sources, Iterable) or isinstance(sources, (str, bytes)):
            raise ValueError("sources must be a list of source objects")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(coverage_targets),
            sources=tuple(
                sorted(
                    (EventSource.from_mapping(item) for item in sources if isinstance(item, dict)),
                    key=_source_sort_key,
                )
            ),
        )

    def expanded_event_levels(self, source: EventSource) -> tuple[str, ...]:
        """Resolve source event-level aliases into concrete level tokens."""

        levels: list[str] = []
        seen: set[str] = set()
        for level in source.event_levels:
            for expanded_level in self.coverage_targets.event_levels.get(level, (level,)):
                if expanded_level not in seen:
                    levels.append(expanded_level)
                    seen.add(expanded_level)
        return tuple(levels)


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full event-source registry."""

    with Path(path).open(encoding="utf-8") as source_file:
        return EventSourceRegistry.from_mapping(json.load(source_file))


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an FEI country code or all-country target."""

    normalized_country = country.strip().upper()
    statuses = _included_statuses(include_planned)
    registry = load_event_source_registry(path)

    return [
        source
        for source in registry.sources
        if source.status in statuses
        and (
            normalized_country in source.countries
            or country in source.countries
            or any(target in source.countries for target in registry.coverage_targets.countries)
        )
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a concrete eventing level."""

    normalized_level = _event_level_key(event_level)
    statuses = _included_statuses(include_planned)
    registry = load_event_source_registry(path)

    return [
        source
        for source in registry.sources
        if source.status in statuses
        and normalized_level
        in {_event_level_key(level) for level in registry.expanded_event_levels(source)}
    ]


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = region.lower().replace(" ", "_")
    statuses = _included_statuses(include_planned)

    return [
        source
        for source in load_event_source_registry(path).sources
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


def _string_tuple_mapping(values: dict[str, object], key: str) -> dict[str, tuple[str, ...]]:
    value = values.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object of string lists")

    items: dict[str, tuple[str, ...]] = {}
    for item_key, item_value in value.items():
        if not isinstance(item_key, str) or not item_key:
            raise ValueError(f"{key} keys must be non-empty strings")
        if not isinstance(item_value, Iterable) or isinstance(item_value, (str, bytes)):
            raise ValueError(f"{key}.{item_key} must be a list of strings")
        levels = tuple(item_value)
        if not all(isinstance(level, str) and level for level in levels):
            raise ValueError(f"{key}.{item_key} must contain only non-empty strings")
        items[item_key] = levels
    return items


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _included_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _source_sort_key(source: EventSource) -> tuple[int, bool, str]:
    return (source.priority, source.id != "data_fei", source.id)


def _event_level_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower().replace("*", "")).strip("_")
    normalized = re.sub(r"_+", "_", normalized)
    return _EVENT_LEVEL_ALIASES.get(normalized, normalized)


_EVENT_LEVEL_ALIASES = {
    "cci_intro": "cci_intro",
    "cci1intro": "cci1_intro",
    "cci1_intro": "cci1_intro",
    "cci1_i": "cci1_intro",
    "cci1i": "cci1_intro",
    "cci1s": "cci1_short",
    "cci1_s": "cci1_short",
    "cci1_short": "cci1_short",
    "cci2s": "cci2_short",
    "cci2_s": "cci2_short",
    "cci2_short": "cci2_short",
    "cci2l": "cci2_long",
    "cci2_l": "cci2_long",
    "cci2_long": "cci2_long",
    "cci3s": "cci3_short",
    "cci3_s": "cci3_short",
    "cci3_short": "cci3_short",
    "cci3l": "cci3_long",
    "cci3_l": "cci3_long",
    "cci3_long": "cci3_long",
    "cci4s": "cci4_short",
    "cci4_s": "cci4_short",
    "cci4_short": "cci4_short",
    "cci4l": "cci4_long",
    "cci4_l": "cci4_long",
    "cci4_long": "cci4_long",
    "cci5l": "cci5_long",
    "cci5_l": "cci5_long",
    "cci5_long": "cci5_long",
}
