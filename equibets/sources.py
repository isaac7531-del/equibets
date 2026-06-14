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
    """Declared country and level coverage goals for the source registry."""

    countries: tuple[str, ...]
    national_event_levels: tuple[str, ...]
    international_event_levels: tuple[str, ...]

    @property
    def all_event_levels(self) -> tuple[str, ...]:
        """Return every configured eventing level in registry order."""

        return self.national_event_levels + self.international_event_levels

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        country_targets = values.get("countries")
        if not isinstance(country_targets, list):
            raise ValueError("coverage_targets.countries must be a list")

        country_ids: list[str] = []
        for item in country_targets:
            if isinstance(item, str):
                country_ids.append(item)
            elif isinstance(item, dict):
                country_ids.append(_required_str(item, "id"))
            else:
                raise ValueError(
                    "coverage_targets.countries must contain strings or mappings"
                )

        event_levels = values.get("event_levels")
        if not isinstance(event_levels, dict):
            raise ValueError("coverage_targets.event_levels must be a mapping")

        return cls(
            countries=tuple(country_ids),
            national_event_levels=_string_tuple(event_levels, "national"),
            international_event_levels=_string_tuple(event_levels, "international"),
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
    """Loaded source registry metadata and configured sources."""

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

        source_mappings: list[dict[str, object]] = []
        for item in sources_value:
            if not isinstance(item, dict):
                raise ValueError("sources must contain only source mappings")
            source_mappings.append(item)

        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in source_mappings),
                key=lambda source: (
                    source.priority,
                    source.id != "data_fei",
                    source.id,
                ),
            )
        )

        coverage_targets = values.get("coverage_targets")
        if not isinstance(coverage_targets, dict):
            raise ValueError("coverage_targets must be a mapping")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(coverage_targets),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=sources,
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full source registry metadata and sorted source list."""

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

    normalized_region = _normalized_token(region)
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
    """Return sources that directly cover an ISO country code or all nations."""

    normalized_country = country.strip().upper()
    if not normalized_country:
        raise ValueError("country must be a non-empty string")

    statuses = {"active", "planned"} if include_planned else {"active"}

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
    """Return sources that cover a normalized eventing level."""

    normalized_level = _normalized_token(event_level)
    if not normalized_level:
        raise ValueError("event_level must be a non-empty string")

    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_level in {_normalized_token(level) for level in source.event_levels}
    ]


def _source_covers_country(source: EventSource, normalized_country: str) -> bool:
    if "all_fei_member_nations" in source.countries:
        return True
    return normalized_country in {
        country.upper()
        for country in source.countries
        if not country.startswith("all_fei_")
    }


def _normalized_token(value: str) -> str:
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
