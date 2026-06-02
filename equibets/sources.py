"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader coverage.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "event_sources.json"
COVERAGE_FILE = Path(__file__).resolve().parents[1] / "data" / "source_coverage.json"


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


def load_country_groups(path: Path | str = COVERAGE_FILE) -> dict[str, tuple[str, ...]]:
    """Load named country-code groups used by the source registry."""

    with Path(path).open(encoding="utf-8") as coverage_file:
        payload = json.load(coverage_file)

    return {
        _required_str(item, "id"): _string_tuple(item, "countries")
        for item in _required_list(payload, "country_groups")
    }


def load_event_level_groups(path: Path | str = COVERAGE_FILE) -> dict[str, tuple[str, ...]]:
    """Load named event-level groups used by source coverage checks."""

    with Path(path).open(encoding="utf-8") as coverage_file:
        payload = json.load(coverage_file)

    return {
        _required_str(item, "id"): _string_tuple(item, "levels")
        for item in _required_list(payload, "event_level_groups")
    }


def expand_country_codes(
    countries: Iterable[str],
    *,
    coverage_path: Path | str = COVERAGE_FILE,
) -> tuple[str, ...]:
    """Expand registry country groups into concrete FEI country/NOC codes."""

    return _expand_country_codes(countries, load_country_groups(coverage_path))


def _expand_country_codes(
    countries: Iterable[str],
    groups: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...]:
    """Expand country groups with already-loaded coverage metadata."""

    expanded: set[str] = set()
    for country in countries:
        expanded.update(groups.get(country, (country,)))
    return tuple(sorted(expanded))


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
    country: str,
    *,
    path: Path | str = DATA_FILE,
    coverage_path: Path | str = COVERAGE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a FEI country/NOC code."""

    normalized_country = country.strip().upper()
    statuses = {"active", "planned"} if include_planned else {"active"}
    country_groups = load_country_groups(coverage_path)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_country in _expand_country_codes(source.countries, country_groups)
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources advertising a source-level coverage tag."""

    normalized_level = _normalize_token(event_level)
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_level in {_normalize_token(level) for level in source.event_levels}
    ]


def sources_for_country_and_event_level(
    country: str,
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    coverage_path: Path | str = COVERAGE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering both a FEI country/NOC code and a level tag."""

    level_source_ids = {
        source.id
        for source in sources_for_event_level(
            event_level,
            path=path,
            include_planned=include_planned,
        )
    }
    return [
        source
        for source in sources_for_country(
            country,
            path=path,
            coverage_path=coverage_path,
            include_planned=include_planned,
        )
        if source.id in level_source_ids
    ]


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


def _required_list(values: Mapping[str, object], key: str) -> list[dict[str, object]]:
    value = values.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{key} must be a list of objects")
    return value


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_")
