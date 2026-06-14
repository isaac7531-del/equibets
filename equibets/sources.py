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
NATIONAL_EVENT_COVERAGE_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "national_event_coverage.json"
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
class NationalEventLevel:
    """A national-event level tier covered by national federation feeds."""

    id: str
    name: str
    category: str
    notes: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "NationalEventLevel":
        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            category=_required_str(values, "category"),
            notes=_required_str(values, "notes"),
        )


@dataclass(frozen=True)
class NationalFederation:
    """One FEI national federation and its configured eventing coverage."""

    noc_code: str
    country: str
    fei_group: str
    federation_name: str
    source_ids: tuple[str, ...]
    event_levels: tuple[str, ...]

    @classmethod
    def from_mapping(
        cls,
        values: dict[str, object],
        *,
        event_levels: tuple[str, ...],
        group_source_overrides: dict[str, tuple[str, ...]],
        country_source_overrides: dict[str, tuple[str, ...]],
    ) -> "NationalFederation":
        noc_code = _required_str(values, "noc_code").upper()
        fei_group = _required_str(values, "fei_group")
        source_ids = _unique_strings(
            (
                "data_fei",
                *group_source_overrides.get(fei_group, ()),
                *country_source_overrides.get(noc_code, ()),
                "global_national_federations",
            )
        )
        return cls(
            noc_code=noc_code,
            country=_required_str(values, "country"),
            fei_group=fei_group,
            federation_name=_required_str(values, "federation_name"),
            source_ids=source_ids,
            event_levels=event_levels,
        )


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    payload = _read_json(path)
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


def load_national_event_levels(
    path: Path | str = NATIONAL_EVENT_COVERAGE_FILE,
) -> list[NationalEventLevel]:
    """Load national-event levels covered by national federation feeds."""

    payload = _read_json(path)
    levels = [
        NationalEventLevel.from_mapping(item)
        for item in payload["national_event_levels"]
    ]
    return sorted(levels, key=lambda level: level.id)


def load_national_federations(
    path: Path | str = NATIONAL_EVENT_COVERAGE_FILE,
) -> list[NationalFederation]:
    """Load FEI national federations with country and level coverage."""

    payload = _read_json(path)
    event_levels = tuple(level.id for level in load_national_event_levels(path))
    group_source_overrides = _source_override_map(payload, "group_source_overrides")
    country_source_overrides = _source_override_map(payload, "country_source_overrides")
    federations = [
        NationalFederation.from_mapping(
            item,
            event_levels=event_levels,
            group_source_overrides=group_source_overrides,
            country_source_overrides=country_source_overrides,
        )
        for item in payload["federations"]
    ]
    _validate_unique_noc_codes(federations)
    return sorted(federations, key=lambda federation: federation.noc_code)


def national_federation_for_country(
    country_code: str,
    *,
    path: Path | str = NATIONAL_EVENT_COVERAGE_FILE,
) -> NationalFederation:
    """Return the FEI national federation for a NOC country code."""

    normalized_country_code = country_code.upper()
    for federation in load_national_federations(path):
        if federation.noc_code == normalized_country_code:
            return federation
    raise ValueError(f"Unknown FEI national federation country code: {country_code}")


def sources_for_country(
    country_code: str,
    *,
    source_path: Path | str = DATA_FILE,
    coverage_path: Path | str = NATIONAL_EVENT_COVERAGE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return source priorities for a FEI national federation country code."""

    federation = national_federation_for_country(country_code, path=coverage_path)
    statuses = {"active", "planned"} if include_planned else {"active"}
    source_ids = set(federation.source_ids)
    return [
        source
        for source in load_event_sources(source_path)
        if source.id in source_ids and source.status in statuses
    ]


def _read_json(path: Path | str) -> dict[str, object]:
    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _source_override_map(
    payload: dict[str, object],
    key: str,
) -> dict[str, tuple[str, ...]]:
    raw_value = payload.get(key, {})
    if not isinstance(raw_value, dict):
        raise ValueError(f"{key} must be an object")
    return {
        _required_str({"key": map_key}, "key"): _string_tuple({"value": map_value}, "value")
        for map_key, map_value in raw_value.items()
    }


def _validate_unique_noc_codes(federations: list[NationalFederation]) -> None:
    seen: set[str] = set()
    for federation in federations:
        if federation.noc_code in seen:
            raise ValueError(f"Duplicate NOC code in national coverage: {federation.noc_code}")
        seen.add(federation.noc_code)


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


def _unique_strings(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return tuple(unique_values)
