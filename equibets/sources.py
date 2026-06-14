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
    """Declared country and level coverage goals for event-results ingestion."""

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
    """Loaded event-results source registry."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        primary_source_id = _required_str(values, "primary_source_id")
        raw_sources = values.get("sources")
        if not isinstance(raw_sources, list):
            raise ValueError("sources must be a list")

        return cls(
            version=_required_int(values, "version"),
            primary_source_id=primary_source_id,
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values, "coverage_targets")
            ),
            sources=tuple(
                sorted(
                    (EventSource.from_mapping(item) for item in raw_sources),
                    key=lambda source: (
                        source.priority,
                        source.id != primary_source_id,
                        source.id,
                    ),
                )
            ),
        )

    def sources_for_country(
        self, country: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources with explicit or all-member coverage for a country."""

        normalized_country = country.strip().upper()
        statuses = _statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses
            and (
                normalized_country in source.countries
                or "all_fei_member_nations" in source.countries
            )
        ]

    def sources_for_event_level(
        self, event_level: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources that cover a canonical event level slug."""

        normalized_level = _normalize_event_level(event_level)
        statuses = _statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses and normalized_level in source.event_levels
        ]

    def sources_for_region(
        self, region: str, *, include_planned: bool = True
    ) -> list[EventSource]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = region.lower().replace(" ", "_")
        statuses = _statuses(include_planned)

        return [
            source
            for source in self.sources
            if source.status in statuses
            and ("global" in source.regions or normalized_region in source.regions)
        ]


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the event source registry and coverage targets."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

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
    """Return sources covering a canonical event level slug."""

    return load_event_source_registry(path).sources_for_event_level(
        event_level,
        include_planned=include_planned,
    )


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


def _statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_event_level(event_level: str) -> str:
    normalized = event_level.strip().lower().replace(" ", "_").replace("-", "_")
    normalized = normalized.replace("*", "").replace("__", "_")

    return {
        "cci_intro": "cci_intro",
        "cci1_intro": "cci1_intro",
        "cci1_s": "cci1_short",
        "cci1_short": "cci1_short",
        "cci2_s": "cci2_short",
        "cci2_short": "cci2_short",
        "cci2_l": "cci2_long",
        "cci2_long": "cci2_long",
        "cci3_s": "cci3_short",
        "cci3_short": "cci3_short",
        "cci3_l": "cci3_long",
        "cci3_long": "cci3_long",
        "cci4_s": "cci4_short",
        "cci4_short": "cci4_short",
        "cci4_l": "cci4_long",
        "cci4_long": "cci4_long",
        "cci5_l": "cci5_long",
        "cci5_long": "cci5_long",
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
    }.get(normalized, normalized)


def _required_mapping(values: dict[str, object], key: str) -> dict[str, object]:
    value = values.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
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
