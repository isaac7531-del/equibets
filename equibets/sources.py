"""Event-result source registry helpers.

The project prioritizes FEI data while tracking national-event source coverage
for every FEI member nation and domestic eventing level.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"
GLOBAL_COUNTRY_TOKEN = "all_fei_member_nations"

_COUNTRY_COVERAGE_TOKENS = {
    "ARG": ("all_fei_south_america_member_nations",),
    "AUS": ("all_fei_oceania_member_nations",),
    "BRA": ("all_fei_south_america_member_nations",),
    "CAN": ("all_fei_north_america_member_nations",),
    "CHL": ("all_fei_south_america_member_nations",),
    "CHN": ("all_fei_asia_member_nations",),
    "CRC": ("all_fei_central_america_caribbean_member_nations",),
    "FRA": ("all_fei_europe_member_nations",),
    "GBR": ("all_fei_europe_member_nations",),
    "GER": ("all_fei_europe_member_nations",),
    "IRL": ("all_fei_europe_member_nations",),
    "JPN": ("all_fei_asia_member_nations",),
    "KOR": ("all_fei_asia_member_nations",),
    "MEX": ("all_fei_north_america_member_nations",),
    "NZL": ("all_fei_oceania_member_nations",),
    "QAT": ("all_fei_middle_east_member_nations",),
    "RSA": ("all_fei_africa_member_nations",),
    "UAE": ("all_fei_middle_east_member_nations",),
    "USA": ("all_fei_north_america_member_nations",),
    "ZAF": ("all_fei_africa_member_nations",),
}


@dataclass(frozen=True)
class CoverageTargets:
    """The registry's declared all-country and all-level coverage target."""

    countries: str
    domestic_event_levels: tuple[str, ...]
    fei_event_levels: tuple[str, ...]

    @property
    def all_event_levels(self) -> tuple[str, ...]:
        return self.domestic_event_levels + self.fei_event_levels

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_required_str(values, "countries"),
            domestic_event_levels=_string_tuple(values, "domestic_event_levels"),
            fei_event_levels=_string_tuple(values, "fei_event_levels"),
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
    """The full source registry document."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        raw_sources = values.get("sources")
        if not isinstance(raw_sources, Iterable) or isinstance(raw_sources, (str, bytes)):
            raise ValueError("sources must be a list of source mappings")

        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in raw_sources),
                key=lambda source: (source.priority, source.id != "data_fei", source.id),
            )
        )
        source_ids = [source.id for source in sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source ids must be unique")

        primary_source_id = _required_str(values, "primary_source_id")
        if primary_source_id not in source_ids:
            raise ValueError("primary_source_id must match a configured source")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=primary_source_id,
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            sources=sources,
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full event-source registry document."""

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

    normalized_region = _normalize_token(region)
    statuses = _statuses(include_planned)

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
    """Return sources covering a country while preserving global priorities."""

    country_code = country.strip().upper()
    country_tokens = {
        country_code,
        GLOBAL_COUNTRY_TOKEN,
        *_COUNTRY_COVERAGE_TOKENS.get(country_code, ()),
    }
    statuses = _statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and country_tokens.intersection(source.countries)
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a normalized event level."""

    normalized_level = _normalize_token(event_level)
    statuses = _statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and normalized_level in source.event_levels
    ]


def _statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_token(value: str) -> str:
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
