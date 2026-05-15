"""Build live eventing scoreboards from freshly collected result records."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from equibets.results import EventingResult, consolidate_results, load_results


DEFAULT_RESULTS_FILE = Path(__file__).resolve().parents[1] / "data" / "fei_results.json"
DEFAULT_LIVE_SCORING_FILE = Path(__file__).resolve().parents[1] / "data" / "live_scoring.json"


@dataclass(frozen=True)
class LiveScoreEntry:
    """One ranked combination on a live event scoreboard."""

    rank: int
    rider_name: str
    horse_name: str
    total_penalties: float
    dressage_score: float
    show_jumping_penalties: float
    cross_country_jump_penalties: float
    cross_country_time_penalties: float
    source_id: str
    source_record_id: str
    collected_at: datetime


@dataclass(frozen=True)
class LiveEventScoreboard:
    """Current scores for one event, level, country, and date."""

    event_key: str
    event_name: str
    event_date: date
    level: str
    country: str
    result_count: int
    last_collected_at: datetime
    leader: LiveScoreEntry
    scores: tuple[LiveScoreEntry, ...]


def load_result_files(paths: Sequence[Path | str]) -> list[EventingResult]:
    """Load and combine result records from one or more JSON stores."""

    results: list[EventingResult] = []
    for path in paths:
        result_path = Path(path)
        if not result_path.exists():
            continue
        results.extend(load_results(result_path))
    return results


def build_live_scoreboards(
    results: Iterable[EventingResult],
    *,
    as_of: date | None = None,
    lookback_days: int = 7,
    lookahead_days: int = 2,
    max_events: int | None = None,
) -> list[LiveEventScoreboard]:
    """Return current-event scoreboards ranked by lowest live penalty score."""

    if lookback_days < 0 or lookahead_days < 0:
        raise ValueError("lookback_days and lookahead_days must be non-negative")

    scoring_date = as_of or datetime.now(timezone.utc).date()
    oldest_event_date = scoring_date.toordinal() - lookback_days
    newest_event_date = scoring_date.toordinal() + lookahead_days
    current_results = [
        result
        for result in consolidate_results(list(results))
        if oldest_event_date <= result.event_date.toordinal() <= newest_event_date
    ]

    grouped: dict[tuple[str, date, str, str], list[EventingResult]] = defaultdict(list)
    for result in current_results:
        grouped[_event_key(result)].append(result)

    scoreboards = [
        _scoreboard_from_group(event_results)
        for event_results in grouped.values()
        if event_results
    ]
    scoreboards.sort(
        key=lambda scoreboard: (
            scoreboard.event_date,
            scoreboard.event_name.lower(),
            scoreboard.level.lower(),
            scoreboard.country.lower(),
        ),
        reverse=True,
    )
    if max_events is not None:
        return scoreboards[:max_events]
    return scoreboards


def live_scoreboards_payload(
    scoreboards: Sequence[LiveEventScoreboard],
    *,
    generated_at: datetime | None = None,
    as_of: date | None = None,
) -> dict[str, object]:
    """Convert live scoreboards into the public JSON payload."""

    generated = (generated_at or datetime.now(timezone.utc)).replace(microsecond=0)
    as_of_date = as_of or generated.date()
    source_ids = sorted(
        {
            score.source_id
            for scoreboard in scoreboards
            for score in scoreboard.scores
        }
    )
    return {
        "version": 1,
        "generated_at": generated.isoformat(),
        "as_of_date": as_of_date.isoformat(),
        "source_ids": source_ids,
        "events": [_scoreboard_to_mapping(scoreboard) for scoreboard in scoreboards],
    }


def write_live_scoreboards(
    scoreboards: Sequence[LiveEventScoreboard],
    path: Path | str = DEFAULT_LIVE_SCORING_FILE,
    *,
    generated_at: datetime | None = None,
    as_of: date | None = None,
) -> None:
    """Write scoreboards to a JSON file consumed by the app or automation."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = live_scoreboards_payload(scoreboards, generated_at=generated_at, as_of=as_of)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, sort_keys=True)
        output_file.write("\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate live eventing scoring JSON from result stores")
    parser.add_argument(
        "--results",
        action="append",
        type=Path,
        default=[],
        help="Result JSON store to read; repeatable. Defaults to data/fei_results.json.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_LIVE_SCORING_FILE)
    parser.add_argument("--as-of", type=_date_arg, help="Current scoring date, YYYY-MM-DD")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--lookahead-days", type=int, default=2)
    parser.add_argument("--max-events", type=int)
    args = parser.parse_args(argv)

    result_paths = args.results or [DEFAULT_RESULTS_FILE]
    results = load_result_files(result_paths)
    scoreboards = build_live_scoreboards(
        results,
        as_of=args.as_of,
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
        max_events=args.max_events,
    )
    write_live_scoreboards(scoreboards, args.output, as_of=args.as_of)
    print(
        "Live scoring snapshot written: "
        f"events={len(scoreboards)}, "
        f"results={sum(scoreboard.result_count for scoreboard in scoreboards)}, "
        f"output={args.output}"
    )
    return 0


def _scoreboard_from_group(results: Sequence[EventingResult]) -> LiveEventScoreboard:
    ranked_results = sorted(
        results,
        key=lambda result: (
            result.finishing_score,
            result.dressage_score,
            result.rider_name.lower(),
            result.horse_name.lower(),
        ),
    )

    scores: list[LiveScoreEntry] = []
    current_rank = 0
    previous_score: float | None = None
    for index, result in enumerate(ranked_results, start=1):
        if previous_score != result.finishing_score:
            current_rank = index
            previous_score = result.finishing_score
        scores.append(_score_entry(result, current_rank))

    first_result = ranked_results[0]
    last_collected_at = max(result.collected_at for result in ranked_results)
    event_key = _slug(
        f"{first_result.event_name}-{first_result.event_date.isoformat()}-"
        f"{first_result.level}-{first_result.country}"
    )
    score_tuple = tuple(scores)
    return LiveEventScoreboard(
        event_key=event_key,
        event_name=first_result.event_name,
        event_date=first_result.event_date,
        level=first_result.level,
        country=first_result.country,
        result_count=len(score_tuple),
        last_collected_at=last_collected_at,
        leader=score_tuple[0],
        scores=score_tuple,
    )


def _score_entry(result: EventingResult, rank: int) -> LiveScoreEntry:
    return LiveScoreEntry(
        rank=rank,
        rider_name=result.rider_name,
        horse_name=result.horse_name,
        total_penalties=result.finishing_score,
        dressage_score=result.dressage_score,
        show_jumping_penalties=result.show_jumping_penalties,
        cross_country_jump_penalties=result.cross_country_jump_penalties,
        cross_country_time_penalties=result.cross_country_time_penalties,
        source_id=result.source_id,
        source_record_id=result.source_record_id,
        collected_at=result.collected_at,
    )


def _scoreboard_to_mapping(scoreboard: LiveEventScoreboard) -> dict[str, object]:
    return {
        "event_key": scoreboard.event_key,
        "event_name": scoreboard.event_name,
        "event_date": scoreboard.event_date.isoformat(),
        "level": scoreboard.level,
        "country": scoreboard.country,
        "result_count": scoreboard.result_count,
        "last_collected_at": scoreboard.last_collected_at.isoformat(),
        "leader": _score_entry_to_mapping(scoreboard.leader),
        "scores": [_score_entry_to_mapping(score) for score in scoreboard.scores],
    }


def _score_entry_to_mapping(score: LiveScoreEntry) -> dict[str, object]:
    return {
        "rank": score.rank,
        "rider_name": score.rider_name,
        "horse_name": score.horse_name,
        "total_penalties": score.total_penalties,
        "dressage_score": score.dressage_score,
        "show_jumping_penalties": score.show_jumping_penalties,
        "cross_country_jump_penalties": score.cross_country_jump_penalties,
        "cross_country_time_penalties": score.cross_country_time_penalties,
        "source_id": score.source_id,
        "source_record_id": score.source_record_id,
        "collected_at": score.collected_at.isoformat(),
    }


def _event_key(result: EventingResult) -> tuple[str, date, str, str]:
    return (
        _slug(result.event_name),
        result.event_date,
        _slug(result.level),
        _slug(result.country),
    )


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


if __name__ == "__main__":
    raise SystemExit(main())
