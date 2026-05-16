"""Live current-event score ingestion, search, and ranking helpers."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from .results import EventingResult, consolidate_results


COMPETITIVE_STATUSES = {"entered", "live", "complete"}
LIVE_STATUSES = COMPETITIVE_STATUSES | {"withdrawn", "eliminated", "retired"}
PHASE_STATUSES = {"not_started", "in_progress", "complete"}
PHASE_NAMES = ("dressage", "show_jumping", "cross_country")


@dataclass(frozen=True)
class LiveEventScore:
    """A score row from a current event, including partial phase progress."""

    source_id: str
    source_record_id: str
    source_priority: int
    rider_name: str
    horse_name: str
    event_name: str
    event_date: date
    level: str
    country: str
    collected_at: datetime
    status: str = "live"
    dressage_score: float | None = None
    show_jumping_penalties: float | None = None
    cross_country_jump_penalties: float | None = None
    cross_country_time_penalties: float | None = None
    dressage_status: str = "not_started"
    show_jumping_status: str = "not_started"
    cross_country_status: str = "not_started"
    source_url: str | None = None

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

    @property
    def completed_phase_count(self) -> int:
        return sum(
            status == "complete"
            for status in (
                self.dressage_status,
                self.show_jumping_status,
                self.cross_country_status,
            )
        )

    @property
    def is_competitive(self) -> bool:
        return self.status in COMPETITIVE_STATUSES

    @property
    def is_complete(self) -> bool:
        return self.status == "complete" or self.completed_phase_count == len(PHASE_NAMES)

    @property
    def live_total(self) -> float:
        """Current penalty total from available phases."""

        return round(
            sum(
                value
                for value in (
                    self.dressage_score,
                    self.show_jumping_penalties,
                    self.cross_country_jump_penalties,
                    self.cross_country_time_penalties,
                )
                if value is not None
            ),
            1,
        )

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "LiveEventScore":
        phase_statuses = _optional_phase_statuses(values)
        dressage_score = _optional_number(values, "dressage_score")
        show_jumping_penalties = _optional_number(values, "show_jumping_penalties")
        cross_country_jump_penalties = _optional_number(values, "cross_country_jump_penalties")
        cross_country_time_penalties = _optional_number(values, "cross_country_time_penalties")

        return cls(
            source_id=_required_str(values, "source_id"),
            source_record_id=_required_str(values, "source_record_id"),
            source_priority=_optional_int(values, "source_priority", 50),
            rider_name=_required_str(values, "rider_name"),
            horse_name=_required_str(values, "horse_name"),
            event_name=_required_str(values, "event_name"),
            event_date=date.fromisoformat(_required_str(values, "event_date")),
            level=_required_str(values, "level"),
            country=_required_str(values, "country"),
            collected_at=datetime.fromisoformat(_required_str(values, "collected_at")),
            status=_optional_status(values, "status", "complete" if _all_phases_complete(phase_statuses) else "live"),
            dressage_score=dressage_score,
            show_jumping_penalties=show_jumping_penalties,
            cross_country_jump_penalties=cross_country_jump_penalties,
            cross_country_time_penalties=cross_country_time_penalties,
            dressage_status=phase_statuses["dressage"],
            show_jumping_status=phase_statuses["show_jumping"],
            cross_country_status=phase_statuses["cross_country"],
            source_url=_optional_str(values, "source_url"),
        )

    def to_mapping(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_record_id": self.source_record_id,
            "source_priority": self.source_priority,
            "rider_name": self.rider_name,
            "horse_name": self.horse_name,
            "event_name": self.event_name,
            "event_date": self.event_date.isoformat(),
            "level": self.level,
            "country": self.country,
            "status": self.status,
            "dressage_score": self.dressage_score,
            "show_jumping_penalties": self.show_jumping_penalties,
            "cross_country_jump_penalties": self.cross_country_jump_penalties,
            "cross_country_time_penalties": self.cross_country_time_penalties,
            "phase_statuses": {
                "dressage": self.dressage_status,
                "show_jumping": self.show_jumping_status,
                "cross_country": self.cross_country_status,
            },
            "live_total": self.live_total,
            "collected_at": self.collected_at.isoformat(),
            "source_url": self.source_url,
        }

    def to_completed_result(self) -> EventingResult | None:
        """Convert complete live scores into the durable result shape."""

        if (
            not self.is_complete
            or self.dressage_score is None
            or self.show_jumping_penalties is None
            or self.cross_country_jump_penalties is None
            or self.cross_country_time_penalties is None
        ):
            return None

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
            dressage_score=self.dressage_score,
            show_jumping_penalties=self.show_jumping_penalties,
            cross_country_jump_penalties=self.cross_country_jump_penalties,
            cross_country_time_penalties=self.cross_country_time_penalties,
            collected_at=self.collected_at,
        )


def load_live_scores(path: Path | str) -> list[LiveEventScore]:
    """Load current-event scores from a JSON feed on disk."""

    with Path(path).open(encoding="utf-8") as live_file:
        return live_scores_from_payload(json.load(live_file))


def fetch_live_scores(url: str, *, timeout: float = 20) -> list[LiveEventScore]:
    """Fetch current-event scores from a JSON feed URL."""

    request = urllib.request.Request(url, headers={"User-Agent": "equibets-live-scoring/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    return live_scores_from_payload(payload)


def pull_current_event_scores(
    *,
    feed_urls: Iterable[str] = (),
    feed_paths: Iterable[Path | str] = (),
) -> list[LiveEventScore]:
    """Load and consolidate current-event scores from paths and remote feeds."""

    scores: list[LiveEventScore] = []
    for path in feed_paths:
        scores.extend(load_live_scores(path))
    for url in feed_urls:
        scores.extend(fetch_live_scores(url))
    return consolidate_live_scores(scores)


def live_scores_from_payload(payload: dict[str, object]) -> list[LiveEventScore]:
    """Normalize a feed payload into live score rows.

    Supported feed shapes:
    - {"results": [...]} with event fields on each row
    - {"events": [{"name": ..., "results": [...]}]} with event-level defaults
    """

    if not isinstance(payload, dict):
        raise ValueError("live score payload must be a JSON object")

    if "events" in payload:
        events = payload["events"]
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        scores: list[LiveEventScore] = []
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("events must contain objects")
            event_results = event.get("results", [])
            if not isinstance(event_results, list):
                raise ValueError("event results must be a list")
            defaults = _event_defaults(event)
            for result in event_results:
                if not isinstance(result, dict):
                    raise ValueError("results must contain objects")
                scores.append(LiveEventScore.from_mapping({**defaults, **result}))
        return consolidate_live_scores(scores)

    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("results must be a list")
    return consolidate_live_scores(
        [LiveEventScore.from_mapping(result) for result in results if isinstance(result, dict)]
    )


def consolidate_live_scores(scores: Sequence[LiveEventScore]) -> list[LiveEventScore]:
    """Deduplicate live scores, keeping the best source then newest collection."""

    selected: dict[tuple[str, str, date, str], LiveEventScore] = {}
    for score in scores:
        existing = selected.get(score.result_key)
        if existing is None or _is_better_live_score(score, existing):
            selected[score.result_key] = score
    return rank_live_scores(selected.values())


def rank_live_scores(scores: Iterable[LiveEventScore]) -> list[LiveEventScore]:
    """Rank current-event rows for a live leaderboard."""

    return sorted(
        scores,
        key=lambda score: (
            not score.is_competitive,
            -score.completed_phase_count,
            score.live_total,
            score.event_date,
            score.rider_name,
            score.horse_name,
        ),
    )


def search_live_scores(
    scores: Iterable[LiveEventScore],
    query: str,
    *,
    limit: int | None = None,
) -> list[LiveEventScore]:
    """Search live results by rider, horse, event, level, country, or source."""

    tokens = [_slug(token) for token in query.split() if _slug(token)]
    if not tokens:
        matches = rank_live_scores(scores)
    else:
        matches = [
            score
            for score in scores
            if all(token in _search_blob(score) for token in tokens)
        ]
        matches = rank_live_scores(matches)

    return matches[:limit] if limit is not None else matches


def merge_completed_live_results(
    existing_results: Sequence[EventingResult],
    live_scores: Sequence[LiveEventScore],
) -> list[EventingResult]:
    """Fold completed live rows into stored results using existing dedupe rules."""

    completed_results = [
        result
        for result in (score.to_completed_result() for score in live_scores)
        if result is not None
    ]
    return consolidate_results([*existing_results, *completed_results])


def live_scores_payload(scores: Sequence[LiveEventScore]) -> dict[str, object]:
    """Serialize live scores for the frontend feed."""

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_ids": sorted({score.source_id for score in scores}),
        "results": [score.to_mapping() for score in rank_live_scores(scores)],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull current-event live scoring feeds.")
    parser.add_argument("--feed-url", action="append", default=[], help="JSON feed URL to fetch.")
    parser.add_argument("--input", action="append", default=[], help="Local JSON feed to include.")
    parser.add_argument("--query", default="", help="Optional rider, horse, event, or source search query.")
    parser.add_argument("--output", help="Write normalized live score payload to this path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    scores = pull_current_event_scores(feed_urls=args.feed_url, feed_paths=args.input)
    if args.query:
        scores = search_live_scores(scores, args.query)

    payload = live_scores_payload(scores)
    indent = 2 if args.pretty else None
    encoded = json.dumps(payload, indent=indent)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(f"{encoded}\n", encoding="utf-8")
    else:
        print(encoded)
    return 0


def _event_defaults(event: dict[str, object]) -> dict[str, object]:
    return {
        "source_id": event.get("source_id"),
        "source_priority": event.get("source_priority"),
        "event_name": event.get("event_name") or event.get("name"),
        "event_date": event.get("event_date") or event.get("date"),
        "level": event.get("level"),
        "country": event.get("country"),
        "status": event.get("status"),
        "source_url": event.get("source_url"),
        "collected_at": event.get("collected_at"),
    }


def _is_better_live_score(candidate: LiveEventScore, existing: LiveEventScore) -> bool:
    if candidate.source_priority != existing.source_priority:
        return candidate.source_priority < existing.source_priority
    if candidate.completed_phase_count != existing.completed_phase_count:
        return candidate.completed_phase_count > existing.completed_phase_count
    return candidate.collected_at > existing.collected_at


def _search_blob(score: LiveEventScore) -> str:
    return " ".join(
        _slug(value)
        for value in (
            score.rider_name,
            score.horse_name,
            score.event_name,
            score.level,
            score.country,
            score.source_id,
            score.status,
        )
    )


def _optional_phase_statuses(values: dict[str, object]) -> dict[str, str]:
    raw_phase_statuses = values.get("phase_statuses", {})
    if raw_phase_statuses is None:
        raw_phase_statuses = {}
    if not isinstance(raw_phase_statuses, dict):
        raise ValueError("phase_statuses must be an object")

    cross_country_score = values.get("cross_country_jump_penalties")
    if not isinstance(cross_country_score, (int, float)):
        cross_country_score = values.get("cross_country_time_penalties")

    return {
        "dressage": _phase_status(raw_phase_statuses, "dressage", values.get("dressage_score")),
        "show_jumping": _phase_status(
            raw_phase_statuses,
            "show_jumping",
            values.get("show_jumping_penalties"),
        ),
        "cross_country": _phase_status(
            raw_phase_statuses,
            "cross_country",
            cross_country_score,
        ),
    }


def _phase_status(values: dict[str, object], key: str, score_value: object) -> str:
    value = values.get(key)
    if value is None:
        return "complete" if isinstance(score_value, (int, float)) else "not_started"
    if not isinstance(value, str) or value not in PHASE_STATUSES:
        raise ValueError(f"{key} phase status must be one of {sorted(PHASE_STATUSES)}")
    return value


def _all_phases_complete(phase_statuses: dict[str, str]) -> bool:
    return all(status == "complete" for status in phase_statuses.values())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


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
    if value is None:
        return default
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


def _optional_status(values: dict[str, object], key: str, default: str) -> str:
    value = values.get(key, default)
    if value is None:
        return default
    if not isinstance(value, str) or value not in LIVE_STATUSES:
        raise ValueError(f"{key} must be one of {sorted(LIVE_STATUSES)}")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
