"""Free-play event prediction probabilities for eventing fields."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from statistics import pstdev

from .results import EventingResult, consolidate_results


@dataclass(frozen=True)
class FieldEntry:
    """A declared horse and rider entry in an upcoming class."""

    rider_name: str
    horse_name: str


@dataclass(frozen=True)
class ProbabilityPriors:
    """Conservative priors used until result feeds include non-completion status."""

    elimination_probability: float = 0.02
    retirement_probability: float = 0.01
    withdrawal_probability: float = 0.01

    @property
    def completion_probability(self) -> float:
        return max(
            0.0,
            1
            - self.elimination_probability
            - self.retirement_probability
            - self.withdrawal_probability,
        )


@dataclass(frozen=True)
class EntryPhaseModel:
    """Expected phase performance for one horse and rider combination."""

    rider_name: str
    horse_name: str
    expected_dressage_score: float
    expected_show_jumping_penalties: float
    expected_cross_country_jump_penalties: float
    expected_cross_country_time_penalties: float
    clear_show_jumping_probability: float
    clear_cross_country_probability: float
    elimination_probability: float
    retirement_probability: float
    withdrawal_probability: float
    expected_finishing_score: float
    recent_result_count: int
    confidence: str


@dataclass(frozen=True)
class MarketProbability:
    """Free-play prediction market probabilities for one field entry."""

    rider_name: str
    horse_name: str
    expected_finishing_score: float
    win_probability: float
    top_3_probability: float
    top_10_probability: float
    best_dressage_probability: float
    clear_show_jumping_probability: float
    clear_cross_country_probability: float
    confidence: str


@dataclass(frozen=True)
class _SimulationModel:
    phase_model: EntryPhaseModel
    dressage_spread: float
    show_jumping_spread: float
    cross_country_jump_spread: float
    cross_country_time_spread: float


def estimate_phase_model(
    results: list[EventingResult],
    rider_name: str,
    horse_name: str,
    *,
    recent_result_limit: int = 8,
    priors: ProbabilityPriors | None = None,
) -> EntryPhaseModel:
    """Estimate expected phase scores from recent consolidated starts."""

    model = _build_simulation_model(
        results,
        FieldEntry(rider_name=rider_name, horse_name=horse_name),
        recent_result_limit=recent_result_limit,
        priors=priors or ProbabilityPriors(),
    )
    return model.phase_model


def simulate_market_probabilities(
    results: list[EventingResult],
    entries: list[FieldEntry],
    *,
    iterations: int = 5000,
    seed: int | None = None,
    recent_result_limit: int = 8,
    priors: ProbabilityPriors | None = None,
) -> list[MarketProbability]:
    """Run a Monte Carlo simulation for free-play market probabilities."""

    if iterations <= 0:
        raise ValueError("iterations must be greater than zero")
    if not entries:
        return []

    active_priors = priors or ProbabilityPriors()
    simulation_models = [
        _build_simulation_model(
            results,
            entry,
            recent_result_limit=recent_result_limit,
            priors=active_priors,
        )
        for entry in entries
    ]

    rng = random.Random(seed)
    counts = {
        entry_index: {
            "win": 0,
            "top_3": 0,
            "top_10": 0,
            "best_dressage": 0,
            "clear_show_jumping": 0,
            "clear_cross_country": 0,
        }
        for entry_index in range(len(simulation_models))
    }

    for _ in range(iterations):
        simulated = [
            _simulate_entry(model, rng)
            for model in simulation_models
        ]
        ranked = sorted(
            (
                (entry_index, performance[0])
                for entry_index, performance in enumerate(simulated)
                if performance[0] != float("inf")
            ),
            key=lambda item: item[1],
        )

        if ranked:
            counts[ranked[0][0]]["win"] += 1
        for rank, (entry_index, _score) in enumerate(ranked, start=1):
            if rank <= 3:
                counts[entry_index]["top_3"] += 1
            if rank <= 10:
                counts[entry_index]["top_10"] += 1

        best_dressage = min(
            (
                (entry_index, performance[1])
                for entry_index, performance in enumerate(simulated)
                if performance[1] != float("inf")
            ),
            key=lambda item: item[1],
            default=None,
        )
        if best_dressage is not None:
            counts[best_dressage[0]]["best_dressage"] += 1

        for entry_index, (_score, _dressage, sj_clear, xc_clear) in enumerate(simulated):
            if sj_clear:
                counts[entry_index]["clear_show_jumping"] += 1
            if xc_clear:
                counts[entry_index]["clear_cross_country"] += 1

    return [
        MarketProbability(
            rider_name=model.phase_model.rider_name,
            horse_name=model.phase_model.horse_name,
            expected_finishing_score=model.phase_model.expected_finishing_score,
            win_probability=counts[index]["win"] / iterations,
            top_3_probability=counts[index]["top_3"] / iterations,
            top_10_probability=counts[index]["top_10"] / iterations,
            best_dressage_probability=counts[index]["best_dressage"] / iterations,
            clear_show_jumping_probability=counts[index]["clear_show_jumping"] / iterations,
            clear_cross_country_probability=counts[index]["clear_cross_country"] / iterations,
            confidence=model.phase_model.confidence,
        )
        for index, model in enumerate(simulation_models)
    ]


def _build_simulation_model(
    results: list[EventingResult],
    entry: FieldEntry,
    *,
    recent_result_limit: int,
    priors: ProbabilityPriors,
) -> _SimulationModel:
    recent_results = _recent_results(results, entry, recent_result_limit)
    if not recent_results:
        raise ValueError(f"No results found for {entry.horse_name} and {entry.rider_name}")

    dressage_scores = [result.dressage_score for result in recent_results]
    show_jumping_scores = [result.show_jumping_penalties for result in recent_results]
    cross_country_jump_scores = [
        result.cross_country_jump_penalties
        for result in recent_results
    ]
    cross_country_time_scores = [
        result.cross_country_time_penalties
        for result in recent_results
    ]
    expected_dressage = _weighted_average(dressage_scores)
    expected_show_jumping = _weighted_average(show_jumping_scores)
    expected_cross_country_jump = _weighted_average(cross_country_jump_scores)
    expected_cross_country_time = _weighted_average(cross_country_time_scores)

    phase_model = EntryPhaseModel(
        rider_name=recent_results[0].rider_name,
        horse_name=recent_results[0].horse_name,
        expected_dressage_score=round(expected_dressage, 1),
        expected_show_jumping_penalties=round(expected_show_jumping, 1),
        expected_cross_country_jump_penalties=round(expected_cross_country_jump, 1),
        expected_cross_country_time_penalties=round(expected_cross_country_time, 1),
        clear_show_jumping_probability=_weighted_clear_probability(show_jumping_scores),
        clear_cross_country_probability=_weighted_clear_probability(cross_country_jump_scores),
        elimination_probability=priors.elimination_probability,
        retirement_probability=priors.retirement_probability,
        withdrawal_probability=priors.withdrawal_probability,
        expected_finishing_score=round(
            expected_dressage
            + expected_show_jumping
            + expected_cross_country_jump
            + expected_cross_country_time,
            1,
        ),
        recent_result_count=len(recent_results),
        confidence=_confidence(len(recent_results)),
    )
    return _SimulationModel(
        phase_model=phase_model,
        dressage_spread=_spread(dressage_scores, floor=1.5, fallback=3.0),
        show_jumping_spread=_spread(show_jumping_scores, floor=1.0, fallback=4.0),
        cross_country_jump_spread=_spread(cross_country_jump_scores, floor=2.0, fallback=8.0),
        cross_country_time_spread=_spread(cross_country_time_scores, floor=1.5, fallback=4.0),
    )


def _recent_results(
    results: list[EventingResult],
    entry: FieldEntry,
    limit: int,
) -> list[EventingResult]:
    target_key = _combination_key(entry.rider_name, entry.horse_name)
    return sorted(
        [
            result
            for result in consolidate_results(results)
            if result.combination_key == target_key
        ],
        key=lambda result: result.event_date,
        reverse=True,
    )[:limit]


def _simulate_entry(
    model: _SimulationModel,
    rng: random.Random,
) -> tuple[float, float, bool, bool]:
    phase_model = model.phase_model
    non_completion_probability = (
        phase_model.elimination_probability
        + phase_model.retirement_probability
        + phase_model.withdrawal_probability
    )
    if rng.random() < non_completion_probability:
        return (float("inf"), float("inf"), False, False)

    dressage = max(
        0.0,
        rng.gauss(phase_model.expected_dressage_score, model.dressage_spread),
    )
    show_jumping = _sample_penalties(
        phase_model.expected_show_jumping_penalties,
        phase_model.clear_show_jumping_probability,
        model.show_jumping_spread,
        rng,
        minimum_non_clear=4.0,
    )
    cross_country_jump = _sample_penalties(
        phase_model.expected_cross_country_jump_penalties,
        phase_model.clear_cross_country_probability,
        model.cross_country_jump_spread,
        rng,
        minimum_non_clear=20.0,
    )
    cross_country_time = max(
        0.0,
        rng.gauss(
            phase_model.expected_cross_country_time_penalties,
            model.cross_country_time_spread,
        ),
    )
    return (
        dressage + show_jumping + cross_country_jump + cross_country_time,
        dressage,
        show_jumping == 0,
        cross_country_jump == 0,
    )


def _sample_penalties(
    expected_penalties: float,
    clear_probability: float,
    spread: float,
    rng: random.Random,
    *,
    minimum_non_clear: float,
) -> float:
    if rng.random() < clear_probability:
        return 0.0
    non_clear_probability = max(1 - clear_probability, 0.01)
    non_clear_mean = max(minimum_non_clear, expected_penalties / non_clear_probability)
    return max(minimum_non_clear, rng.gauss(non_clear_mean, spread))


def _weighted_average(values: list[float]) -> float:
    weight_total = 0
    value_total = 0.0
    for weight, value in zip(range(len(values), 0, -1), values):
        value_total += value * weight
        weight_total += weight
    return value_total / weight_total


def _weighted_clear_probability(values: list[float]) -> float:
    return round(_weighted_average([1.0 if value == 0 else 0.0 for value in values]), 3)


def _combination_key(rider_name: str, horse_name: str) -> str:
    return f"{_slug(rider_name)}::{_slug(horse_name)}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _spread(values: list[float], *, floor: float, fallback: float) -> float:
    if len(values) < 2:
        return fallback
    return max(floor, pstdev(values))


def _confidence(result_count: int) -> str:
    if result_count >= 5:
        return "high"
    if result_count >= 3:
        return "medium"
    return "low"
