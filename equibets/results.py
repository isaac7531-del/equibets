"""Result records, consolidation, and finishing-score prediction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
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


@dataclass(frozen=True)
class LiveScoreEntry:
    """Ranked score for one combination inside an event competition."""

    competition_rank: int
    rider_name: str
    horse_name: str
    event_name: str
    event_date: date
    level: str
    country: str
    finishing_score: float
    dressage_score: float
    show_jumping_penalties: float
    cross_country_jump_penalties: float
    cross_country_time_penalties: float
    source_id: str
    source_record_id: str
    collected_at: datetime


def load_results(path: Path | str) -> list[EventingResult]:
    """Load eventing results from JSON."""

    with Path(path).open(encoding="utf-8") as results_file:
        payload = json.load(results_file)

    return [EventingResult.from_mapping(item) for item in payload["results"]]


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


def rank_live_scores(
    results: list[EventingResult],
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[LiveScoreEntry]:
    """Return ranked, consolidated scores for active/current event windows."""

    competitions: dict[tuple[str, date, str, str], list[EventingResult]] = {}
    for result in consolidate_results(results):
        if start_date is not None and result.event_date < start_date:
            continue
        if end_date is not None and result.event_date > end_date:
            continue
        competition_key = (
            result.event_name,
            result.event_date,
            result.level,
            result.country,
        )
        competitions.setdefault(competition_key, []).append(result)

    entries: list[LiveScoreEntry] = []
    for competition_results in competitions.values():
        ranked_results = sorted(competition_results, key=_live_score_sort_key)
        previous_score: float | None = None
        previous_rank = 0
        for index, result in enumerate(ranked_results, start=1):
            if previous_score is None or result.finishing_score != previous_score:
                previous_rank = index
                previous_score = result.finishing_score
            entries.append(
                LiveScoreEntry(
                    competition_rank=previous_rank,
                    rider_name=result.rider_name,
                    horse_name=result.horse_name,
                    event_name=result.event_name,
                    event_date=result.event_date,
                    level=result.level,
                    country=result.country,
                    finishing_score=result.finishing_score,
                    dressage_score=result.dressage_score,
                    show_jumping_penalties=result.show_jumping_penalties,
                    cross_country_jump_penalties=result.cross_country_jump_penalties,
                    cross_country_time_penalties=result.cross_country_time_penalties,
                    source_id=result.source_id,
                    source_record_id=result.source_record_id,
                    collected_at=result.collected_at,
                )
            )

    return sorted(
        entries,
        key=lambda entry: (
            -entry.event_date.toordinal(),
            entry.event_name,
            entry.level,
            entry.competition_rank,
            entry.finishing_score,
            entry.cross_country_jump_penalties + entry.cross_country_time_penalties,
            entry.dressage_score,
            entry.rider_name,
            entry.horse_name,
        ),
    )


def live_score_to_mapping(score: LiveScoreEntry) -> dict[str, object]:
    """Convert a ranked live score entry to JSON-serializable values."""

    return {
        "competition_rank": score.competition_rank,
        "rider_name": score.rider_name,
        "horse_name": score.horse_name,
        "event_name": score.event_name,
        "event_date": score.event_date.isoformat(),
        "level": score.level,
        "country": score.country,
        "finishing_score": score.finishing_score,
        "dressage_score": score.dressage_score,
        "show_jumping_penalties": score.show_jumping_penalties,
        "cross_country_jump_penalties": score.cross_country_jump_penalties,
        "cross_country_time_penalties": score.cross_country_time_penalties,
        "source_id": score.source_id,
        "source_record_id": score.source_record_id,
        "collected_at": score.collected_at.isoformat(),
    }


def _is_better_result(candidate: EventingResult, existing: EventingResult) -> bool:
    if candidate.source_priority != existing.source_priority:
        return candidate.source_priority < existing.source_priority
    if candidate.is_user_entered != existing.is_user_entered:
        return not candidate.is_user_entered
    return candidate.collected_at > existing.collected_at


def _live_score_sort_key(result: EventingResult) -> tuple[float, float, float, str, str]:
    return (
        result.finishing_score,
        result.cross_country_jump_penalties + result.cross_country_time_penalties,
        result.dressage_score,
        result.rider_name,
        result.horse_name,
    )


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
