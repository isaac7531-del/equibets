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
ALL_FEI_MEMBER_NATIONS = "all_fei_member_nations"

COUNTRY_REGION_HINTS = {
    "AUS": ("australia", "oceania"),
    "GBR": ("uk", "europe"),
    "NZL": ("new_zealand", "oceania"),
    "USA": ("usa", "north_america"),
}


@dataclass(frozen=True)
class CoverageTargets:
    """Coverage goals declared by the event-source registry."""

    countries: tuple[str, ...]
    fei_international_levels: tuple[str, ...]
    national_event_levels: tuple[str, ...]
    coverage_regions: tuple[str, ...]
    priority_country_regions: tuple[str, ...]

    @property
    def event_levels(self) -> tuple[str, ...]:
        return self.fei_international_levels + self.national_event_levels

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            fei_international_levels=_string_tuple(values, "fei_international_levels"),
            national_event_levels=_string_tuple(values, "national_event_levels"),
            coverage_regions=_string_tuple(values, "coverage_regions"),
            priority_country_regions=_string_tuple(values, "priority_country_regions"),
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

    def covers_country(self, country: str) -> bool:
        """Return whether this source is a candidate for an ISO country code."""

        normalized_country = country.upper()
        countries = {item.upper() for item in self.countries}
        if normalized_country in countries or ALL_FEI_MEMBER_NATIONS in self.countries:
            return True

        country_regions = COUNTRY_REGION_HINTS.get(normalized_country, ())
        if any(region in self.regions for region in country_regions):
            return True

        regional_country_tokens = {
            f"all_fei_{region}_member_nations" for region in country_regions
        }
        return bool(regional_country_tokens.intersection(self.countries))

    def covers_event_level(self, level: str) -> bool:
        """Return whether this source covers a normalized event level."""

        normalized_level = _normalize_key(level)
        return normalized_level in {_normalize_key(item) for item in self.event_levels}

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
    """Versioned event-source registry with coverage goals and source metadata."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    priority_regions: tuple[str, ...]
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        sources_value = values.get("sources")
        if not isinstance(sources_value, list):
            raise ValueError("sources must be a list of source mappings")

        sources = tuple(EventSource.from_mapping(item) for item in sources_value)
        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=_sort_sources(sources),
        )

    def source_by_id(self, source_id: str) -> EventSource:
        for source in self.sources:
            if source.id == source_id:
                return source
        raise KeyError(f"Unknown event source: {source_id}")

    def sources_for_event_level(
        self,
        level: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        return [
            source
            for source in self.sources
            if _source_has_status(source, include_planned)
            and source.covers_event_level(level)
        ]

    def sources_for_country(
        self,
        country: str,
        *,
        level: str | None = None,
        include_planned: bool = True,
    ) -> list[EventSource]:
        return [
            source
            for source in self.sources
            if _source_has_status(source, include_planned)
            and source.covers_country(country)
            and (level is None or source.covers_event_level(level))
        ]

    def sources_for_region(
        self,
        region: str,
        *,
        level: str | None = None,
        include_planned: bool = True,
    ) -> list[EventSource]:
        normalized_region = _normalize_key(region)
        return [
            source
            for source in self.sources
            if _source_has_status(source, include_planned)
            and ("global" in source.regions or normalized_region in source.regions)
            and (level is None or source.covers_event_level(level))
        ]


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the versioned source registry."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, dict):
        raise ValueError("event source registry must be a JSON object")
    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def source_by_id(source_id: str, *, path: Path | str = DATA_FILE) -> EventSource:
    """Return a configured source by ID."""

    return load_event_source_registry(path).source_by_id(source_id)


def source_priority(source_id: str, *, path: Path | str = DATA_FILE) -> int:
    """Return the deduplication priority configured for a source."""

    return source_by_id(source_id, path=path).priority


def sources_for_event_level(
    level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level."""

    return load_event_source_registry(path).sources_for_event_level(
        level,
        include_planned=include_planned,
    )


def sources_for_country(
    country: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an ISO country code, optionally at one level."""

    return load_event_source_registry(path).sources_for_country(
        country,
        level=level,
        include_planned=include_planned,
    )


def sources_for_region(
    region: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    return load_event_source_registry(path).sources_for_region(
        region,
        level=level,
        include_planned=include_planned,
    )


def _sort_sources(sources: Iterable[EventSource]) -> tuple[EventSource, ...]:
    return tuple(
        sorted(
            sources,
            key=lambda source: (source.priority, source.id != "data_fei", source.id),
        )
    )


def _source_has_status(source: EventSource, include_planned: bool) -> bool:
    statuses = {"active", "planned"} if include_planned else {"active"}
    return source.status in statuses


def _normalize_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("*-intro", "_intro")
    normalized = normalized.replace("*-s", "_short")
    normalized = normalized.replace("*-l", "_long")
    normalized = normalized.replace("-intro", "_intro")
    normalized = normalized.replace("-s", "_short")
    normalized = normalized.replace("-l", "_long")
    normalized = normalized.replace("*", "")
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


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


def _required_mapping(values: dict[str, object], key: str) -> dict[str, object]:
    value = values.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _required_int(values: dict[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (dict, str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
