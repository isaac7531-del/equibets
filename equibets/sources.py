"""Event-result source registry helpers.

The project prioritizes FEI data while still tracking national-event sources
that are important for broader coverage.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_FILE = DATA_DIR / "event_sources.json"
SCOPE_FILE = DATA_DIR / "national_event_scope.json"


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
    scope_path: Path | str = SCOPE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country code while preserving priorities."""

    normalized_country = _normalize_country(country)
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_country in expand_country_codes(source.countries, scope_path=scope_path)
    ]


def sources_for_level(
    level: str,
    *,
    path: Path | str = DATA_FILE,
    scope_path: Path | str = SCOPE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level while preserving priorities."""

    normalized_level = _normalize_level(level)
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_level
        in {
            _normalize_level(source_level)
            for source_level in expand_event_levels(source.event_levels, scope_path=scope_path)
        }
    ]


def expand_country_codes(
    countries: Iterable[str],
    *,
    scope_path: Path | str = SCOPE_FILE,
) -> tuple[str, ...]:
    """Resolve country group aliases such as ``all_countries`` to ISO codes."""

    groups = _load_scope_groups("country_groups", scope_path)
    return tuple(_normalize_country(country) for country in _expand_values(countries, groups))


def expand_event_levels(
    event_levels: Iterable[str],
    *,
    scope_path: Path | str = SCOPE_FILE,
) -> tuple[str, ...]:
    """Resolve event-level group aliases such as ``all_national_event_levels``."""

    groups = _load_scope_groups("event_level_groups", scope_path)
    return tuple(_expand_values(event_levels, groups))


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


def _load_scope_groups(
    group_name: str,
    scope_path: Path | str,
) -> dict[str, tuple[str, ...]]:
    with Path(scope_path).open(encoding="utf-8") as scope_file:
        payload = json.load(scope_file)

    raw_groups = payload.get(group_name)
    if not isinstance(raw_groups, dict):
        raise ValueError(f"{group_name} must be an object")

    groups: dict[str, tuple[str, ...]] = {}
    for key, values in raw_groups.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{group_name} keys must be non-empty strings")
        if not isinstance(values, Iterable) or isinstance(values, (str, bytes)):
            raise ValueError(f"{group_name}.{key} must be a list of strings")
        items = tuple(values)
        if not all(isinstance(item, str) and item for item in items):
            raise ValueError(f"{group_name}.{key} must contain only non-empty strings")
        groups[key] = items
    return groups


def _expand_values(
    values: Iterable[str],
    groups: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    expanded: list[str] = []
    seen: set[str] = set()

    def add(value: str, stack: tuple[str, ...]) -> None:
        if value in groups:
            if value in stack:
                cycle = " -> ".join((*stack, value))
                raise ValueError(f"Scope group cycle detected: {cycle}")
            for item in groups[value]:
                add(item, (*stack, value))
            return

        if value not in seen:
            seen.add(value)
            expanded.append(value)

    for value in values:
        add(value, ())
    return tuple(expanded)


def _normalize_country(country: str) -> str:
    return country.strip().upper()


def _normalize_level(level: str) -> str:
    return level.strip().lower().replace(" ", "_")
