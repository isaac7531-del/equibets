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
class SourceRegistry:
    """Structured data loaded from the event-results source registry."""

    sources: tuple[EventSource, ...]
    country_groups: dict[str, tuple[str, ...]]
    event_level_groups: dict[str, tuple[str, ...]]


def load_source_registry(path: Path | str = DATA_FILE) -> SourceRegistry:
    """Load the full source registry with expandable coverage groups."""

    payload = _load_payload(path)
    sources = tuple(
        sorted(
            (EventSource.from_mapping(item) for item in payload["sources"]),
            key=lambda source: (source.priority, source.id != "data_fei", source.id),
        )
    )
    return SourceRegistry(
        sources=sources,
        country_groups=_group_mapping(payload, "country_groups"),
        event_level_groups=_group_mapping(payload, "event_level_groups"),
    )


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_source_registry(path).sources)


def load_country_groups(path: Path | str = DATA_FILE) -> dict[str, tuple[str, ...]]:
    """Load named country-code groups from the source registry."""

    return load_source_registry(path).country_groups


def load_event_level_groups(path: Path | str = DATA_FILE) -> dict[str, tuple[str, ...]]:
    """Load named event-level groups from the source registry."""

    return load_source_registry(path).event_level_groups


def source_country_codes(
    source: EventSource,
    *,
    path: Path | str = DATA_FILE,
) -> tuple[str, ...]:
    """Return expanded country codes covered by a source."""

    return _expand_grouped_values(
        source.countries,
        load_country_groups(path),
        normalizer=_normalize_country_code,
    )


def source_event_levels(
    source: EventSource,
    *,
    path: Path | str = DATA_FILE,
) -> tuple[str, ...]:
    """Return expanded event levels covered by a source."""

    return _expand_grouped_values(
        source.event_levels,
        load_event_level_groups(path),
        normalizer=_normalize_token,
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
    country_code: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country while preserving global priorities."""

    normalized_country = _normalize_country_code(country_code)
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_country in source_country_codes(source, path=path)
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an event level while preserving priorities."""

    normalized_level = _normalize_token(event_level)
    statuses = {"active", "planned"} if include_planned else {"active"}

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and normalized_level in source_event_levels(source, path=path)
    ]


def _load_payload(path: Path | str) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    if not isinstance(payload, dict):
        raise ValueError("source registry must be a JSON object")
    return payload


def _group_mapping(
    payload: dict[str, object],
    key: str,
) -> dict[str, tuple[str, ...]]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")

    groups: dict[str, tuple[str, ...]] = {}
    for group_id, group_values in value.items():
        if not isinstance(group_id, str) or not group_id:
            raise ValueError(f"{key} group names must be non-empty strings")
        groups[group_id] = _validated_string_tuple(group_values, key)
    return groups


def _expand_grouped_values(
    values: tuple[str, ...],
    groups: dict[str, tuple[str, ...]],
    *,
    normalizer,
) -> tuple[str, ...]:
    expanded: list[str] = []
    seen: set[str] = set()

    def add_value(value: str) -> None:
        if value in groups:
            for group_value in groups[value]:
                add_value(group_value)
            return

        normalized_value = normalizer(value)
        if normalized_value not in seen:
            seen.add(normalized_value)
            expanded.append(normalized_value)

    for value in values:
        add_value(value)

    return tuple(expanded)


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
    return _validated_string_tuple(value, key)


def _validated_string_tuple(value: object, key: str) -> tuple[str, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _normalize_country_code(value: str) -> str:
    return value.strip().upper()


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")
