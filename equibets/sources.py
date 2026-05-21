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
FEDERATION_DATA_FILE = DATA_DIR / "national_federations.json"
ALL_FEI_MEMBER_NATIONS = "all_fei_member_nations"
ALL_FEI_EUROPE_MEMBER_NATIONS = "all_fei_europe_member_nations"
EUROPEAN_FEI_GROUPS = frozenset({"Group EEA", "Group EEF"})


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
class NationalFederation:
    """One FEI-affiliated national federation used for coverage planning."""

    noc: str
    country_name: str
    fei_group: str
    federation_name: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "NationalFederation":
        return cls(
            noc=_required_str(values, "noc"),
            country_name=_required_str(values, "country_name"),
            fei_group=_required_str(values, "fei_group"),
            federation_name=_required_str(values, "federation_name"),
        )


@dataclass(frozen=True)
class NationalFederationRegistry:
    """FEI national federation coverage registry."""

    source_url: str
    updated_at: str
    national_event_levels: tuple[str, ...]
    federations: tuple[NationalFederation, ...]


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    sources = [EventSource.from_mapping(item) for item in payload["sources"]]
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def load_national_federation_registry(
    path: Path | str = FEDERATION_DATA_FILE,
) -> NationalFederationRegistry:
    """Load FEI national federation coverage data."""

    with Path(path).open(encoding="utf-8") as federation_file:
        payload = json.load(federation_file)

    federations = tuple(
        sorted(
            (NationalFederation.from_mapping(item) for item in payload["federations"]),
            key=lambda federation: federation.noc,
        )
    )
    return NationalFederationRegistry(
        source_url=_required_str(payload, "source_url"),
        updated_at=_required_str(payload, "updated_at"),
        national_event_levels=_string_tuple(payload, "national_event_levels"),
        federations=federations,
    )


def load_national_federations(path: Path | str = FEDERATION_DATA_FILE) -> list[NationalFederation]:
    """Load FEI-affiliated national federations sorted by NOC code."""

    return list(load_national_federation_registry(path).federations)


def national_event_levels(path: Path | str = FEDERATION_DATA_FILE) -> tuple[str, ...]:
    """Return the coarse national-event tiers tracked for every federation."""

    return load_national_federation_registry(path).national_event_levels


def expand_country_codes(
    countries: Iterable[str],
    *,
    federation_path: Path | str = FEDERATION_DATA_FILE,
) -> tuple[str, ...]:
    """Expand source-registry coverage tokens into concrete FEI NOC codes."""

    federations = load_national_federations(federation_path)
    expanded: list[str] = []
    seen: set[str] = set()

    def append(code: str) -> None:
        if code not in seen:
            expanded.append(code)
            seen.add(code)

    for country in countries:
        if country == ALL_FEI_MEMBER_NATIONS:
            for federation in federations:
                append(federation.noc)
        elif country == ALL_FEI_EUROPE_MEMBER_NATIONS:
            for federation in federations:
                if federation.fei_group in EUROPEAN_FEI_GROUPS:
                    append(federation.noc)
        else:
            append(country)

    return tuple(expanded)


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
