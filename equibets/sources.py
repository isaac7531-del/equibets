"""Event-result source registry helpers.

The project prioritizes FEI data while tracking national-event sources for
broader all-country and all-level eventing coverage.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"
ACTIVE_STATUSES = frozenset({"active"})
PLANNED_STATUSES = frozenset({"active", "planned"})
COUNTRY_REGIONS = {
    "ARE": ("middle_east", "asia"),
    "ARG": ("south_america",),
    "AUS": ("australia", "oceania"),
    "AUT": ("europe",),
    "BEL": ("europe",),
    "BHR": ("middle_east", "asia"),
    "BRA": ("south_america",),
    "CAN": ("north_america",),
    "CHE": ("europe",),
    "CHL": ("south_america",),
    "CHN": ("asia",),
    "COL": ("south_america",),
    "DEU": ("europe",),
    "DNK": ("europe",),
    "ECU": ("south_america",),
    "ESP": ("europe",),
    "FIN": ("europe",),
    "FRA": ("europe",),
    "GBR": ("uk", "europe"),
    "HKG": ("asia",),
    "IND": ("asia",),
    "IRL": ("europe",),
    "ITA": ("europe",),
    "JPN": ("asia",),
    "KOR": ("asia",),
    "MEX": ("central_america_caribbean",),
    "NLD": ("europe",),
    "NOR": ("europe",),
    "NZL": ("new_zealand", "oceania"),
    "POL": ("europe",),
    "PRT": ("europe",),
    "QAT": ("middle_east", "asia"),
    "SAU": ("middle_east", "asia"),
    "SWE": ("europe",),
    "THA": ("asia",),
    "URY": ("south_america",),
    "USA": ("usa", "north_america"),
    "ZAF": ("africa",),
}
COUNTRY_ALIASES = {
    "GB": "GBR",
    "UK": "GBR",
    "GREAT_BRITAIN": "GBR",
    "BRITAIN": "GBR",
    "UNITED_KINGDOM": "GBR",
    "UNITED_STATES": "USA",
    "UNITED_STATES_OF_AMERICA": "USA",
    "US": "USA",
    "UAE": "ARE",
    "RSA": "ZAF",
    "SOUTH_AFRICA": "ZAF",
    "NEW_ZEALAND": "NZL",
}


@dataclass(frozen=True)
class CoverageTargets:
    """The countries and event levels the registry is expected to cover."""

    countries: tuple[str, ...]
    national_and_regional_levels: tuple[str, ...]
    fei_levels: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
            national_and_regional_levels=_string_tuple(
                values,
                "all_national_and_regional_levels",
            ),
            fei_levels=_string_tuple(values, "all_fei_eventing_levels"),
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
    """Loaded event-source registry and coverage metadata."""

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
            raise ValueError("sources must be a list")

        coverage_targets_value = values.get("coverage_targets")
        if not isinstance(coverage_targets_value, dict):
            raise ValueError("coverage_targets must be an object")

        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in sources_value),
                key=lambda source: (
                    source.priority,
                    source.id != values.get("primary_source_id"),
                    source.id,
                ),
            )
        )

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=CoverageTargets.from_mapping(coverage_targets_value),
            priority_regions=_string_tuple(values, "priority_regions"),
            sources=sources,
        )

    def sources_for_region(
        self,
        region: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = _normalize_lookup(region)
        statuses = _allowed_statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses
            and ("global" in source.regions or normalized_region in source.regions)
        ]

    def sources_for_country(
        self,
        country: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources that cover a country directly, regionally, or globally."""

        normalized_country = _normalize_country(country)
        country_regions = COUNTRY_REGIONS.get(normalized_country, ())
        regional_country_tokens = {
            f"all_fei_{region}_member_nations" for region in country_regions
        }
        statuses = _allowed_statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses
            and (
                normalized_country in source.countries
                or "all_fei_member_nations" in source.countries
                or any(token in source.countries for token in regional_country_tokens)
            )
        ]

    def sources_for_event_level(
        self,
        event_level: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources that cover a canonical or FEI-formatted event level."""

        normalized_level = _normalize_event_level(event_level)
        statuses = _allowed_statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses and normalized_level in source.event_levels
        ]


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the event-source registry and coverage targets."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    return EventSourceRegistry.from_mapping(payload)


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with the configured primary source first."""

    return list(load_event_source_registry(path).sources)


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    return load_event_source_registry(path).sources_for_region(
        region,
        include_planned=include_planned,
    )


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country while preserving global priorities."""

    return load_event_source_registry(path).sources_for_country(
        country,
        include_planned=include_planned,
    )


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level while preserving global priorities."""

    return load_event_source_registry(path).sources_for_event_level(
        event_level,
        include_planned=include_planned,
    )


def _allowed_statuses(include_planned: bool) -> frozenset[str]:
    return PLANNED_STATUSES if include_planned else ACTIVE_STATUSES


def _normalize_lookup(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_country(country: str) -> str:
    value = country.strip().upper().replace(" ", "_").replace("-", "_")
    return COUNTRY_ALIASES.get(value, value)


def _normalize_event_level(event_level: str) -> str:
    value = _normalize_lookup(event_level).replace("*", "")
    aliases = {
        "beginnernovice": "beginner_novice",
        "intro": "introductory",
        "cci_intro": "cci_intro",
        "cci_i": "cci_intro",
        "ccii": "cci_intro",
        "cci1intro": "cci1_intro",
        "cci1_intro": "cci1_intro",
        "cci1_i": "cci1_intro",
        "cci1i": "cci1_intro",
        "cci1introductory": "cci1_intro",
        "cci1_introductory": "cci1_intro",
        "cci1_s": "cci1_short",
        "cci1s": "cci1_short",
        "cci1_l": "cci1_long",
        "cci1l": "cci1_long",
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
        "cci1_short": "cci1_short",
        "cci1_long": "cci1_long",
        "cci2_short": "cci2_short",
        "cci2_long": "cci2_long",
        "cci3_short": "cci3_short",
        "cci3_long": "cci3_long",
        "cci4_short": "cci4_short",
        "cci4_long": "cci4_long",
        "cci5_long": "cci5_long",
    }
    if value in aliases:
        return aliases[value]

    cci_match = re.fullmatch(r"cci([1-5])_?([sl])", value)
    if cci_match:
        suffix = "short" if cci_match.group(2) == "s" else "long"
        return f"cci{cci_match.group(1)}_{suffix}"

    national_star_match = re.fullmatch(r"national_?([1-5])_?star", value)
    if national_star_match:
        names = {
            "1": "one",
            "2": "two",
            "3": "three",
            "4": "four",
            "5": "five",
        }
        return f"national_{names[national_star_match.group(1)]}_star"

    return value


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
