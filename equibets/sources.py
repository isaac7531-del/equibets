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
ALL_COUNTRIES_TOKEN = "all_fei_member_nations"

DOMESTIC_EVENT_LEVELS = (
    "starter",
    "introductory",
    "beginner_novice",
    "novice",
    "training",
    "modified",
    "preliminary",
    "intermediate",
    "advanced",
    "regional",
    "national",
    "national_one_star",
    "national_two_star",
    "national_three_star",
    "national_four_star",
    "national_five_star",
)

FEI_EVENT_LEVELS = (
    "fei_international",
    "cci_intro",
    "cci1_intro",
    "cci1_short",
    "cci1_long",
    "cci2_short",
    "cci2_long",
    "cci3_short",
    "cci3_long",
    "cci4_short",
    "cci4_long",
    "cci5_long",
    "championship",
)

REGION_COUNTRY_TOKENS = {
    "all_fei_africa_member_nations": "africa",
    "all_fei_asia_member_nations": "asia",
    "all_fei_europe_member_nations": "europe",
    "all_fei_middle_east_member_nations": "middle_east",
    "all_fei_north_america_member_nations": "north_america",
    "all_fei_central_america_caribbean_member_nations": (
        "central_america_caribbean"
    ),
    "all_fei_south_america_member_nations": "south_america",
    "all_fei_oceania_member_nations": "oceania",
}

REGION_COUNTRIES = {
    "africa": (
        "ALG",
        "ANG",
        "BEN",
        "BOT",
        "BUR",
        "CMR",
        "CGO",
        "CIV",
        "COD",
        "EGY",
        "ETH",
        "GAB",
        "GHA",
        "KEN",
        "LBA",
        "MAD",
        "MAR",
        "MRI",
        "MOZ",
        "NAM",
        "NGR",
        "RSA",
        "SEN",
        "SUD",
        "SWZ",
        "TAN",
        "TUN",
        "UGA",
        "ZAM",
        "ZIM",
    ),
    "asia": (
        "BAN",
        "BRU",
        "CAM",
        "CHN",
        "HKG",
        "INA",
        "IND",
        "JPN",
        "KAZ",
        "KGZ",
        "KOR",
        "MAS",
        "MGL",
        "MYA",
        "NEP",
        "PAK",
        "PHI",
        "SIN",
        "SRI",
        "THA",
        "TPE",
        "UZB",
        "VIE",
    ),
    "europe": (
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
        "RUS",
        "SMR",
        "SRB",
        "SLO",
        "SVK",
        "SUI",
        "SWE",
        "TUR",
        "UKR",
    ),
    "middle_east": (
        "BRN",
        "IRQ",
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
    ),
    "north_america": (
        "CAN",
        "MEX",
        "USA",
    ),
    "central_america_caribbean": (
        "ARU",
        "BAH",
        "BAR",
        "BER",
        "CAY",
        "CRC",
        "CUB",
        "DOM",
        "ESA",
        "GUA",
        "HAI",
        "HON",
        "ISV",
        "JAM",
        "NCA",
        "PAN",
        "PUR",
        "TTO",
    ),
    "south_america": (
        "ARG",
        "BOL",
        "BRA",
        "CHI",
        "COL",
        "ECU",
        "PAR",
        "PER",
        "URU",
        "VEN",
    ),
    "oceania": (
        "ASA",
        "AUS",
        "COK",
        "FIJ",
        "FSM",
        "GUM",
        "NCL",
        "NZL",
        "PNG",
        "SAM",
        "SOL",
        "TAH",
        "TGA",
        "VAN",
    ),
}

COUNTRY_REGIONS = {
    country: region
    for region, countries in REGION_COUNTRIES.items()
    for country in countries
}

LEVEL_ALIASES = {
    "advanced": "advanced",
    "beginner_novice": "beginner_novice",
    "bn": "beginner_novice",
    "cci": "fei_international",
    "cci_intro": "cci_intro",
    "cci1_intro": "cci1_intro",
    "cci1intro": "cci1_intro",
    "championship": "championship",
    "championships": "championship",
    "fei": "fei_international",
    "fei_international": "fei_international",
    "international": "fei_international",
    "intro": "introductory",
    "introductory": "introductory",
    "modified": "modified",
    "national": "national",
    "national_1": "national_one_star",
    "national_1_star": "national_one_star",
    "national_2": "national_two_star",
    "national_2_star": "national_two_star",
    "national_3": "national_three_star",
    "national_3_star": "national_three_star",
    "national_4": "national_four_star",
    "national_4_star": "national_four_star",
    "national_5": "national_five_star",
    "national_5_star": "national_five_star",
    "national_five_star": "national_five_star",
    "national_four_star": "national_four_star",
    "national_one_star": "national_one_star",
    "national_three_star": "national_three_star",
    "national_two_star": "national_two_star",
    "novice": "novice",
    "prelim": "preliminary",
    "preliminary": "preliminary",
    "regional": "regional",
    "starter": "starter",
    "training": "training",
}

for grade in range(1, 5):
    LEVEL_ALIASES[f"cci{grade}_s"] = f"cci{grade}_short"
    LEVEL_ALIASES[f"cci{grade}_short"] = f"cci{grade}_short"
    LEVEL_ALIASES[f"cci{grade}_l"] = f"cci{grade}_long"
    LEVEL_ALIASES[f"cci{grade}_long"] = f"cci{grade}_long"

LEVEL_ALIASES["cci5_l"] = "cci5_long"
LEVEL_ALIASES["cci5_long"] = "cci5_long"


@dataclass(frozen=True)
class CoverageTargets:
    """Coverage targets declared by the event-results registry."""

    countries: tuple[str, ...]
    disciplines: tuple[str, ...]
    domestic_event_levels: tuple[str, ...]
    fei_event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            disciplines=_string_tuple(values, "disciplines"),
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
    """The complete event-results source registry."""

    version: int
    primary_source_id: str
    coverage_goal: str
    coverage_targets: CoverageTargets
    priority_regions: tuple[str, ...]
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        targets = values.get("coverage_targets")
        sources = values.get("sources")
        if not isinstance(targets, dict):
            raise ValueError("coverage_targets must be a mapping")
        if not isinstance(sources, list):
            raise ValueError("sources must be a list")

        ordered_sources = sorted(
            (EventSource.from_mapping(item) for item in sources),
            key=lambda source: (
                source.priority,
                source.id != _required_str(values, "primary_source_id"),
                source.id,
            ),
        )
        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(targets),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=tuple(ordered_sources),
        )


def load_event_source_registry(
    path: Path | str = DATA_FILE,
) -> EventSourceRegistry:
    """Load the complete event-results source registry."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, dict):
        raise ValueError("event source registry must be a mapping")
    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country code while preserving priorities."""

    country_code = country.strip().upper()
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

    normalized_level = normalize_event_level(event_level)
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and normalized_level in source.event_levels
    ]


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


def normalize_event_level(event_level: str) -> str:
    """Normalize common event-level labels to registry tokens."""

    normalized = event_level.strip().lower()
    normalized = normalized.replace("*", "")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    normalized = re.sub(r"_+", "_", normalized).strip("_")

    if normalized in LEVEL_ALIASES:
        return LEVEL_ALIASES[normalized]

    short_long_match = re.fullmatch(r"cci([1-5])_(s|short|l|long)", normalized)
    if short_long_match:
        grade, length = short_long_match.groups()
        return f"cci{grade}_{'short' if length in {'s', 'short'} else 'long'}"

    return normalized


def _allowed_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _source_covers_country(source: EventSource, country_code: str) -> bool:
    if ALL_COUNTRIES_TOKEN in source.countries:
        return True
    if country_code in source.countries:
        return True

    country_region = COUNTRY_REGIONS.get(country_code)
    if country_region is None:
        return False

    return any(
        REGION_COUNTRY_TOKENS.get(country_token) == country_region
        for country_token in source.countries
    )


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
