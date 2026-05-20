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
GLOBAL_REGION = "global"
ALL_COUNTRIES = "all_countries"
ALL_EVENTING_LEVELS = "all_eventing_levels"
LEGACY_ALL_FEI_NATIONS = "all_fei_member_nations"


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
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region and optional level by priority."""

    normalized_region = _token_key(region)
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and _covers_region(source, normalized_region)
        and _covers_level(source, level)
    ]


def sources_for_country(
    country: str,
    *,
    level: str | None = None,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country and optional level by priority.

    ``country`` should be an ISO 3166-1 alpha-3 code such as ``GBR`` or ``USA``.
    Registry-wide country wildcards are used for sources that cover every
    country.
    """

    normalized_country = _country_key(country)
    statuses = _allowed_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and _covers_country(source, normalized_country)
        and _covers_level(source, level)
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


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


def _allowed_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _covers_region(source: EventSource, normalized_region: str) -> bool:
    regions = {_token_key(region) for region in source.regions}
    return GLOBAL_REGION in regions or normalized_region in regions


def _covers_country(source: EventSource, normalized_country: str) -> bool:
    countries = {_country_key(country) for country in source.countries}
    return (
        ALL_COUNTRIES in countries
        or LEGACY_ALL_FEI_NATIONS in countries
        or normalized_country in countries
    )


def _covers_level(source: EventSource, level: str | None) -> bool:
    if level is None:
        return True

    levels = {_token_key(event_level) for event_level in source.event_levels}
    return ALL_EVENTING_LEVELS in levels or _token_key(level) in levels


def _country_key(country: str) -> str:
    token = _token_key(country)
    if token.startswith("all_"):
        return token
    return country.strip().upper()


def _token_key(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")
