"""Load, search, and score current-event result feeds."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from urllib.request import urlopen

from .results import EventingResult


DEFAULT_SOURCE_PRIORITY = 50


@dataclass(frozen=True)
class CurrentEventResult:
    """A result row from an in-progress event feed.

    Phase scores may be missing until that phase is published. Missing phase
    values count as zero for the live score but remain distinguishable via
    ``completed_phase_count`` and ``phase_status``.
    """

    id: str
    source_id: str
    source_record_id: str
    source_priority: int
    rider_name: str
    horse_name: str
    event_name: str
    event_date: date
    level: str
    country: str
    dressage_score: float | None
    show_jumping_penalties: float | None
    cross_country_jump_penalties: float | None
    cross_country_time_penalties: float | None
    phase_status: str
    collected_at: datetime

    @property
    def live_score(self) -> float:
        """Current penalty total from every published phase."""

        return round(
            _penalty_or_zero(self.dressage_score)
            + _penalty_or_zero(self.show_jumping_penalties)
            + _penalty_or_zero(self.cross_country_jump_penalties)
            + _penalty_or_zero(self.cross_country_time_penalties),
            1,
        )

    @property
    def completed_phase_count(self) -> int:
        return sum(
            value is not None
            for value in (
                self.dressage_score,
                self.show_jumping_penalties,
                self.cross_country_jump_penalties,
                self.cross_country_time_penalties,
            )
        )

    def to_eventing_result(self, *, require_final: bool = False) -> EventingResult:
        """Convert the live row to the common result model.

        ``require_final`` protects downstream consolidation jobs from treating
        in-progress scores as final official results unless explicitly allowed.
        """

        if require_final and self.completed_phase_count < 4:
            raise ValueError("Current event result is not final")

        return EventingResult(
            source_id=self.source_id,
            source_record_id=self.source_record_id,
            source_priority=self.source_priority,
            rider_name=self.rider_name,
            horse_name=self.horse_name,
            event_name=self.event_name,
            event_date=self.event_date,
            level=self.level,
            country=self.country,
            dressage_score=_penalty_or_zero(self.dressage_score),
            show_jumping_penalties=_penalty_or_zero(self.show_jumping_penalties),
            cross_country_jump_penalties=_penalty_or_zero(self.cross_country_jump_penalties),
            cross_country_time_penalties=_penalty_or_zero(self.cross_country_time_penalties),
            collected_at=self.collected_at,
        )

    @classmethod
    def from_mapping(
        cls,
        values: dict[str, object],
        *,
        default_collected_at: datetime | None = None,
    ) -> "CurrentEventResult":
        source_record_id = _required_str(values, "source_record_id")
        collected_at = _optional_datetime(values, "collected_at") or default_collected_at
        if collected_at is None:
            raise ValueError("collected_at must be provided by the row or feed")

        return cls(
            id=_optional_str(values, "id") or source_record_id,
            source_id=_required_str(values, "source_id"),
            source_record_id=source_record_id,
            source_priority=_optional_int(values, "source_priority", DEFAULT_SOURCE_PRIORITY),
            rider_name=_required_str(values, "rider_name"),
            horse_name=_required_str(values, "horse_name"),
            event_name=_required_str(values, "event_name"),
            event_date=date.fromisoformat(_required_str(values, "event_date")),
            level=_required_str(values, "level"),
            country=_required_str(values, "country"),
            dressage_score=_optional_number(values, "dressage_score"),
            show_jumping_penalties=_optional_number(values, "show_jumping_penalties"),
            cross_country_jump_penalties=_optional_number(values, "cross_country_jump_penalties"),
            cross_country_time_penalties=_optional_number(values, "cross_country_time_penalties"),
            phase_status=_optional_str(values, "phase_status") or "unknown",
            collected_at=collected_at,
        )


def load_current_event_results(location: Path | str) -> list[CurrentEventResult]:
    """Load current-event result rows from a local JSON file or HTTPS URL."""

    payload = json.loads(_read_json_text(location))
    return parse_current_event_payload(payload)


def parse_current_event_payload(payload: dict[str, object]) -> list[CurrentEventResult]:
    """Parse the current-event feed JSON shape used by the app."""

    feed_collected_at = _optional_datetime(payload, "collected_at")
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise ValueError("results must be a list")

    results: list[CurrentEventResult] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("results must contain objects")
        results.append(CurrentEventResult.from_mapping(row, default_collected_at=feed_collected_at))
    return results


def search_current_event_results(
    results: list[CurrentEventResult],
    query: str,
) -> list[CurrentEventResult]:
    """Search current results by combination, event, level, country, or source."""

    normalized_query = query.strip().lower()
    matches = (
        [
            result
            for result in results
            if normalized_query
            in " ".join(
                (
                    result.rider_name,
                    result.horse_name,
                    result.event_name,
                    result.level,
                    result.country,
                    result.source_id,
                )
            ).lower()
        ]
        if normalized_query
        else results
    )
    return live_leaderboard(matches)


def live_leaderboard(results: list[CurrentEventResult]) -> list[CurrentEventResult]:
    """Rank current-event rows by completeness, live score, and source priority."""

    return sorted(
        results,
        key=lambda result: (
            -result.completed_phase_count,
            result.live_score,
            result.source_priority,
            result.collected_at,
        ),
    )


def current_event_results_as_eventing_results(
    results: list[CurrentEventResult],
    *,
    require_final: bool = False,
) -> list[EventingResult]:
    """Normalize current-event rows into EventingResult records."""

    return [result.to_eventing_result(require_final=require_final) for result in results]


def _read_json_text(location: Path | str) -> str:
    location_text = str(location)
    if location_text.startswith(("http://", "https://")):
        with urlopen(location_text, timeout=30) as response:
            return response.read().decode("utf-8")

    return Path(location).read_text(encoding="utf-8")


def _penalty_or_zero(value: float | None) -> float:
    return 0.0 if value is None else value


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


def _optional_int(values: dict[str, object], key: str, default: int) -> int:
    value = values.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _optional_number(values: dict[str, object], key: str) -> float | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number or null")
    return float(value)


def _optional_datetime(values: dict[str, object], key: str) -> datetime | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be null or an ISO datetime string")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
