"""Result records, consolidation, and finishing-score prediction."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


USER_ENTERED_PRIORITY = 100


@dataclass(frozen=True)
class EventingResult:
    """One eventing result for a horse and rider combination."""

    source_id: str
    source_record_id: str
    source_priority: int
    rider_name: str
    horse_name: str
    event_name: str
    event_date: date
    level: str
    country: str
    dressage_score: float
    show_jumping_penalties: float
    cross_country_jump_penalties: float
    cross_country_time_penalties: float
    collected_at: datetime
    is_user_entered: bool = False

    @property
    def finishing_score(self) -> float:
        """Lower scores are better in eventing."""

        return round(
            self.dressage_score
            + self.show_jumping_penalties
            + self.cross_country_jump_penalties
            + self.cross_country_time_penalties,
            1,
        )

    @property
    def combination_key(self) -> str:
        return f"{_slug(self.rider_name)}::{_slug(self.horse_name)}"

    @property
    def result_key(self) -> tuple[str, str, date, str]:
        return (
            self.combination_key,
            _slug(self.event_name),
            self.event_date,
            _slug(self.level),
        )

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "EventingResult":
        is_user_entered = _optional_bool(values, "is_user_entered", False)
        return cls(
            source_id=_required_str(values, "source_id"),
            source_record_id=_required_str(values, "source_record_id"),
            source_priority=_optional_int(
                values,
                "source_priority",
                USER_ENTERED_PRIORITY if is_user_entered else 50,
            ),
            rider_name=_required_str(values, "rider_name"),
            horse_name=_required_str(values, "horse_name"),
            event_name=_required_str(values, "event_name"),
            event_date=date.fromisoformat(_required_str(values, "event_date")),
            level=_required_str(values, "level"),
            country=_required_str(values, "country"),
            dressage_score=_required_number(values, "dressage_score"),
            show_jumping_penalties=_required_number(values, "show_jumping_penalties"),
            cross_country_jump_penalties=_required_number(
                values,
                "cross_country_jump_penalties",
            ),
            cross_country_time_penalties=_required_number(
                values,
                "cross_country_time_penalties",
            ),
            collected_at=datetime.fromisoformat(_required_str(values, "collected_at")),
            is_user_entered=is_user_entered,
        )


@dataclass(frozen=True)
class CombinationPrediction:
    """Likely upcoming finishing score for a combination."""

    rider_name: str
    horse_name: str
    likely_finishing_score: float
    recent_result_count: int
    best_recent_score: float
    worst_recent_score: float
    source_ids: tuple[str, ...]
    confidence: str


def load_results(path: Path | str) -> list[EventingResult]:
    """Load eventing results from JSON."""

    with Path(path).open(encoding="utf-8") as results_file:
        payload = json.load(results_file)

    return [EventingResult.from_mapping(item) for item in payload.get("results", [])]


class ResultStore:
    """Persist normalized eventing results in the project's JSON format."""

    def __init__(self, path: Path | str, *, source_id: str | None = None) -> None:
        self.path = Path(path)
        self.source_id = source_id

    def load(self) -> list[EventingResult]:
        if not self.path.exists():
            return []
        return load_results(self.path)

    def merge(self, new_results: Iterable[EventingResult]) -> list[EventingResult]:
        return consolidate_results([*self.load(), *new_results])

    def save(self, results: Sequence[EventingResult]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "results": [result_to_mapping(result) for result in results],
        }
        if self.source_id is not None:
            payload["source_id"] = self.source_id
        with self.path.open("w", encoding="utf-8") as results_file:
            json.dump(payload, results_file, indent=2, sort_keys=True)
            results_file.write("\n")


def consolidate_results(results: list[EventingResult]) -> list[EventingResult]:
    """Deduplicate results, keeping the highest-priority source for each start."""

    selected: dict[tuple[str, str, date, str], EventingResult] = {}
    for result in results:
        existing = selected.get(result.result_key)
        if existing is None or _is_better_result(result, existing):
            selected[result.result_key] = result

    return sorted(
        selected.values(),
        key=lambda result: (result.event_date, result.rider_name, result.horse_name),
    )


def predict_finishing_score(
    results: list[EventingResult],
    rider_name: str,
    horse_name: str,
    *,
    recent_result_limit: int = 5,
) -> CombinationPrediction:
    """Estimate likely finishing score from recent consolidated starts."""

    combination_key = f"{_slug(rider_name)}::{_slug(horse_name)}"
    recent_results = [
        result
        for result in consolidate_results(results)
        if result.combination_key == combination_key
    ]
    recent_results = sorted(
        recent_results,
        key=lambda result: result.event_date,
        reverse=True,
    )[:recent_result_limit]

    if not recent_results:
        raise ValueError("No results found for combination")

    weighted_score_total = 0.0
    weight_total = 0
    for weight, result in zip(range(len(recent_results), 0, -1), recent_results):
        weighted_score_total += result.finishing_score * weight
        weight_total += weight

    scores = [result.finishing_score for result in recent_results]
    return CombinationPrediction(
        rider_name=recent_results[0].rider_name,
        horse_name=recent_results[0].horse_name,
        likely_finishing_score=round(weighted_score_total / weight_total, 1),
        recent_result_count=len(recent_results),
        best_recent_score=min(scores),
        worst_recent_score=max(scores),
        source_ids=tuple(sorted({result.source_id for result in recent_results})),
        confidence=_confidence(len(recent_results)),
    )


def result_to_mapping(result: EventingResult) -> dict[str, object]:
    """Convert an EventingResult to JSON-serializable values."""

    return {
        "source_id": result.source_id,
        "source_record_id": result.source_record_id,
        "source_priority": result.source_priority,
        "rider_name": result.rider_name,
        "horse_name": result.horse_name,
        "event_name": result.event_name,
        "event_date": result.event_date.isoformat(),
        "level": result.level,
        "country": result.country,
        "dressage_score": result.dressage_score,
        "show_jumping_penalties": result.show_jumping_penalties,
        "cross_country_jump_penalties": result.cross_country_jump_penalties,
        "cross_country_time_penalties": result.cross_country_time_penalties,
        "collected_at": result.collected_at.isoformat(),
        "is_user_entered": result.is_user_entered,
    }


def _is_better_result(candidate: EventingResult, existing: EventingResult) -> bool:
    if candidate.source_priority != existing.source_priority:
        return candidate.source_priority < existing.source_priority
    if candidate.is_user_entered != existing.is_user_entered:
        return not candidate.is_user_entered
    return candidate.collected_at > existing.collected_at


def _confidence(result_count: int) -> str:
    if result_count >= 5:
        return "high"
    if result_count >= 3:
        return "medium"
    return "low"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_number(values: dict[str, object], key: str) -> float:
    value = values.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _optional_int(values: dict[str, object], key: str, default: int) -> int:
    value = values.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _optional_bool(values: dict[str, object], key: str, default: bool) -> bool:
    value = values.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value
