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
COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")


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

    payload = _load_registry_payload(path)
    return _sorted_sources(payload)

def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country while preserving source priority."""

    normalized_country = _normalize_country_code(country)
    payload = _load_registry_payload(path)
    statuses = _matching_statuses(include_planned)

    return [
        source
        for source in _sorted_sources(payload)
        if source.status in statuses
        and _source_covers_country(source, normalized_country, payload)
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level while preserving priority."""

    normalized_level = _normalize_event_level(event_level)
    payload = _load_registry_payload(path)
    statuses = _matching_statuses(include_planned)

    return [
        source
        for source in _sorted_sources(payload)
        if source.status in statuses
        and _source_covers_event_level(source, normalized_level, payload)
    ]


def sources_for_country_and_level(
    country: str,
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering both a country and an event level."""

    normalized_country = _normalize_country_code(country)
    normalized_level = _normalize_event_level(event_level)
    payload = _load_registry_payload(path)
    statuses = _matching_statuses(include_planned)

    return [
        source
        for source in _sorted_sources(payload)
        if source.status in statuses
        and _source_covers_country(source, normalized_country, payload)
        and _source_covers_event_level(source, normalized_level, payload)
    ]


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = region.lower().replace(" ", "_")
    payload = _load_registry_payload(path)
    statuses = _matching_statuses(include_planned)

    return [
        source
        for source in _sorted_sources(payload)
        if source.status in statuses
        and ("global" in source.regions or normalized_region in source.regions)
    ]


def _load_registry_payload(path: Path | str) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, dict):
        raise ValueError("event source registry must be a JSON object")
    return payload


def _sorted_sources(payload: dict[str, object]) -> list[EventSource]:
    source_values = payload.get("sources")
    if not isinstance(source_values, Iterable) or isinstance(source_values, (str, bytes)):
        raise ValueError("sources must be a list of source mappings")

    sources: list[EventSource] = []
    for item in source_values:
        if not isinstance(item, dict):
            raise ValueError("sources must contain only source mappings")
        sources.append(EventSource.from_mapping(item))

    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def _matching_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _source_covers_country(
    source: EventSource,
    country: str,
    payload: dict[str, object],
) -> bool:
    country_groups = _registry_mapping(payload, "country_groups")

    for country_scope in source.countries:
        if country_scope.upper() == country:
            return True

        group = country_groups.get(country_scope)
        if group is not None and _country_group_covers(country_scope, group, country):
            return True

    return False


def _country_group_covers(group_id: str, value: object, country: str) -> bool:
    if not isinstance(value, dict):
        raise ValueError(f"country group {group_id} must be a mapping")

    match_type = value.get("match_type")
    if match_type == "any_iso3":
        return True
    if match_type == "country_list":
        return country in _strings_from_value(value.get("countries"), f"{group_id}.countries")

    raise ValueError(f"country group {group_id} has unsupported match_type")


def _source_covers_event_level(
    source: EventSource,
    event_level: str,
    payload: dict[str, object],
) -> bool:
    event_level_groups = _registry_mapping(payload, "event_level_groups")

    for level_scope in source.event_levels:
        if _normalize_event_level(level_scope) == event_level:
            return True

        group = event_level_groups.get(level_scope)
        if group is not None and event_level in _strings_from_value(group, level_scope):
            return True

    return False


def _registry_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return value


def _normalize_country_code(country: str) -> str:
    normalized = country.strip().upper()
    if not COUNTRY_CODE_PATTERN.fullmatch(normalized):
        raise ValueError("country must be a three-letter country code")
    return normalized


def _normalize_event_level(event_level: str) -> str:
    normalized = event_level.strip().lower().replace(" ", "_").replace("-", "_")
    if not normalized:
        raise ValueError("event_level must be a non-empty string")
    return normalized


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
    return _strings_from_value(values.get(key), key)


def _strings_from_value(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
