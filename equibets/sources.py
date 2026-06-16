"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader coverage.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"

COUNTRY_ALIASES = {
    "UK": "GBR",
    "RSA": "ZAF",
}

EVENT_LEVEL_ALIASES = {
    "advanced": "advanced",
    "beginnovice": "beginner_novice",
    "beginnernovice": "beginner_novice",
    "bn": "beginner_novice",
    "cciinternational": "fei_international",
    "ccintro": "cci_intro",
    "cciintro": "cci_intro",
    "fei": "fei_international",
    "feiinternational": "fei_international",
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
    """Reusable country and level groups declared by the source registry."""

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
        return cls(country_sets=country_sets, event_level_sets=event_level_sets)

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
        """Expand level-set tokens and normalize explicit level labels."""

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
    def from_mapping(cls, values: Mapping[str, object]) -> "EventSource":
        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            priority=_required_int(values, "priority"),
            scope=_required_str(values, "scope"),
            regions=tuple(_normalize_region(region) for region in _string_tuple(values, "regions")),
            countries=_string_tuple(values, "countries"),
            disciplines=tuple(discipline.lower() for discipline in _string_tuple(values, "disciplines")),
            event_levels=_string_tuple(values, "event_levels"),
            source_type=_required_str(values, "source_type"),
            base_url=_optional_str(values, "base_url"),
            status=_required_str(values, "status"),
            notes=_required_str(values, "notes"),
        )


@dataclass(frozen=True)
class EventSourceRegistry:
    """Loaded event source registry plus coverage metadata."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> "EventSourceRegistry":
        coverage_targets = CoverageTargets.from_mapping(
            _required_mapping(values, "coverage_targets")
        )
        sources = tuple(
            sorted(
                (EventSource.from_mapping(item) for item in _required_items(values, "sources")),
                key=lambda source: (
                    source.priority,
                    source.id != _required_str(values, "primary_source_id"),
                    source.id,
                ),
            )
        )
        return cls(
            version=_required_int(values, "version"),
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=tuple(
                _normalize_region(region) for region in _string_tuple(values, "priority_regions")
            ),
            coverage_targets=coverage_targets,
            sources=sources,
        )

    @classmethod
    def from_path(cls, path: Path | str = DATA_FILE) -> "EventSourceRegistry":
        with Path(path).open(encoding="utf-8") as source_file:
            return cls.from_mapping(json.load(source_file))

    def filtered_sources(self, *, include_planned: bool = True) -> list[EventSource]:
        statuses = {"active", "planned"} if include_planned else {"active"}
        return [source for source in self.sources if source.status in statuses]

    def expanded_countries(self, source: EventSource) -> tuple[str, ...]:
        return self.coverage_targets.expand_countries(source.countries)

    def expanded_event_levels(self, source: EventSource) -> tuple[str, ...]:
        return self.coverage_targets.expand_event_levels(source.event_levels)

    def all_countries(self) -> tuple[str, ...]:
        return self.coverage_targets.country_sets["all_fei_member_nations"]

    def all_national_event_levels(self) -> tuple[str, ...]:
        return self.coverage_targets.event_level_sets["all_national_and_regional_levels"]

    def sources_for_region(
        self, region: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = _normalize_region(region)
        return [
            source
            for source in self.filtered_sources(include_planned=include_planned)
            if "global" in source.regions or normalized_region in source.regions
        ]

    def sources_for_country(
        self, country: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources that can cover a country code."""

        normalized_country = _normalize_country_code(country)
        return [
            source
            for source in self.filtered_sources(include_planned=include_planned)
            if normalized_country in self.expanded_countries(source)
        ]

    def sources_for_event_level(
        self, event_level: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources that can cover an event level label or registry token."""

        normalized_level = _normalize_event_level(event_level)
        return [
            source
            for source in self.filtered_sources(include_planned=include_planned)
            if normalized_level in self.expanded_event_levels(source)
        ]


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the source registry with country and level coverage targets."""

    return EventSourceRegistry.from_path(path)


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

    return load_event_source_registry(path).sources_for_region(
        region, include_planned=include_planned
    )


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country code while preserving priorities."""

    return load_event_source_registry(path).sources_for_country(
        country, include_planned=include_planned
    )


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a national, regional, or FEI event level."""

    return load_event_source_registry(path).sources_for_event_level(
        event_level, include_planned=include_planned
    )


def _normalize_country_code(country: str) -> str:
    normalized = country.strip().upper().replace(" ", "_")
    if not normalized:
        raise ValueError("country must be a non-empty string")
    return COUNTRY_ALIASES.get(normalized, normalized)


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
    values: Mapping[str, object], key: str
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
