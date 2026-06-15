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
ACTIVE_STATUSES = {"active"}
PLANNED_STATUSES = {"active", "planned"}

COUNTRY_REGION_ALIASES = {
    "ARG": ("south_america",),
    "AUS": ("australia", "oceania"),
    "AUT": ("europe",),
    "BEL": ("europe",),
    "BRA": ("south_america",),
    "CAN": ("north_america",),
    "CHE": ("europe",),
    "CHL": ("south_america",),
    "CHN": ("asia",),
    "COL": ("south_america",),
    "CZE": ("europe",),
    "DEU": ("europe",),
    "DNK": ("europe",),
    "ESP": ("europe",),
    "FIN": ("europe",),
    "FRA": ("europe",),
    "GBR": ("uk", "europe"),
    "HKG": ("asia",),
    "HUN": ("europe",),
    "IND": ("asia",),
    "IRL": ("europe",),
    "ITA": ("europe",),
    "JPN": ("asia",),
    "KOR": ("asia",),
    "MEX": ("north_america",),
    "NLD": ("europe",),
    "NOR": ("europe",),
    "NZL": ("new_zealand", "oceania"),
    "POL": ("europe",),
    "PRT": ("europe",),
    "SWE": ("europe",),
    "THA": ("asia",),
    "URY": ("south_america",),
    "USA": ("usa", "north_america"),
    "ZAF": ("africa",),
}


@dataclass(frozen=True)
class CoverageTargets:
    """Declared country and level coverage goals for public event data."""

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
        """Return every declared level, domestic first and then FEI."""

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
    """A loaded event source registry, including coverage metadata."""

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
        source_mappings = tuple(raw_sources)
        if not all(isinstance(item, dict) for item in source_mappings):
            raise ValueError("sources must contain only source mappings")

        raw_coverage_targets = values.get("coverage_targets")
        if not isinstance(raw_coverage_targets, dict):
            raise ValueError("coverage_targets must be an object")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(raw_coverage_targets),
            sources=tuple(_sort_sources(EventSource.from_mapping(item) for item in source_mappings)),
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the source registry, including coverage goals and sorted sources."""

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
    """Return sources covering an FEI country code while preserving priorities."""

    country_code = country.upper().replace(" ", "_")
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and _source_covers_country(source, country_code)
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level while preserving priorities."""

    normalized_level = _normalize_event_level(event_level)
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_level in {_normalize_event_level(level) for level in source.event_levels}
    ]


def _sort_sources(sources: Iterable[EventSource]) -> list[EventSource]:
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def _allowed_statuses(include_planned: bool) -> set[str]:
    return PLANNED_STATUSES if include_planned else ACTIVE_STATUSES


def _source_covers_country(source: EventSource, country_code: str) -> bool:
    countries = {country.upper() for country in source.countries}
    if country_code in countries or "ALL_FEI_MEMBER_NATIONS" in countries:
        return True

    return any(
        f"ALL_FEI_{region.upper()}_MEMBER_NATIONS" in countries
        for region in COUNTRY_REGION_ALIASES.get(country_code, ())
    )


def _normalize_event_level(event_level: str) -> str:
    value = event_level.strip().lower()
    compact = re.sub(r"[\s_*]+", "", value)

    cci_length = re.fullmatch(r"cci([1-5])-?([sl])", compact)
    if cci_length:
        length = "short" if cci_length.group(2) == "s" else "long"
        return f"cci{cci_length.group(1)}_{length}"

    cci_intro = re.fullmatch(r"cci([1-5])?-?(intro|introductory)", compact)
    if cci_intro:
        star = cci_intro.group(1)
        return f"cci{star}_introductory" if star else "cci_introductory"

    national_star = re.fullmatch(r"(national|ccn)([1-5])", compact)
    if national_star:
        star_names = {
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
        }
        return f"national_{star_names[national_star.group(2)]}_star"

    return _normalize_token(value)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


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
