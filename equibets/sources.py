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
ALL_FEI_MEMBER_NATIONS = "all_fei_member_nations"


@dataclass(frozen=True)
class CoverageTargets:
    """Declared country, region, and event-level coverage goals."""

    countries: tuple[str, ...]
    regions: tuple[str, ...]
    national_event_levels: tuple[str, ...]
    fei_international_event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            regions=_string_tuple(values, "regions"),
            national_event_levels=_string_tuple(values, "national_event_levels"),
            fei_international_event_levels=_string_tuple(
                values, "fei_international_event_levels"
            ),
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
    """The complete source registry and its coverage metadata."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        sources = _sorted_sources(
            EventSource.from_mapping(item) for item in _mapping_tuple(values, "sources")
        )

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            sources=tuple(sources),
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the complete source registry, including coverage metadata."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_region(
    region: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = _normalize_identifier(region)
    registry = load_event_source_registry(path)

    return [
        source
        for source in registry.sources
        if _status_matches(source, include_planned)
        and ("global" in source.regions or normalized_region in source.regions)
        and _source_matches_level(source, level, registry.coverage_targets)
    ]


def sources_for_country(
    country: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an FEI country code and optional event level."""

    normalized_country = country.strip().upper()
    registry = load_event_source_registry(path)

    return [
        source
        for source in registry.sources
        if _status_matches(source, include_planned)
        and _source_matches_country(source, normalized_country)
        and _source_matches_level(source, level, registry.coverage_targets)
    ]


def sources_for_event_level(
    level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level across all configured countries."""

    registry = load_event_source_registry(path)

    return [
        source
        for source in registry.sources
        if _status_matches(source, include_planned)
        and _source_matches_level(source, level, registry.coverage_targets)
    ]


def _sorted_sources(sources: Iterable[EventSource]) -> list[EventSource]:
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def _status_matches(source: EventSource, include_planned: bool) -> bool:
    statuses = {"active", "planned"} if include_planned else {"active"}
    return source.status in statuses


def _source_matches_country(source: EventSource, country: str) -> bool:
    return ALL_FEI_MEMBER_NATIONS in source.countries or country in source.countries


def _source_matches_level(
    source: EventSource,
    level: str | None,
    coverage_targets: CoverageTargets,
) -> bool:
    if level is None:
        return True

    return bool(
        set(source.event_levels).intersection(
            _expanded_event_levels(level, coverage_targets)
        )
    )


def _expanded_event_levels(
    level: str,
    coverage_targets: CoverageTargets,
) -> tuple[str, ...]:
    normalized_level = _normalize_level(level)
    aliases = {
        "fei_international": coverage_targets.fei_international_event_levels,
        "international": coverage_targets.fei_international_event_levels,
        "national": coverage_targets.national_event_levels,
        "regional": coverage_targets.national_event_levels,
        "all_national_event_levels": coverage_targets.national_event_levels,
        "all_fei_international_event_levels": (
            coverage_targets.fei_international_event_levels
        ),
        "cci1": ("cci1_intro",),
        "cci1_intro": ("cci1_intro",),
        "cci2_s": ("cci2_short",),
        "cci2_short": ("cci2_short",),
        "cci2_l": ("cci2_long",),
        "cci2_long": ("cci2_long",),
        "cci3_s": ("cci3_short",),
        "cci3_short": ("cci3_short",),
        "cci3_l": ("cci3_long",),
        "cci3_long": ("cci3_long",),
        "cci4_s": ("cci4_short",),
        "cci4_short": ("cci4_short",),
        "cci4_l": ("cci4_long",),
        "cci4_long": ("cci4_long",),
        "cci5_l": ("cci5_long",),
        "cci5_long": ("cci5_long",),
    }
    return aliases.get(normalized_level, (normalized_level,))


def _normalize_identifier(value: str) -> str:
    return value.strip().lower().replace("/", "_").replace(" ", "_")


def _normalize_level(level: str) -> str:
    normalized = _normalize_identifier(level)
    return normalized.replace("*", "").replace("-", "_")


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


def _mapping_tuple(values: dict[str, object], key: str) -> tuple[dict[str, object], ...]:
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
