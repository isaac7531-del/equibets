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
COUNTRY_SCOPE_FILE = Path(__file__).resolve().parents[1] / "data" / "country_scopes.json"


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
class CountryScope:
    """A reusable group of FEI/NOC country codes used by source coverage."""

    id: str
    name: str
    match: str
    countries: tuple[str, ...]
    notes: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CountryScope":
        match = _required_str(values, "match")
        if match not in {"explicit", "wildcard"}:
            raise ValueError("match must be explicit or wildcard")

        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            match=match,
            countries=tuple(
                sorted(
                    _normalize_country_code(item)
                    for item in _string_tuple(values, "countries")
                )
            ),
            notes=_required_str(values, "notes"),
        )

    def covers(self, country: str) -> bool:
        """Return whether this scope covers a normalized FEI/NOC country code."""

        if self.match == "wildcard":
            return True
        return _normalize_country_code(country) in self.countries


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    sources = [EventSource.from_mapping(item) for item in payload["sources"]]
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def load_country_scopes(path: Path | str = COUNTRY_SCOPE_FILE) -> dict[str, CountryScope]:
    """Load named country scopes used by event source coverage."""

    with Path(path).open(encoding="utf-8") as scope_file:
        payload = json.load(scope_file)

    scopes = [CountryScope.from_mapping(item) for item in payload["scopes"]]
    return {scope.id: scope for scope in scopes}


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    normalized_region = _normalize_token(region)
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
    country_scope_path: Path | str = COUNTRY_SCOPE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources that can cover a FEI/NOC country code."""

    scopes = load_country_scopes(country_scope_path)
    return [
        source
        for source in load_event_sources(path)
        if source.status in _included_statuses(include_planned)
        and _source_covers_country(source, country, scopes)
    ]


def sources_for_event_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources that publish a registry event-level scope."""

    normalized_level = _normalize_token(event_level)
    return [
        source
        for source in load_event_sources(path)
        if source.status in _included_statuses(include_planned)
        and normalized_level in source.event_levels
    ]


def sources_for_national_events(
    *,
    country: str | None = None,
    event_level: str | None = None,
    path: Path | str = DATA_FILE,
    country_scope_path: Path | str = COUNTRY_SCOPE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return national-event sources, optionally narrowed by country and level."""

    scopes = load_country_scopes(country_scope_path)
    normalized_level = _normalize_token(event_level) if event_level else None
    return [
        source
        for source in load_event_sources(path)
        if source.status in _included_statuses(include_planned)
        and source.scope == "national"
        and (country is None or _source_covers_country(source, country, scopes))
        and (normalized_level is None or normalized_level in source.event_levels)
    ]


def _source_covers_country(
    source: EventSource,
    country: str,
    scopes: dict[str, CountryScope],
) -> bool:
    normalized_country = _normalize_country_code(country)
    for country_or_scope in source.countries:
        if _normalize_country_code(country_or_scope) == normalized_country:
            return True

        scope = scopes.get(country_or_scope)
        if scope is not None and scope.covers(normalized_country):
            return True

    return False


def _included_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_country_code(country: str) -> str:
    normalized_country = country.strip().upper().replace(" ", "_")
    if not normalized_country:
        raise ValueError("country must be a non-empty FEI/NOC code")
    return normalized_country


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


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
