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
ALL_FEI_COUNTRIES = "all_fei_member_nations"
ALL_NATIONAL_LEVELS = "all_national_and_regional_levels"
ALL_FEI_LEVELS = "all_fei_international_levels"


COUNTRY_REGION_HINTS: dict[str, tuple[str, ...]] = {
    "ARG": ("south_america",),
    "AUS": ("australia", "oceania"),
    "BRA": ("south_america",),
    "CAN": ("north_america",),
    "CHL": ("south_america",),
    "EGY": ("africa", "middle_east"),
    "GBR": ("uk", "europe"),
    "JPN": ("asia",),
    "KSA": ("middle_east", "asia"),
    "MEX": ("north_america",),
    "NZL": ("new_zealand", "oceania"),
    "QAT": ("middle_east", "asia"),
    "UAE": ("middle_east", "asia"),
    "USA": ("usa", "north_america"),
    "ZAF": ("africa",),
}


@dataclass(frozen=True)
class CoverageTargets:
    """The all-country and all-level coverage goals for the source registry."""

    countries: tuple[str, ...]
    national_and_regional_levels: tuple[str, ...]
    fei_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            national_and_regional_levels=_string_tuple(
                values,
                "national_and_regional_levels",
            ),
            fei_levels=_string_tuple(values, "fei_levels"),
        )

    @property
    def all_event_levels(self) -> tuple[str, ...]:
        """Return every normalized event-level target in priority order."""

        return self.fei_levels + self.national_and_regional_levels


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
    """Versioned source registry and coverage target metadata."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        primary_source_id = _required_str(values, "primary_source_id")
        sources = [
            EventSource.from_mapping(_mapping_item(item, "sources"))
            for item in _required_list(values, "sources")
        ]
        sorted_sources = tuple(
            sorted(
                sources,
                key=lambda source: (
                    source.priority,
                    source.id != primary_source_id,
                    source.id,
                ),
            )
        )
        return cls(
            version=_required_int(values, "version"),
            primary_source_id=primary_source_id,
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            sources=sorted_sources,
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full versioned event-source registry."""

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

    normalized_region = region.lower().replace(" ", "_")
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
    """Return sources that can contribute results for a country code."""

    normalized_country = country.strip().upper()
    statuses = _allowed_statuses(include_planned)

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
    """Return sources that can contribute results for an eventing level."""

    registry = load_event_source_registry(path)
    normalized_level = _normalize_token(event_level)
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in registry.sources
        if source.status in statuses
        and _source_covers_event_level(
            source,
            normalized_level,
            registry.coverage_targets,
        )
    ]


def _source_covers_country(source: EventSource, country: str) -> bool:
    if country in source.countries or ALL_FEI_COUNTRIES in source.countries:
        return True

    country_regions = COUNTRY_REGION_HINTS.get(country, ())
    for source_country in source.countries:
        region = _region_from_country_group(source_country)
        if region in country_regions:
            return True
    return False


def _source_covers_event_level(
    source: EventSource,
    normalized_level: str,
    coverage_targets: CoverageTargets,
) -> bool:
    national_levels = {
        _normalize_token(level)
        for level in coverage_targets.national_and_regional_levels
    }
    fei_levels = {_normalize_token(level) for level in coverage_targets.fei_levels}

    for source_level in source.event_levels:
        normalized_source_level = _normalize_token(source_level)
        if normalized_source_level == normalized_level:
            return True
        if source_level == ALL_NATIONAL_LEVELS and normalized_level in national_levels:
            return True
        if source_level == ALL_FEI_LEVELS and normalized_level in fei_levels:
            return True
    return False


def _region_from_country_group(country_group: str) -> str | None:
    match = re.fullmatch(r"all_fei_(.+)_member_nations", country_group)
    if match is None or country_group == ALL_FEI_COUNTRIES:
        return None
    return match.group(1)


def _normalize_token(value: str) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "_",
        value.lower().replace("*", ""),
    ).strip("_")
    aliases = {
        "cci1_i": "cci1_intro",
        "cci1_s": "cci1_short",
        "cci2_s": "cci2_short",
        "cci2_l": "cci2_long",
        "cci3_s": "cci3_short",
        "cci3_l": "cci3_long",
        "cci4_s": "cci4_short",
        "cci4_l": "cci4_long",
        "cci5_s": "cci5_short",
        "cci5_l": "cci5_long",
    }
    return aliases.get(normalized, normalized)


def _allowed_statuses(include_planned: bool) -> set[str]:
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


def _required_list(values: dict[str, object], key: str) -> list[object]:
    value = values.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


def _mapping_item(value: object, key: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{key} must contain only objects")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
