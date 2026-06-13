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
class CoverageTargets:
    """Reusable country and event-level targets referenced by source records."""

    primary_source_id: str
    coverage_goal: str
    priority_regions: tuple[str, ...]
    country_groups: dict[str, tuple[str, ...]]
    event_level_groups: dict[str, tuple[str, ...]]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CoverageTargets":
        coverage_targets = values.get("coverage_targets", {})
        if not isinstance(coverage_targets, dict):
            raise ValueError("coverage_targets must be an object")

        return cls(
            primary_source_id=_required_str(values, "primary_source_id"),
            coverage_goal=_required_str(values, "coverage_goal"),
            priority_regions=tuple(
                _normalize_token(region)
                for region in _string_tuple(values, "priority_regions")
            ),
            country_groups=_string_tuple_dict(coverage_targets, "country_groups"),
            event_level_groups=_normalized_string_tuple_dict(
                coverage_targets,
                "event_level_groups",
            ),
        )

    def expand_countries(self, targets: Iterable[str]) -> tuple[str, ...]:
        """Expand country group names into ISO-3 country codes."""

        return _dedupe_preserve_order(
            self._expand_targets(
                targets,
                self.country_groups,
                target_type="country",
                normalize=_normalize_country,
            )
        )

    def expand_event_levels(self, targets: Iterable[str]) -> tuple[str, ...]:
        """Expand event-level group names into normalized level identifiers."""

        return _dedupe_preserve_order(
            self._expand_targets(
                targets,
                self.event_level_groups,
                target_type="event level",
                normalize=_normalize_token,
            )
        )

    def _expand_targets(
        self,
        targets: Iterable[str],
        groups: dict[str, tuple[str, ...]],
        *,
        target_type: str,
        normalize,
        stack: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        expanded: list[str] = []
        for target in targets:
            normalized_target = _normalize_token(target)
            if normalized_target in groups:
                if normalized_target in stack:
                    cycle = " -> ".join((*stack, normalized_target))
                    raise ValueError(f"{target_type} target cycle detected: {cycle}")
                expanded.extend(
                    self._expand_targets(
                        groups[normalized_target],
                        groups,
                        target_type=target_type,
                        normalize=normalize,
                        stack=(*stack, normalized_target),
                    )
                )
            else:
                expanded.append(normalize(target))

        return tuple(expanded)


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
    def from_mapping(
        cls,
        values: dict[str, object],
        coverage_targets: CoverageTargets | None = None,
    ) -> "EventSource":
        country_targets = _string_tuple(values, "countries")
        event_level_targets = _string_tuple(values, "event_levels")

        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            priority=_required_int(values, "priority"),
            scope=_required_str(values, "scope"),
            regions=tuple(
                _normalize_token(region) for region in _string_tuple(values, "regions")
            ),
            countries=(
                coverage_targets.expand_countries(country_targets)
                if coverage_targets
                else country_targets
            ),
            disciplines=_string_tuple(values, "disciplines"),
            event_levels=(
                coverage_targets.expand_event_levels(event_level_targets)
                if coverage_targets
                else tuple(_normalize_token(level) for level in event_level_targets)
            ),
            source_type=_required_str(values, "source_type"),
            base_url=_optional_str(values, "base_url"),
            status=_required_str(values, "status"),
            notes=_required_str(values, "notes"),
        )


@dataclass(frozen=True)
class EventSourceRegistry:
    """Expanded event-results source registry with coverage metadata."""

    coverage_targets: CoverageTargets
    sources: tuple[EventSource, ...]

    def sources_for_region(
        self,
        region: str,
        *,
        include_planned: bool = True,
        level: str | None = None,
    ) -> list[EventSource]:
        """Return sources covering a region while preserving global priorities."""

        normalized_region = _normalize_token(region)
        return [
            source
            for source in self._matching_sources(include_planned, level)
            if "global" in source.regions or normalized_region in source.regions
        ]

    def sources_for_country(
        self,
        country: str,
        *,
        include_planned: bool = True,
        level: str | None = None,
    ) -> list[EventSource]:
        """Return sources covering an ISO-3 country code."""

        normalized_country = _normalize_country(country)
        return [
            source
            for source in self._matching_sources(include_planned, level)
            if normalized_country in source.countries
        ]

    def sources_for_event_level(
        self,
        level: str,
        *,
        include_planned: bool = True,
    ) -> list[EventSource]:
        """Return sources that can provide results for an event level."""

        normalized_level = _normalize_token(level)
        statuses = _included_statuses(include_planned)
        return [
            source
            for source in self.sources
            if source.status in statuses and normalized_level in source.event_levels
        ]

    def _matching_sources(
        self,
        include_planned: bool,
        level: str | None,
    ) -> tuple[EventSource, ...]:
        statuses = _included_statuses(include_planned)
        normalized_level = _normalize_token(level) if level else None
        return tuple(
            source
            for source in self.sources
            if source.status in statuses
            and (
                normalized_level is None
                or normalized_level in source.event_levels
            )
        )


def load_event_source_registry(
    path: Path | str = DATA_FILE,
) -> EventSourceRegistry:
    """Load and expand the source registry, preserving source priority order."""

    with Path(path).open(encoding="utf-8") as source_file:
        payload = json.load(source_file)

    coverage_targets = CoverageTargets.from_mapping(payload)
    sources = [
        EventSource.from_mapping(item, coverage_targets)
        for item in payload["sources"]
    ]
    return EventSourceRegistry(
        coverage_targets=coverage_targets,
        sources=tuple(_sort_sources(sources)),
    )


def load_event_sources(path: Path | str = DATA_FILE) -> list[EventSource]:
    """Load sources sorted by priority, with FEI first on ties."""

    return list(load_event_source_registry(path).sources)


def sources_for_region(
    region: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering a region while preserving global priorities."""

    return load_event_source_registry(path).sources_for_region(
        region,
        include_planned=include_planned,
        level=level,
    )


def sources_for_country(
    country: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
    level: str | None = None,
) -> list[EventSource]:
    """Return sources covering an ISO-3 country code."""

    return load_event_source_registry(path).sources_for_country(
        country,
        include_planned=include_planned,
        level=level,
    )


def sources_for_event_level(
    level: str,
    *,
    path: Path | str = DATA_FILE,
    include_planned: bool = True,
) -> list[EventSource]:
    """Return sources that can provide results for an event level."""

    return load_event_source_registry(path).sources_for_event_level(
        level,
        include_planned=include_planned,
    )


def _sort_sources(sources: Iterable[EventSource]) -> list[EventSource]:
    return sorted(
        sources,
        key=lambda source: (source.priority, source.id != "data_fei", source.id),
    )


def _included_statuses(include_planned: bool) -> set[str]:
    return {"active", "planned"} if include_planned else {"active"}


def _dedupe_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _normalize_token(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _normalize_country(value: str) -> str:
    normalized = value.strip().upper()
    if len(normalized) != 3 or not normalized.isalpha():
        raise ValueError(f"country code must be a three-letter ISO code: {value}")
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


def _string_tuple_dict(
    values: dict[str, object],
    key: str,
) -> dict[str, tuple[str, ...]]:
    value = values.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")

    return {
        _normalize_token(group_name): _string_tuple(value, group_name)
        for group_name in value
    }


def _normalized_string_tuple_dict(
    values: dict[str, object],
    key: str,
) -> dict[str, tuple[str, ...]]:
    groups = _string_tuple_dict(values, key)
    return {
        group_name: tuple(_normalize_token(item) for item in items)
        for group_name, items in groups.items()
    }
