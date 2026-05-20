"""National-event coverage scope and source selection helpers."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from equibets.sources import DATA_FILE, EventSource, load_event_sources


SCOPE_FILE = Path(__file__).resolve().parents[1] / "data" / "national_event_scope.json"


@dataclass(frozen=True)
class CountryGroup:
    """A country coverage target used by one or more event sources."""

    id: str
    name: str
    coverage: str
    member_count: int | None
    country_codes: tuple[str, ...]
    source_url: str | None
    notes: str
    regions: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CountryGroup":
        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            coverage=_required_str(values, "coverage"),
            member_count=_optional_int(values, "member_count"),
            country_codes=_string_tuple(values, "country_codes"),
            source_url=_optional_str(values, "source_url"),
            notes=_required_str(values, "notes"),
            regions=_string_tuple(values, "regions", default=()),
        )

    def covers_country(self, country_code: str) -> bool:
        """Return whether this group explicitly covers a country code."""

        normalized_code = country_code.upper()
        return "*" in self.country_codes or normalized_code in self.country_codes


@dataclass(frozen=True)
class EventLevelGroup:
    """A domestic level coverage target used by national-event sources."""

    id: str
    source_event_levels: tuple[str, ...]
    class_policy: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventLevelGroup":
        return cls(
            id=_required_str(values, "id"),
            source_event_levels=_string_tuple(values, "source_event_levels"),
            class_policy=_required_str(values, "class_policy"),
        )


@dataclass(frozen=True)
class NationalEventScope:
    """Scope metadata for collecting national and regional eventing results."""

    version: int
    updated_at: str
    coverage_goal: str
    country_groups: tuple[CountryGroup, ...]
    event_level_groups: tuple[EventLevelGroup, ...]
    update_order: tuple[str, ...]
    national_results_output_path: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "NationalEventScope":
        output = _required_mapping(values, "national_results_output")
        return cls(
            version=_required_int(values, "version"),
            updated_at=_required_str(values, "updated_at"),
            coverage_goal=_required_str(values, "coverage_goal"),
            country_groups=tuple(
                CountryGroup.from_mapping(item)
                for item in _mapping_sequence(values, "country_groups")
            ),
            event_level_groups=tuple(
                EventLevelGroup.from_mapping(item)
                for item in _mapping_sequence(values, "event_level_groups")
            ),
            update_order=_string_tuple(values, "update_order"),
            national_results_output_path=_required_str(output, "path"),
        )

    @property
    def all_national_event_levels(self) -> tuple[str, ...]:
        """Return all source-level scopes used for domestic events."""

        levels: list[str] = []
        for group in self.event_level_groups:
            for level in group.source_event_levels:
                if level not in levels:
                    levels.append(level)
        return tuple(levels)

    def country_group(self, group_id: str) -> CountryGroup | None:
        for group in self.country_groups:
            if group.id == group_id:
                return group
        return None


def load_national_event_scope(path: Path | str = SCOPE_FILE) -> NationalEventScope:
    """Load national-event collection scope metadata."""

    with Path(path).open(encoding="utf-8") as scope_file:
        payload = json.load(scope_file)
    return NationalEventScope.from_mapping(payload)


def public_update_sources(
    *,
    source_path: Path | str = DATA_FILE,
    scope_path: Path | str = SCOPE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return all public sources in the configured update order."""

    return _ordered_sources(
        source_path=source_path,
        scope_path=scope_path,
        include_planned=include_planned,
        national_only=False,
    )


def national_update_sources(
    *,
    source_path: Path | str = DATA_FILE,
    scope_path: Path | str = SCOPE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return national-event sources in the configured update order."""

    return _ordered_sources(
        source_path=source_path,
        scope_path=scope_path,
        include_planned=include_planned,
        national_only=True,
    )


def national_sources_for_country(
    country_code: str,
    *,
    event_level: str | None = None,
    source_path: Path | str = DATA_FILE,
    scope_path: Path | str = SCOPE_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return national sources that can contribute results for a country/level."""

    scope = load_national_event_scope(scope_path)
    requested_level = event_level.lower().replace(" ", "_") if event_level else None
    return [
        source
        for source in national_update_sources(
            source_path=source_path,
            scope_path=scope_path,
            include_planned=include_planned,
        )
        if _source_covers_country(source, country_code, scope)
        and (
            requested_level is None
            or requested_level in {_normalize_level(level) for level in source.event_levels}
        )
    ]


def build_update_plan(
    *,
    country_codes: Sequence[str] = (),
    event_levels: Sequence[str] = (),
    source_path: Path | str = DATA_FILE,
    scope_path: Path | str = SCOPE_FILE,
    include_planned: bool = True,
) -> dict[str, object]:
    """Build a JSON-serializable national-event source plan."""

    scope = load_national_event_scope(scope_path)
    normalized_levels = tuple(_normalize_level(level) for level in event_levels)
    if country_codes:
        sources_by_id: dict[str, EventSource] = {}
        for country_code in country_codes:
            for level in normalized_levels or (None,):
                for source in national_sources_for_country(
                    country_code,
                    event_level=level,
                    source_path=source_path,
                    scope_path=scope_path,
                    include_planned=include_planned,
                ):
                    sources_by_id[source.id] = source
        sources = [
            source
            for source in national_update_sources(
                source_path=source_path,
                scope_path=scope_path,
                include_planned=include_planned,
            )
            if source.id in sources_by_id
        ]
        countries: object = [country.upper() for country in country_codes]
    else:
        sources = national_update_sources(
            source_path=source_path,
            scope_path=scope_path,
            include_planned=include_planned,
        )
        countries = "all_fei_member_nations"

    return {
        "scope_version": scope.version,
        "scope_updated_at": scope.updated_at,
        "countries": countries,
        "event_levels": list(normalized_levels or scope.all_national_event_levels),
        "national_results_output": scope.national_results_output_path,
        "sources": [_source_to_mapping(source) for source in sources],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the national-event source update plan as JSON.",
    )
    parser.add_argument(
        "--country",
        action="append",
        default=[],
        help="NOC/ISO-3 country code to include. May be supplied more than once.",
    )
    parser.add_argument(
        "--event-level",
        action="append",
        default=[],
        help="Domestic source level to include, such as national or regional.",
    )
    parser.add_argument(
        "--active-only",
        action="store_true",
        help="Exclude planned sources that do not have crawlers yet.",
    )
    args = parser.parse_args(argv)

    plan = build_update_plan(
        country_codes=args.country,
        event_levels=args.event_level,
        include_planned=not args.active_only,
    )
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


def _ordered_sources(
    *,
    source_path: Path | str,
    scope_path: Path | str,
    include_planned: bool,
    national_only: bool,
) -> list[EventSource]:
    scope = load_national_event_scope(scope_path)
    source_by_id = {source.id: source for source in load_event_sources(source_path)}
    statuses = {"active", "planned"} if include_planned else {"active"}

    ordered: list[EventSource] = []
    for source_id in scope.update_order:
        source = source_by_id.get(source_id)
        if source is None or source.status not in statuses:
            continue
        if national_only and source.scope != "national":
            continue
        ordered.append(source)
    return ordered


def _source_covers_country(
    source: EventSource,
    country_code: str,
    scope: NationalEventScope,
) -> bool:
    normalized_code = country_code.upper()
    for country_ref in source.countries:
        if country_ref.upper() == normalized_code:
            return True
        group = scope.country_group(country_ref)
        if group is not None and group.covers_country(normalized_code):
            return True
    return False


def _source_to_mapping(source: EventSource) -> dict[str, object]:
    return {
        "id": source.id,
        "name": source.name,
        "priority": source.priority,
        "countries": list(source.countries),
        "event_levels": list(source.event_levels),
        "base_url": source.base_url,
        "status": source.status,
    }


def _normalize_level(level: str) -> str:
    return level.lower().replace(" ", "_")


def _required_mapping(values: dict[str, object], key: str) -> dict[str, object]:
    value = values.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def _mapping_sequence(values: dict[str, object], key: str) -> tuple[dict[str, object], ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of objects")

    items = tuple(value)
    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"{key} must contain only objects")
    return items


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


def _optional_int(values: dict[str, object], key: str) -> int | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _string_tuple(
    values: dict[str, object],
    key: str,
    *,
    default: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    value = values.get(key, default)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of strings")

    items = tuple(value)
    if not all(isinstance(item, str) and item for item in items):
        raise ValueError(f"{key} must contain only non-empty strings")
    return items


if __name__ == "__main__":
    raise SystemExit(main())
