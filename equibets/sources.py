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
GLOBAL_COUNTRY_TOKENS = frozenset({"ALL_FEI_MEMBER_NATIONS"})
EUROPE_COUNTRY_TOKENS = frozenset({"ALL_FEI_EUROPE_MEMBER_NATIONS"})
ALL_EVENT_LEVEL_TOKENS = frozenset({"all_eventing_levels"})
ALL_NATIONAL_EVENT_LEVEL_TOKENS = frozenset({"all_national_event_levels"})
NATIONAL_EVENT_LEVELS = frozenset({"national", "regional", "local", "grassroots"})

# FEI's European Group I/II nations plus European microstates represented by
# national federations. These codes are used only to resolve the registry's
# European aggregate token; global FEI-member tokens still cover every country.
EUROPE_FEI_MEMBER_COUNTRIES = frozenset(
    {
        "ALB",
        "AND",
        "ARM",
        "AUT",
        "AZE",
        "BEL",
        "BIH",
        "BLR",
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
        "KOS",
        "LAT",
        "LIE",
        "LTU",
        "LUX",
        "MDA",
        "MKD",
        "MLT",
        "MNE",
        "MON",
        "NED",
        "NOR",
        "POL",
        "POR",
        "ROU",
        "RUS",
        "SMR",
        "SRB",
        "SLO",
        "SUI",
        "SVK",
        "SWE",
        "TUR",
        "UKR",
    }
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
    event_levels: Iterable[str] | None = None,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = region.lower().replace(" ", "_")
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
        and source_covers_event_levels(source, event_levels)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    event_levels: Iterable[str] | None = None,
) -> list[EventSource]:
    """Return sources covering a country and optional event tiers.

    Country coverage supports explicit FEI/NOC country codes such as ``GBR``
    and registry aggregate tokens such as ``all_fei_member_nations``.
    """

    statuses = {"active", "planned"} if include_planned else {"active"}
    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and source_covers_country(source, country)
        and source_covers_event_levels(source, event_levels)
    ]


def source_covers_country(source: EventSource, country: str) -> bool:
    """Return whether a source covers a FEI/NOC country code."""

    normalized_country = _normalize_country(country)
    if not normalized_country:
        raise ValueError("country must be a non-empty string")

    countries = frozenset(_normalize_country(item) for item in source.countries)
    if GLOBAL_COUNTRY_TOKENS & countries:
        return True
    if EUROPE_COUNTRY_TOKENS & countries and normalized_country in EUROPE_FEI_MEMBER_COUNTRIES:
        return True
    return normalized_country in countries


def source_covers_event_levels(
    source: EventSource,
    event_levels: Iterable[str] | None,
) -> bool:
    """Return whether a source covers at least one requested event tier."""

    requested_levels = _normalize_event_levels(event_levels)
    if not requested_levels:
        return True

    source_levels = _expand_event_levels(source.event_levels)
    if ALL_EVENT_LEVEL_TOKENS & source_levels:
        return True
    return bool(source_levels & requested_levels)


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


def _normalize_country(value: str) -> str:
    return value.strip().upper().replace("-", "_").replace(" ", "_")


def _normalize_event_levels(values: Iterable[str] | None) -> frozenset[str]:
    if values is None:
        return frozenset()
    if isinstance(values, (str, bytes)):
        values = (str(values),)
    return _expand_event_levels(values)


def _expand_event_levels(values: Iterable[str]) -> frozenset[str]:
    levels = {_normalize_level(value) for value in values}
    if ALL_EVENT_LEVEL_TOKENS & levels:
        return levels | NATIONAL_EVENT_LEVELS | {"fei_international"}
    if ALL_NATIONAL_EVENT_LEVEL_TOKENS & levels:
        return levels | NATIONAL_EVENT_LEVELS
    return frozenset(levels)


def _normalize_level(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")
