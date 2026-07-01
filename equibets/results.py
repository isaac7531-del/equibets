"""Result records, consolidation, and transparent finishing-score prediction."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from statistics import mean, pstdev


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
    rider_fei_id: str = ""
    horse_fei_id: str = ""
    combination_id: str = ""
    placing: str = ""
    show_jumping_time_penalties: float = 0.0
    total_score: float | None = None
    status: str = "completed"
    mer_status: str = ""
    event_url: str = ""
    source_url: str = ""
    venue: str = ""

    @property
    def finishing_score(self) -> float:
        """Lower scores are better in eventing."""

        if self.total_score is not None:
            return round(self.total_score, 1)
        return round(
            self.dressage_score
            + self.show_jumping_penalties
            + self.show_jumping_time_penalties
            + self.cross_country_jump_penalties
            + self.cross_country_time_penalties,
            1,
        )

    @property
    def is_completed(self) -> bool:
        return _completion_status(self.status, self.placing) == "completed"

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
            rider_fei_id=_optional_str(values, "rider_fei_id"),
            horse_fei_id=_optional_str(values, "horse_fei_id"),
            combination_id=_optional_str(values, "combination_id"),
            placing=_optional_str(values, "placing"),
            show_jumping_time_penalties=_optional_number(values, "show_jumping_time_penalties", 0.0),
            total_score=_nullable_number(values, "total_score"),
            status=_optional_str(values, "status", "completed"),
            mer_status=_optional_str(values, "mer_status"),
            event_url=_optional_str(values, "event_url"),
            source_url=_optional_str(values, "source_url"),
            venue=_optional_str(values, "venue"),
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
    predicted_low_score: float = 0.0
    predicted_high_score: float = 0.0


@dataclass(frozen=True)
class PredictionEvidence:
    """Transparent inputs behind a score-range prediction."""

    rider_name: str
    horse_name: str
    target_level: str
    predicted_dressage_score: float
    predicted_xc_jump_penalties: float
    predicted_xc_time_penalties: float
    predicted_show_jumping_penalties: float
    predicted_show_jumping_time_penalties: float
    predicted_final_score_low: float
    predicted_final_score_high: float
    average_dressage_current_level: float | None
    average_dressage_one_level_below: float | None
    average_final_score: float | None
    xc_clear_jumping_rate: float
    xc_time_penalty_average: float
    sj_rail_average: float
    completion_rate: float
    elimination_retirement_rate: float
    best_score: float | None
    worst_score: float | None
    recent_3_run_average: float | None
    recent_5_run_average: float | None
    trend_direction: str
    level_reliability: str
    country_pattern: str
    venue_pattern: str
    same_level_result_count: int
    horse_result_count: int
    combination_result_count: int


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
    evidence = build_prediction_evidence(
        results,
        recent_results[0].rider_name,
        recent_results[0].horse_name,
        target_level=recent_results[0].level,
    )
    return CombinationPrediction(
        rider_name=recent_results[0].rider_name,
        horse_name=recent_results[0].horse_name,
        likely_finishing_score=round(weighted_score_total / weight_total, 1),
        recent_result_count=len(recent_results),
        best_recent_score=min(scores),
        worst_recent_score=max(scores),
        source_ids=tuple(sorted({result.source_id for result in recent_results})),
        confidence=_confidence(len(recent_results)),
        predicted_low_score=evidence.predicted_final_score_low,
        predicted_high_score=evidence.predicted_final_score_high,
    )


def build_prediction_evidence(
    results: list[EventingResult],
    rider_name: str,
    horse_name: str,
    *,
    target_level: str | None = None,
) -> PredictionEvidence:
    """Calculate prediction inputs for one horse/rider combination."""

    consolidated = sorted(consolidate_results(results), key=lambda result: result.event_date, reverse=True)
    horse_key = _slug(horse_name)
    combination_key = f"{_slug(rider_name)}::{horse_key}"
    horse_results = [result for result in consolidated if _slug(result.horse_name) == horse_key]
    combination_results = [result for result in horse_results if result.combination_key == combination_key]
    if not combination_results and not horse_results:
        raise ValueError("No results found for horse or combination")

    evidence_results = combination_results or horse_results
    selected_level = target_level or evidence_results[0].level
    completed = [result for result in evidence_results if result.is_completed]
    same_level = [result for result in completed if _same_level(result.level, selected_level)]
    one_below = [result for result in completed if _level_rank(result.level) == _level_rank(selected_level) - 1]
    score_values = [result.finishing_score for result in completed]

    predicted_dressage = _weighted_phase_average(evidence_results, selected_level, "dressage_score")
    predicted_xc_jump = _weighted_phase_average(evidence_results, selected_level, "cross_country_jump_penalties")
    predicted_xc_time = _weighted_phase_average(evidence_results, selected_level, "cross_country_time_penalties")
    predicted_sj_jump = _weighted_phase_average(evidence_results, selected_level, "show_jumping_penalties")
    predicted_sj_time = _weighted_phase_average(evidence_results, selected_level, "show_jumping_time_penalties")
    predicted_total = predicted_dressage + predicted_xc_jump + predicted_xc_time + predicted_sj_jump + predicted_sj_time

    completion_rate = _rate(len(completed), len(evidence_results))
    el_ret_rate = _rate(
        sum(1 for result in evidence_results if _completion_status(result.status, result.placing) in {"eliminated", "retired", "withdrawn"}),
        len(evidence_results),
    )
    uncertainty = max(2.5, (pstdev(score_values) if len(score_values) > 1 else 3.0) + el_ret_rate * 8.0)

    return PredictionEvidence(
        rider_name=evidence_results[0].rider_name,
        horse_name=evidence_results[0].horse_name,
        target_level=selected_level,
        predicted_dressage_score=round(predicted_dressage, 1),
        predicted_xc_jump_penalties=round(predicted_xc_jump, 1),
        predicted_xc_time_penalties=round(predicted_xc_time, 1),
        predicted_show_jumping_penalties=round(predicted_sj_jump, 1),
        predicted_show_jumping_time_penalties=round(predicted_sj_time, 1),
        predicted_final_score_low=round(max(0.0, predicted_total - uncertainty), 1),
        predicted_final_score_high=round(predicted_total + uncertainty, 1),
        average_dressage_current_level=_average([result.dressage_score for result in same_level]),
        average_dressage_one_level_below=_average([result.dressage_score for result in one_below]),
        average_final_score=_average(score_values),
        xc_clear_jumping_rate=_rate(sum(1 for result in completed if result.cross_country_jump_penalties == 0), len(completed)),
        xc_time_penalty_average=_average([result.cross_country_time_penalties for result in completed]) or 0.0,
        sj_rail_average=round((_average([result.show_jumping_penalties for result in completed]) or 0.0) / 4.0, 2),
        completion_rate=completion_rate,
        elimination_retirement_rate=el_ret_rate,
        best_score=min(score_values) if score_values else None,
        worst_score=max(score_values) if score_values else None,
        recent_3_run_average=_average(score_values[:3]),
        recent_5_run_average=_average(score_values[:5]),
        trend_direction=_trend(score_values),
        level_reliability=_level_reliability(same_level, one_below, completion_rate, el_ret_rate),
        country_pattern=_pattern(evidence_results, "country"),
        venue_pattern=_pattern(evidence_results, "venue"),
        same_level_result_count=len(same_level),
        horse_result_count=len(horse_results),
        combination_result_count=len(combination_results),
    )


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


def _weighted_phase_average(results: list[EventingResult], target_level: str, field_name: str) -> float:
    values: list[tuple[float, float]] = []
    ordered = sorted(results, key=lambda result: result.event_date, reverse=True)
    for index, result in enumerate(ordered):
        if not result.is_completed:
            continue
        value = getattr(result, field_name)
        recency_weight = max(1.0, len(ordered) - index)
        level_weight = 1.5 if _same_level(result.level, target_level) else 0.85
        if _level_rank(result.level) > _level_rank(target_level):
            level_weight = 1.2
        values.append((float(value), recency_weight * level_weight))
    if not values:
        return 0.0
    return sum(value * weight for value, weight in values) / sum(weight for _, weight in values)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(mean(values), 1)


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(count / total, 2)


def _trend(scores_descending: list[float]) -> str:
    if len(scores_descending) < 4:
        return "flat"
    newer = mean(scores_descending[: max(2, len(scores_descending) // 2)])
    older = mean(scores_descending[max(2, len(scores_descending) // 2) :])
    if newer <= older - 1.0:
        return "improving"
    if newer >= older + 1.0:
        return "declining"
    return "flat"


def _level_reliability(
    same_level_results: list[EventingResult],
    one_below_results: list[EventingResult],
    completion_rate: float,
    el_ret_rate: float,
) -> str:
    if len(same_level_results) >= 3 and completion_rate >= 0.75 and el_ret_rate <= 0.2:
        return "proven"
    if len(same_level_results) == 0 and len(one_below_results) >= 2:
        return "stepping up"
    if completion_rate < 0.7 or el_ret_rate > 0.25:
        return "inconsistent"
    return "developing"


def _pattern(results: list[EventingResult], field_name: str) -> str:
    buckets: dict[str, list[float]] = defaultdict(list)
    for result in results:
        if result.is_completed:
            key = getattr(result, field_name) or "Unknown"
            buckets[key].append(result.finishing_score)
    candidates = {key: values for key, values in buckets.items() if len(values) >= 3}
    if not candidates:
        return "not enough data"
    best_key, best_scores = min(candidates.items(), key=lambda item: mean(item[1]))
    return f"best at {best_key} ({round(mean(best_scores), 1)} avg)"


def _same_level(left: str, right: str) -> bool:
    return _level_rank(left) == _level_rank(right) and _level_rank(left) > 0 or _slug(left) == _slug(right)


def _level_rank(level: str) -> int:
    normalized = level.upper().replace("CCI", "CCI")
    match = re.search(r"CCI\s*(\d)", normalized)
    if match:
        return int(match.group(1))
    if "ADVANCED" in normalized:
        return 4
    if "INTERMEDIATE" in normalized:
        return 3
    if "PRELIM" in normalized:
        return 2
    if any(token in normalized for token in ("TRAINING", "NOVICE", "CCN1")):
        return 1
    return 0


def _completion_status(status: str, placing: str = "") -> str:
    text = f"{status} {placing}".lower()
    tokens = set(re.findall(r"[a-z]+", text))
    if tokens & {"el", "elim", "eliminated"}:
        return "eliminated"
    if tokens & {"ret", "retired"}:
        return "retired"
    if tokens & {"wd", "withdrawn"}:
        return "withdrawn"
    return "completed"


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


def _optional_str(values: dict[str, object], key: str, default: str = "") -> str:
    value = values.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _optional_number(values: dict[str, object], key: str, default: float) -> float:
    value = values.get(key, default)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _nullable_number(values: dict[str, object], key: str) -> float | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number or null")
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
