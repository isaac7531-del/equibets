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
GLOBAL_COUNTRY_TARGET = "all_fei_member_nations"


@dataclass(frozen=True)
class CoverageTargets:
    """Top-level country and event-level coverage goals."""

    countries: tuple[str, ...]
    domestic_event_levels: tuple[str, ...]
    fei_event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            domestic_event_levels=_string_tuple(values, "domestic_event_levels"),
            fei_event_levels=_string_tuple(values, "fei_event_levels"),
        )

    @property
    def event_levels(self) -> tuple[str, ...]:
        """All configured event levels, with domestic levels first."""

        return self.domestic_event_levels + self.fei_event_levels


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
    """A versioned event-source registry and its coverage targets."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    priority_regions: tuple[str, ...]
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        sources_value = values.get("sources")
        if not isinstance(sources_value, Iterable) or isinstance(sources_value, (str, bytes)):
            raise ValueError("sources must be a list of source mappings")

        sources = []
        for source_value in sources_value:
            if not isinstance(source_value, dict):
                raise ValueError("sources must contain only source mappings")
            sources.append(EventSource.from_mapping(source_value))

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=tuple(
                sorted(
                    sources,
                    key=lambda source: (
                        source.priority,
                        source.id != _required_str(values, "primary_source_id"),
                        source.id,
                    ),
                )
            ),
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the versioned event-source registry."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, dict):
        raise ValueError("event source registry must be a JSON object")
    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with the primary source first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = region.lower().replace(" ", "_")
    statuses = {"active", "planned"} if include_planned else {"active"}

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
    """Return sources that cover a country code, including all-country sources."""

    normalized_country = country.strip().upper().replace(" ", "_")
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and (
            normalized_country in source.countries
            or GLOBAL_COUNTRY_TARGET in source.countries
        )
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources that cover an event level."""

    normalized_event_level = _normalize_event_level(event_level)
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_event_level
        in {_normalize_event_level(level) for level in source.event_levels}
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


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _normalize_event_level(event_level: str) -> str:
    normalized = event_level.strip().lower().replace("*", "")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    aliases = {
        "cci_1_intro": "cci_one_star_intro",
        "cci1_intro": "cci_one_star_intro",
        "cci1intro": "cci_one_star_intro",
        "cci1_s": "cci1_short",
        "cci1s": "cci1_short",
        "cci2_s": "cci2_short",
        "cci2s": "cci2_short",
        "cci2_l": "cci2_long",
        "cci2l": "cci2_long",
        "cci3_s": "cci3_short",
        "cci3s": "cci3_short",
        "cci3_l": "cci3_long",
        "cci3l": "cci3_long",
        "cci4_s": "cci4_short",
        "cci4s": "cci4_short",
        "cci4_l": "cci4_long",
        "cci4l": "cci4_long",
        "cci5_l": "cci5_long",
        "cci5l": "cci5_long",
    }
    return aliases.get(normalized, normalized)
