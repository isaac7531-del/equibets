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
COVERAGE_FILE = Path(__file__).resolve().parents[1] / "data" / "national_event_coverage.json"


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

    def resolved_countries(
        self,
        *,
        coverage_path: Path | str = COVERAGE_FILE,
    ) -> tuple[str, ...]:
        """Return concrete FEI/NOC country codes covered by this source."""

        return expand_country_tokens(self.countries, coverage_path=coverage_path)

    def resolved_event_levels(
        self,
        *,
        coverage_path: Path | str = COVERAGE_FILE,
    ) -> tuple[str, ...]:
        """Return concrete normalized event-level ids covered by this source."""

        return expand_event_level_tokens(self.event_levels, coverage_path=coverage_path)

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
class EventLevel:
    """A normalized eventing level used for national-event coverage."""

    id: str
    name: str
    scope: str
    order: int
    aliases: tuple[str, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventLevel":
        return cls(
            id=_normalize_level_id(_required_str(values, "id")),
            name=_required_str(values, "name"),
            scope=_required_str(values, "scope"),
            order=_required_int(values, "order"),
            aliases=_string_tuple(values, "aliases"),
        )


@dataclass(frozen=True)
class CoverageTarget:
    """One source/country/level combination that should be collected."""

    source_id: str
    source_priority: int
    country: str
    event_level: str


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    sources = [EventSource.from_mapping(item) for item in payload["sources"]]
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def load_country_sets(
    path: Path | str = COVERAGE_FILE,
) -> dict[str, tuple[str, ...]]:
    """Load named FEI country-code sets used by the source registry."""

    payload = _load_coverage_payload(path)
    country_sets = payload.get("country_sets")
    if not isinstance(country_sets, dict):
        raise ValueError("country_sets must be an object")

    parsed: dict[str, tuple[str, ...]] = {}
    for set_id, raw_set in country_sets.items():
        if not isinstance(set_id, str) or not set_id:
            raise ValueError("country set ids must be non-empty strings")
        if not isinstance(raw_set, dict):
            raise ValueError(f"{set_id} must be an object")

        countries = _string_tuple(raw_set, "countries")
        expected_count = raw_set.get("expected_count")
        if expected_count is not None:
            if not isinstance(expected_count, int):
                raise ValueError(f"{set_id}.expected_count must be an integer")
            if len(countries) != expected_count:
                raise ValueError(
                    f"{set_id} expected {expected_count} countries, found {len(countries)}",
                )
        parsed[set_id] = countries

    return parsed


def load_event_levels(path: Path | str = COVERAGE_FILE) -> list[EventLevel]:
    """Load the normalized level taxonomy for all supported eventing levels."""

    payload = _load_coverage_payload(path)
    event_levels = payload.get("event_levels")
    if not isinstance(event_levels, list):
        raise ValueError("event_levels must be a list")

    levels = [EventLevel.from_mapping(item) for item in event_levels]
    return sorted(levels, key=lambda level: (level.order, level.id))


def load_event_level_sets(
    path: Path | str = COVERAGE_FILE,
) -> dict[str, tuple[str, ...]]:
    """Load named event-level groups used by the source registry."""

    payload = _load_coverage_payload(path)
    level_sets = payload.get("event_level_sets")
    if not isinstance(level_sets, dict):
        raise ValueError("event_level_sets must be an object")

    parsed: dict[str, tuple[str, ...]] = {}
    for set_id, values in level_sets.items():
        if not isinstance(set_id, str) or not set_id:
            raise ValueError("event level set ids must be non-empty strings")
        if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
            raise ValueError(f"{set_id} must be a list of strings")
        items = tuple(values)
        if not all(isinstance(item, str) and item for item in items):
            raise ValueError(f"{set_id} must contain only non-empty strings")
        parsed[_normalize_level_id(set_id)] = tuple(_normalize_level_id(item) for item in items)

    return parsed


def expand_country_tokens(
    countries: Iterable[str],
    *,
    coverage_path: Path | str = COVERAGE_FILE,
) -> tuple[str, ...]:
    """Expand country-set tokens into concrete FEI/NOC country codes."""

    country_sets = load_country_sets(coverage_path)
    expanded: list[str] = []
    for country in countries:
        if country in country_sets:
            expanded.extend(country_sets[country])
        else:
            expanded.append(country.upper())
    return _dedupe(expanded)


def expand_event_level_tokens(
    event_levels: Iterable[str],
    *,
    coverage_path: Path | str = COVERAGE_FILE,
) -> tuple[str, ...]:
    """Expand level-group tokens into concrete normalized level ids."""

    level_sets = load_event_level_sets(coverage_path)
    expanded: list[str] = []

    def append_level(level_id: str, seen: set[str]) -> None:
        normalized_level_id = _normalize_level_id(level_id)
        if normalized_level_id in seen:
            raise ValueError(f"event level set cycle detected at {normalized_level_id}")
        children = level_sets.get(normalized_level_id)
        if children is None:
            expanded.append(normalized_level_id)
            return
        next_seen = {*seen, normalized_level_id}
        for child in children:
            append_level(child, next_seen)

    for event_level in event_levels:
        append_level(event_level, set())

    return _dedupe(expanded)


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
    event_level: str | None = None,
    path: Path | str = DATA_FILE,
    coverage_path: Path | str = COVERAGE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country and, optionally, a concrete level."""

    normalized_country = country.upper()
    normalized_level = _normalize_level_id(event_level) if event_level else None
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_country in source.resolved_countries(coverage_path=coverage_path)
        and (
            normalized_level is None
            or normalized_level in source.resolved_event_levels(coverage_path=coverage_path)
        )
    ]


def national_event_coverage(
    *,
    path: Path | str = DATA_FILE,
    coverage_path: Path | str = COVERAGE_FILE,
    include_planned: bool = True,
) -> list[CoverageTarget]:
    """Return the source/country/level matrix for national eventing updates."""

    statuses = {"active", "planned"} if include_planned else {"active"}
    targets = [
        CoverageTarget(
            source_id=source.id,
            source_priority=source.priority,
            country=country,
            event_level=event_level,
        )
        for source in load_event_sources(path)
        if source.status in statuses
        and source.scope == "national"
        and "eventing" in source.disciplines
        for country in source.resolved_countries(coverage_path=coverage_path)
        for event_level in source.resolved_event_levels(coverage_path=coverage_path)
    ]

    return sorted(
        targets,
        key=lambda target: (
            target.country,
            target.event_level,
            target.source_priority,
            target.source_id,
        ),
    )


def _load_coverage_payload(path: Path | str) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as coverage_file:
        payload = json.load(coverage_file)
    if not isinstance(payload, dict):
        raise ValueError("coverage file must contain a JSON object")
    return payload


def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return tuple(deduped)


def _normalize_level_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


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
