"""Event-result source registry helpers.

The project prioritizes FEI data while tracking national-event sources for
broader all-country and all-level eventing coverage.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"
ACTIVE_STATUSES = frozenset({"active"})
PLANNED_STATUSES = frozenset({"active", "planned"})

COUNTRY_ALIASES = {
    "ARE": "UAE",
    "BRITAIN": "GBR",
    "CHE": "SUI",
    "CHL": "CHI",
    "DEU": "GER",
    "DNK": "DEN",
    "GB": "GBR",
    "GREAT_BRITAIN": "GBR",
    "NLD": "NED",
    "PRT": "POR",
    "RSA": "ZAF",
    "SAU": "KSA",
    "SOUTH_AFRICA": "ZAF",
    "U.K.": "GBR",
    "U.S.": "USA",
    "UK": "GBR",
    "UNITED_KINGDOM": "GBR",
    "UNITED_STATES": "USA",
    "UNITED_STATES_OF_AMERICA": "USA",
    "US": "USA",
    "URY": "URU",
    "NEW_ZEALAND": "NZL",
}
EVENT_LEVEL_ALIASES = {
    "advanced": "advanced",
    "beginnovice": "beginner_novice",
    "beginnernovice": "beginner_novice",
    "bn": "beginner_novice",
    "cciinternational": "fei_international",
    "ccintro": "cci_intro",
    "cciintro": "cci_intro",
    "championship": "championship",
    "fei": "fei_international",
    "feiinternational": "fei_international",
    "grassroot": "grassroots",
    "grassroots": "grassroots",
    "intro": "introductory",
    "introductory": "introductory",
    "modified": "modified",
    "national": "national",
    "novice": "novice",
    "prelim": "preliminary",
    "preliminary": "preliminary",
    "regional": "regional",
    "starter": "starter",
    "training": "training",
}
STAR_WORDS = {
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
}


@dataclass(frozen=True)
class CoverageTargets:
    """Reusable country and event-level groups declared by the registry."""

    country_sets: Mapping[str, tuple[str, ...]]
    event_level_sets: Mapping[str, tuple[str, ...]]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "CoverageTargets":
        country_sets = {
            key: tuple(_normalize_country_code(country) for country in items)
            for key, items in _required_string_lists(values, "country_sets").items()
        }
        event_level_sets = {
            key: tuple(_normalize_event_level(level) for level in items)
            for key, items in _required_string_lists(values, "event_level_sets").items()
        }
        if (
            "all_fei_international_levels" in event_level_sets
            and "all_fei_eventing_levels" not in event_level_sets
        ):
            event_level_sets["all_fei_eventing_levels"] = event_level_sets[
                "all_fei_international_levels"
            ]
        return cls(country_sets=country_sets, event_level_sets=event_level_sets)

    @property
    def countries(self) -> tuple[str, ...]:
        return self.country_sets["all_fei_member_nations"]

    @property
    def national_and_regional_levels(self) -> tuple[str, ...]:
        return self.event_level_sets["all_national_and_regional_levels"]

    @property
    def fei_levels(self) -> tuple[str, ...]:
        return self.event_level_sets["all_fei_eventing_levels"]

    def expand_countries(self, values: Iterable[str]) -> tuple[str, ...]:
        """Expand country-set tokens and normalize explicit country codes."""

        countries: list[str] = []
        for value in values:
            countries.extend(
                self.country_sets[value]
                if value in self.country_sets
                else (_normalize_country_code(value),)
            )
        return _unique_tuple(countries)

    def expand_event_levels(self, values: Iterable[str]) -> tuple[str, ...]:
        """Expand level-set tokens and normalize explicit event-level labels."""

        levels: list[str] = []
        for value in values:
            levels.extend(
                self.event_level_sets[value]
                if value in self.event_level_sets
                else (_normalize_event_level(value),)
            )
        return _unique_tuple(levels)


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
    def from_mapping(
        cls,
        values: Mapping[str, object],
        coverage_targets: CoverageTargets | None = None,
    ) -> "EventSource":
        countries = _string_tuple(values, "countries")
        event_levels = _string_tuple(values, "event_levels")
        if coverage_targets is not None:
            countries = coverage_targets.expand_countries(countries)
            event_levels = coverage_targets.expand_event_levels(event_levels)

        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            priority=_required_int(values, "priority"),
            scope=_required_str(values, "scope"),
            regions=tuple(_normalize_region(region) for region in _string_tuple(values, "regions")),
            countries=countries,
            disciplines=tuple(discipline.lower() for discipline in _string_tuple(values, "disciplines")),
            event_levels=event_levels,
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
    def from_mapping(cls, values: Mapping[str, object]) -> "EventSourceRegistry":
        coverage_targets = CoverageTargets.from_mapping(
            _required_mapping(values, "coverage_targets")
        )
        primary_source_id = _required_str(values, "primary_source_id")

        sources = tuple(
            sorted(
                (
                    EventSource.from_mapping(item, coverage_targets)
                    for item in _required_items(values, "sources")
                ),
                key=lambda source: (
                    source.priority,
                    source.id != primary_source_id,
                    source.id,
                ),
            )
        )

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=primary_source_id,
            coverage_goal=_required_str(values, "coverage_goal"),
            coverage_targets=coverage_targets,
            priority_regions=tuple(
                _normalize_region(region)
                for region in _string_tuple(values, "priority_regions")
            ),
            sources=sources,
        )

    def sources_for_region(
        self,
        region: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = _normalize_region(region)
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

        normalized_country = _normalize_country_code(country)
        statuses = _allowed_statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses
            and normalized_country in source.countries
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


def _normalize_country_code(country: str) -> str:
    value = re.sub(r"[^A-Z0-9.]+", "_", country.strip().upper()).strip("_")
    if not value:
        raise ValueError("country must be a non-empty string")
    return COUNTRY_ALIASES.get(value, value)


def _normalize_event_level(event_level: str) -> str:
    normalized = event_level.strip().lower().replace("*", "")
    if not normalized:
        raise ValueError("event level must be a non-empty string")

    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    if compact in EVENT_LEVEL_ALIASES:
        return EVENT_LEVEL_ALIASES[compact]

    national_star = re.fullmatch(r"(?:national|ccn)([1-5])(?:star)?", compact)
    if national_star:
        return f"national_{STAR_WORDS[national_star.group(1)]}_star"

    cci_intro = re.fullmatch(r"cci1?(?:intro|introductory)", compact)
    if cci_intro:
        return "cci1_intro" if "1" in compact else "cci_intro"

    cci_level = re.fullmatch(r"ccio?([1-5])(?:star)?(short|long|s|l)", compact)
    if cci_level:
        suffix = "short" if cci_level.group(2) in {"short", "s"} else "long"
        return f"cci{cci_level.group(1)}_{suffix}"

    if re.fullmatch(r"ccio?[1-5](?:star)?", compact):
        return "fei_international"

    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


def _normalize_region(region: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", region.strip().lower()).strip("_")


def _required_str(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(values: Mapping[str, object], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be null or a non-empty string")
    return value


def _required_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _required_mapping(values: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = values.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")
    return value


def _required_items(values: Mapping[str, object], key: str) -> tuple[Mapping[str, object], ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of objects")

    items = tuple(value)
    if not all(isinstance(item, Mapping) for item in items):
        raise ValueError(f"{key} must contain only objects")
    return items


def _required_string_lists(
    values: Mapping[str, object],
    key: str,
) -> Mapping[str, tuple[str, ...]]:
    value = values.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"{key} must be an object")

    return {set_name: _string_tuple(value, set_name) for set_name in value}


def _string_tuple(values: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _unique_tuple(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
