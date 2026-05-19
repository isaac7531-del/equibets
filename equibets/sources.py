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
ALL_COUNTRIES = "all_countries"
ALL_EVENTING_LEVELS = "all_eventing_levels"
GLOBAL_REGION = "global"

COUNTRY_REGION_OVERRIDES = {
    "AUS": ("australia",),
    "GBR": ("uk",),
    "NZL": ("new_zealand",),
    "USA": ("usa",),
}

EUROPE_COUNTRIES = {
    "ALB",
    "AND",
    "ARM",
    "AUT",
    "AZE",
    "BEL",
    "BIH",
    "BUL",
    "CRO",
    "CYP",
    "CZE",
    "DEN",
    "ESP",
    "EST",
    "FIN",
    "FRA",
    "GBR",
    "GEO",
    "GER",
    "GRE",
    "HUN",
    "IRL",
    "ISL",
    "ISR",
    "ITA",
    "LAT",
    "LIE",
    "LTU",
    "LUX",
    "MDA",
    "MKD",
    "MLT",
    "MON",
    "NED",
    "NOR",
    "POL",
    "POR",
    "ROU",
    "SMR",
    "SRB",
    "SUI",
    "SVK",
    "SLO",
    "SWE",
    "TUR",
    "UKR",
}


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


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    sources = [EventSource.from_mapping(item) for item in payload["sources"]]
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a region and optional level."""

    normalized_region = _normalize_key(region)
    statuses = _included_statuses(include_planned)
    normalized_level = _normalize_level(level)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and _source_matches_region(source, normalized_region)
        and _source_matches_level(source, normalized_level)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a country and optional eventing level."""

    normalized_country = country.strip().upper()
    if not normalized_country:
        raise ValueError("country must be a non-empty string")

    regions = _regions_for_country(normalized_country)
    statuses = _included_statuses(include_planned)
    normalized_level = _normalize_level(level)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and _source_matches_country(source, normalized_country, regions)
        and _source_matches_level(source, normalized_level)
    ]


def _included_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_key(value: str) -> str:
    normalized = value.strip().lower().replace(" ", "_")
    if not normalized:
        raise ValueError("value must be a non-empty string")
    return normalized


def _normalize_level(level: str | None) -> str | None:
    if level is None:
        return None
    normalized = _normalize_key(level).replace("-", "_")
    return normalized


def _regions_for_country(country: str) -> set[str]:
    regions = {GLOBAL_REGION}
    regions.update(COUNTRY_REGION_OVERRIDES.get(country, ()))

    if country in EUROPE_COUNTRIES:
        regions.add("europe")

    return regions


def _source_matches_region(source: EventSource, region: str) -> bool:
    return GLOBAL_REGION in source.regions or region in source.regions


def _source_matches_country(source: EventSource, country: str, regions: set[str]) -> bool:
    country_matches = ALL_COUNTRIES in source.countries or country in source.countries
    region_matches = GLOBAL_REGION in source.regions or any(region in source.regions for region in regions)
    return country_matches and region_matches


def _source_matches_level(source: EventSource, level: str | None) -> bool:
    if level is None:
        return True
    return ALL_EVENTING_LEVELS in source.event_levels or level in source.event_levels


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
