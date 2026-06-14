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
ALL_NATIONAL_AND_REGIONAL_LEVELS = "all_national_and_regional_levels"
ALL_FEI_INTERNATIONAL_LEVELS = "all_fei_international_levels"

_PLACEHOLDER_COUNTRIES: dict[str, frozenset[str]] = {
    "all_fei_europe_member_nations": frozenset(
        {
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
            "ITA",
            "LAT",
            "LTU",
            "LUX",
            "MDA",
            "MKD",
            "MLT",
            "NED",
            "NOR",
            "POL",
            "POR",
            "ROU",
            "SLO",
            "SRB",
            "SVK",
            "SUI",
            "SWE",
            "TUR",
            "UKR",
        }
    ),
    "all_fei_south_america_member_nations": frozenset(
        {"ARG", "BOL", "BRA", "CHI", "COL", "ECU", "PAR", "PER", "URU", "VEN"}
    ),
    "all_fei_asia_member_nations": frozenset(
        {
            "CHN",
            "HKG",
            "IND",
            "INA",
            "JPN",
            "KAZ",
            "KGZ",
            "KOR",
            "MAS",
            "MGL",
            "PAK",
            "PHI",
            "SGP",
            "SRI",
            "THA",
            "TPE",
            "UZB",
            "VIE",
        }
    ),
    "all_fei_africa_member_nations": frozenset(
        {
            "ALG",
            "BOT",
            "EGY",
            "KEN",
            "MAR",
            "MRI",
            "NAM",
            "RSA",
            "TUN",
            "UGA",
            "ZAM",
            "ZIM",
        }
    ),
    "all_fei_middle_east_member_nations": frozenset(
        {
            "BRN",
            "IRQ",
            "IRI",
            "ISR",
            "JOR",
            "KSA",
            "KUW",
            "LBN",
            "OMA",
            "PLE",
            "QAT",
            "SYR",
            "UAE",
            "YEM",
        }
    ),
    "all_fei_central_america_caribbean_member_nations": frozenset(
        {
            "BAR",
            "CRC",
            "CUB",
            "DOM",
            "ESA",
            "GUA",
            "HAI",
            "HON",
            "JAM",
            "NCA",
            "PAN",
            "PUR",
            "TTO",
        }
    ),
    "all_fei_oceania_member_nations": frozenset({"FIJ", "PNG"}),
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


@dataclass(frozen=True)
class CoverageTargets:
    """Configured country and level groups that broad sources promise to cover."""

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
        """Return every configured event level in priority order."""

        return self.domestic_event_levels + self.fei_event_levels


@dataclass(frozen=True)
class EventSourceRegistry:
    """The versioned source registry and its coverage targets."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    priority_regions: tuple[str, ...]
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        targets = values.get("coverage_targets")
        if not isinstance(targets, dict):
            raise ValueError("coverage_targets must be an object")

        raw_sources = values.get("sources")
        if not isinstance(raw_sources, Iterable) or isinstance(raw_sources, (str, bytes)):
            raise ValueError("sources must be a list of objects")
        source_items = tuple(raw_sources)
        if not all(isinstance(item, dict) for item in source_items):
            raise ValueError("sources must contain only objects")

        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in source_items),
                key=lambda source: (source.priority, source.id != "data_fei", source.id),
            )
        )

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(targets),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=sources,
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the full source registry, including global coverage targets."""

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
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
    ]


def sources_for_country(
    country_code: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an ISO country code, including global backfills."""

    normalized_country = country_code.strip().upper()
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
    """Return sources that can provide a specific eventing level."""

    registry = load_event_source_registry(path)
    normalized_level = _normalize_token(event_level)
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in registry.sources
        if source.status in statuses
        and _source_covers_event_level(source, normalized_level, registry.coverage_targets)
    ]


def sources_by_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Backward-compatible alias for callers that prefer the noun phrase."""

    return sources_for_event_level(
        event_level,
        path=path,
        include_planned=include_planned,
    )


def _source_covers_country(source: EventSource, country_code: str) -> bool:
    for country in source.countries:
        if country == ALL_FEI_MEMBER_NATIONS:
            return True
        if country.upper() == country_code:
            return True
        if country_code in _PLACEHOLDER_COUNTRIES.get(country, frozenset()):
            return True
    return False


def _source_covers_event_level(
    source: EventSource,
    event_level: str,
    coverage_targets: CoverageTargets,
) -> bool:
    domestic_levels = {_normalize_token(level) for level in coverage_targets.domestic_event_levels}
    fei_levels = {_normalize_token(level) for level in coverage_targets.fei_event_levels}

    for configured_level in source.event_levels:
        normalized_configured_level = _normalize_token(configured_level)
        if normalized_configured_level == event_level:
            return True
        if (
            configured_level == ALL_NATIONAL_AND_REGIONAL_LEVELS
            and event_level in domestic_levels
        ):
            return True
        if configured_level == ALL_FEI_INTERNATIONAL_LEVELS and event_level in fei_levels:
            return True
    return False


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


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
