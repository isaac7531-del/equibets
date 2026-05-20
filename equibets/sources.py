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
ALL_COUNTRY_MARKERS = frozenset({"all_fei_member_nations", "all_countries"})
ALL_LEVEL_MARKERS = frozenset({"all_eventing_levels", "all_levels"})


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

    def covers_region(self, region: str) -> bool:
        """Return whether the source covers a region name."""

        normalized_region = _normalize_token(region)
        return "global" in self.regions or normalized_region in self.regions

    def covers_country(self, country: str) -> bool:
        """Return whether the source covers a country code or country marker."""

        normalized_country = country.strip().upper()
        return any(
            source_country in ALL_COUNTRY_MARKERS
            or source_country.upper() == normalized_country
            for source_country in self.countries
        )

    def covers_level(self, event_level: str) -> bool:
        """Return whether the source covers a requested eventing level."""

        normalized_level = _normalize_token(event_level)
        return any(
            source_level in ALL_LEVEL_MARKERS
            or _normalize_token(source_level) == normalized_level
            for source_level in self.event_levels
        )

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

    return [
        source
        for source in load_event_sources(path)
        if source.status in _allowed_statuses(include_planned)
        and source.covers_region(region)
    ]


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    event_level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a country, optionally narrowed to one level."""

    return [
        source
        for source in load_event_sources(path)
        if source.status in _allowed_statuses(include_planned)
        and source.covers_country(country)
        and (event_level is None or source.covers_level(event_level))
    ]


def sources_for_level(
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering an eventing level across all countries."""

    return [
        source
        for source in load_event_sources(path)
        if source.status in _allowed_statuses(include_planned)
        and source.covers_level(event_level)
    ]


def _allowed_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


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
