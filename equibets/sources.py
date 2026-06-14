"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader coverage.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"

_FEI_LEVEL_ALIASES = {
    "cci1_intro": "cci1_intro",
    "cci1_introductory": "cci1_intro",
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


@dataclass(frozen=True)
class CoverageTargets:
    """Reusable country and level groups declared by the source registry."""

    countries: Mapping[str, tuple[str, ...]]
    event_levels: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object] | None) -> "CoverageTargets":
        if values is None:
            return cls(countries={}, event_levels={})
        return cls(
            countries=_string_tuple_mapping(values, "countries"),
            event_levels=_string_tuple_mapping(values, "event_levels"),
        )

    def expand_countries(self, values: Iterable[str]) -> tuple[str, ...]:
        """Expand configured country group tokens into concrete country codes."""

        return _expand_group_values(values, self.countries)

    def expand_event_levels(self, values: Iterable[str]) -> tuple[str, ...]:
        """Expand configured level group tokens into concrete level ids."""

        return _expand_group_values(values, self.event_levels)


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
    def from_mapping(
        cls,
        values: Mapping[str, object],
        *,
        coverage_targets: CoverageTargets | None = None,
    ) -> "EventSource":
        targets = coverage_targets or CoverageTargets.from_mapping(None)
        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            priority=_required_int(values, "priority"),
            scope=_required_str(values, "scope"),
            regions=_string_tuple(values, "regions"),
            countries=targets.expand_countries(_string_tuple(values, "countries")),
            disciplines=_string_tuple(values, "disciplines"),
            event_levels=targets.expand_event_levels(
                _string_tuple(values, "event_levels")
            ),
            source_type=_required_str(values, "source_type"),
            base_url=_optional_str(values, "base_url"),
            status=_required_str(values, "status"),
            notes=_required_str(values, "notes"),
        )


@dataclass(frozen=True)
class EventSourceRegistry:
    """Loaded source registry including coverage metadata and sorted sources."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "EventSourceRegistry":
        coverage_targets = CoverageTargets.from_mapping(
            _optional_mapping(values, "coverage_targets")
        )
        raw_sources = values.get("sources")
        if not isinstance(raw_sources, Iterable) or isinstance(raw_sources, (str, bytes)):
            raise ValueError("sources must be a list of source mappings")

        sources = [
            EventSource.from_mapping(
                _required_mapping(item, "sources item"),
                coverage_targets=coverage_targets,
            )
            for item in raw_sources
        ]
        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=coverage_targets,
            sources=tuple(_sort_sources(sources)),
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full registry, including coverage targets."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    return EventSourceRegistry.from_mapping(_required_mapping(payload, "registry"))


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

    normalized_region = _normalize_region(region)
    statuses = _allowed_statuses(include_planned)

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
    """Return sources covering an FEI/IOC country code such as GBR or USA."""

    normalized_country = country.strip().upper()
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and normalized_country in source.countries
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a normalized event level id."""

    normalized_level = _normalize_event_level(event_level)
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and normalized_level in source.event_levels
    ]


def _sort_sources(sources: Iterable[EventSource]) -> list[EventSource]:
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def _allowed_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_region(region: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", region.lower()).strip("_")


def _normalize_event_level(event_level: str) -> str:
    level = re.sub(r"[^a-z0-9]+", "_", event_level.lower()).strip("_")
    return _FEI_LEVEL_ALIASES.get(level, level)


def _expand_group_values(
    values: Iterable[str],
    groups: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    expanded: list[str] = []
    seen: set[str] = set()
    for value in values:
        for item in groups.get(value, (value,)):
            if item not in seen:
                expanded.append(item)
                seen.add(item)
    return tuple(expanded)


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


def _required_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _optional_mapping(values: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = values.get(key)
    if value is None:
        return None
    return _required_mapping(value, key)


def _string_tuple(values: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _string_tuple_mapping(
    values: Mapping[str, object],
    key: str,
) -> Mapping[str, tuple[str, ...]]:
    value = values.get(key, {})
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be a mapping of lists")

    return {
        group_name: _string_tuple(value, group_name)
        for group_name in sorted(value)
    }
