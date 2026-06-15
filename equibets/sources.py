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


@dataclass(frozen=True)
class CoverageTargets:
    """Coverage goals that every source registry should satisfy."""

    countries: tuple[str, ...]
    domestic_event_levels: tuple[str, ...]
    fei_event_levels: tuple[str, ...]

    @property
    def event_levels(self) -> tuple[str, ...]:
        """Return all event levels covered by the registry."""

        return self.domestic_event_levels + self.fei_event_levels

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        return cls(
            countries=_string_tuple(values, "countries"),
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
    """The configured source registry and its stated coverage targets."""

    version: int
    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventSourceRegistry":
        source_values = values.get("sources")
        if not isinstance(source_values, Iterable) or isinstance(
            source_values,
            (str, bytes),
        ):
            raise ValueError("sources must be a list of source mappings")

        sources = tuple(
            sorted(
                (EventSource.from_mapping(_required_mapping(item, "source")) for item in source_values),
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
            priority_regions=_string_tuple(values, "priority_regions"),
            coverage_targets=CoverageTargets.from_mapping(
                _required_mapping(values.get("coverage_targets"), "coverage_targets")
            ),
            sources=sources,
        )


def load_event_source_registry(path: Path | str = DATA_FILE) -> EventSourceRegistry:
    """Load the source registry and preserve global source priority ordering."""

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
    statuses = _included_statuses(include_planned)

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
    """Return global and exact-country sources for a country or country group."""

    normalized_country = _normalize_country(country)
    statuses = _included_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and (
            "all_fei_member_nations" in source.countries
            or normalized_country in {_normalize_country(item) for item in source.countries}
        )
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level while preserving source priority."""

    normalized_level = _normalize_event_level(event_level)
    statuses = _included_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and normalized_level in source.event_levels
    ]


def _included_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_country(country: str) -> str:
    stripped = country.strip()
    if stripped.lower().startswith("all_"):
        return stripped.lower().replace(" ", "_").replace("-", "_")
    return stripped.upper()


def _normalize_event_level(event_level: str) -> str:
    normalized = event_level.strip().lower()
    normalized = normalized.replace("*", "")
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")

    ordinal_levels = {
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
    }
    if normalized in ordinal_levels:
        return ordinal_levels[normalized]

    cci_match = re.fullmatch(r"cci([1-5])_(s|short|l|long)", normalized)
    if cci_match:
        level, length = cci_match.groups()
        length_name = "short" if length in {"s", "short"} else "long"
        return f"cci{level}_{length_name}"

    intro_match = re.fullmatch(r"cci([1-5]?)(?:_)?(intro|introductory)", normalized)
    if intro_match:
        level = intro_match.group(1)
        return f"cci{level}_introductory" if level else "cci_introductory"

    return normalized


def _required_mapping(value: object, key: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
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
