"""National federation coverage for domestic eventing results."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "national_federations.json"
ALL_FEI_MEMBER_NATIONS = "all_fei_member_nations"
ALL_FEI_EUROPE_MEMBER_NATIONS = "all_fei_europe_member_nations"


@dataclass(frozen=True)
class NationalFederation:
    """One FEI national federation in the national-event coverage registry."""

    noc_code: str
    country_name: str
    federation_name: str
    fei_group: str
    coverage_sources: tuple[str, ...]
    event_levels: tuple[str, ...]
    national_results_url: str | None
    status: str
    notes: str

    @property
    def country_code(self) -> str:
        """Alias used by result records and source country scopes."""

        return self.noc_code

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "NationalFederation":
        return cls(
            noc_code=_required_str(values, "noc_code"),
            country_name=_required_str(values, "country_name"),
            federation_name=_required_str(values, "federation_name"),
            fei_group=_required_str(values, "fei_group"),
            coverage_sources=_string_tuple(values, "coverage_sources"),
            event_levels=_string_tuple(values, "event_levels"),
            national_results_url=_optional_str(values, "national_results_url"),
            status=_required_str(values, "status"),
            notes=_required_str(values, "notes"),
        )


def load_national_federations(path: Path | str = DATA_FILE) -> list[NationalFederation]:
    """Load all FEI national federations sorted by NOC country code."""

    with Path(path).open(encoding="utf-8") as registry_file:
        payload = json.load(registry_file)

    federations = [NationalFederation.from_mapping(item) for item in payload["federations"]]
    return sorted(federations, key=lambda federation: federation.noc_code)


def federation_for_country(
    country_code: str,
    *,
    path: Path | str = DATA_FILE,
) -> NationalFederation:
    """Return the configured national federation for one FEI/NOC country code."""

    normalized_code = country_code.upper()
    for federation in load_national_federations(path):
        if federation.noc_code == normalized_code:
            return federation
    raise KeyError(f"Unknown FEI national federation country code: {country_code}")


def federations_for_source(
    source_id: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[NationalFederation]:
    """Return countries covered by a configured national source."""

    statuses = {"active", "planned"} if include_planned else {"active"}
    return [
        federation
        for federation in load_national_federations(path)
        if federation.status in statuses and source_id in federation.coverage_sources
    ]


def expand_country_scope(
    countries: Iterable[str],
    *,
    path: Path | str = DATA_FILE,
) -> tuple[str, ...]:
    """Expand symbolic country scopes from event_sources.json into country codes."""

    federations = load_national_federations(path)
    by_code = {federation.noc_code: federation for federation in federations}
    expanded: list[str] = []
    for country in countries:
        normalized_country = country.upper()
        if country == ALL_FEI_MEMBER_NATIONS:
            expanded.extend(federation.noc_code for federation in federations)
        elif country == ALL_FEI_EUROPE_MEMBER_NATIONS:
            expanded.extend(
                federation.noc_code
                for federation in federations
                if "europe_national_federations" in federation.coverage_sources
            )
        elif normalized_country in by_code:
            expanded.append(normalized_country)
        else:
            raise KeyError(f"Unknown national federation country scope: {country}")

    return tuple(sorted(dict.fromkeys(expanded)))


def event_levels_for_countries(
    countries: Iterable[str],
    *,
    path: Path | str = DATA_FILE,
) -> tuple[str, ...]:
    """Return all configured national-event levels for a country scope."""

    codes = expand_country_scope(countries, path=path)
    federations = {federation.noc_code: federation for federation in load_national_federations(path)}
    levels = [
        level
        for code in codes
        for level in federations[code].event_levels
    ]
    return tuple(sorted(dict.fromkeys(levels)))


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


def _string_tuple(values: dict[str, object], key: str) -> tuple[str, ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items
