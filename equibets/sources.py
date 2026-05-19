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
ALL_COUNTRY_MARKERS = {"all_countries", "all_fei_member_nations"}
ALL_EVENT_LEVEL_MARKER = "all_eventing_levels"
ALL_FEI_EVENT_LEVEL_MARKER = "all_fei_eventing_levels"
ALL_NATIONAL_EVENT_LEVEL_MARKER = "all_national_eventing_levels"


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
    statuses = _included_statuses(include_planned)

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
    statuses = _included_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses and _source_covers_country(source, normalized_country)
    ]


def sources_for_event(
    country_code: str,
    event_level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources covering a country and event level."""

    normalized_country = _normalize_country_code(country_code)
    normalized_level = _normalize_event_level(event_level)
    statuses = _included_statuses(include_planned)

    return [
        source
        for source in load_event_sources(path)
        if source.status in statuses
        and _source_covers_country(source, normalized_country)
        and _source_covers_event_level(source, normalized_level)
    ]


def _included_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _source_covers_country(source: EventSource, country_code: str) -> bool:
    country_tokens = {_normalize_country_token(country) for country in source.countries}
    return bool(country_tokens & ALL_COUNTRY_MARKERS) or country_code in country_tokens


def _source_covers_event_level(source: EventSource, event_level: str) -> bool:
    level_tokens = {_normalize_event_level(level) for level in source.event_levels}
    if ALL_EVENT_LEVEL_MARKER in level_tokens or event_level in level_tokens:
        return True
    if event_level.startswith("cci"):
        return ALL_FEI_EVENT_LEVEL_MARKER in level_tokens
    return ALL_NATIONAL_EVENT_LEVEL_MARKER in level_tokens


def _normalize_country_code(country_code: str) -> str:
    normalized = country_code.strip().upper()
    if not normalized:
        raise ValueError("country_code must be a non-empty string")
    return normalized


def _normalize_country_token(country: str) -> str:
    if country.isupper() and len(country) == 3:
        return country
    return country.strip().lower()


def _normalize_event_level(event_level: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", event_level.lower()).strip("_")
    if not normalized:
        raise ValueError("event_level must be a non-empty string")

    star_match = re.match(r"^(cc[ni])_?([1-5])", normalized)
    if star_match:
        return "".join(star_match.groups())
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
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
