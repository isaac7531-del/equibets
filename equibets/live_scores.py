"""Live event score snapshots from public result pages."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "current_event_scores.json"


@dataclass(frozen=True)
class LiveScoreLeader:
    """A current leader for one event division or phase."""

    division: str
    place: int
    rider_name: str
    horse_name: str
    score: float
    phase: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "LiveScoreLeader":
        return cls(
            division=_required_str(values, "division"),
            place=_required_int(values, "place"),
            rider_name=_required_str(values, "rider_name"),
            horse_name=_required_str(values, "horse_name"),
            score=_required_number(values, "score"),
            phase=_required_str(values, "phase"),
        )


@dataclass(frozen=True)
class LiveEventScore:
    """A public event score snapshot with one or more leaders."""

    id: str
    source_id: str
    source_name: str
    source_url: str
    event_name: str
    event_date: date
    event_end_date: date
    country: str
    level: str
    status: str
    phase: str
    leaders: tuple[LiveScoreLeader, ...]
    notes: str

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "LiveEventScore":
        leaders = _mapping_tuple(values, "leaders")
        return cls(
            id=_required_str(values, "id"),
            source_id=_required_str(values, "source_id"),
            source_name=_required_str(values, "source_name"),
            source_url=_required_str(values, "source_url"),
            event_name=_required_str(values, "event_name"),
            event_date=date.fromisoformat(_required_str(values, "event_date")),
            event_end_date=date.fromisoformat(_required_str(values, "event_end_date")),
            country=_required_str(values, "country"),
            level=_required_str(values, "level"),
            status=_required_str(values, "status"),
            phase=_required_str(values, "phase"),
            leaders=tuple(LiveScoreLeader.from_mapping(item) for item in leaders),
            notes=_required_str(values, "notes"),
        )

    @property
    def leader_count(self) -> int:
        return len(self.leaders)


@dataclass(frozen=True)
class LiveScoreSnapshot:
    """All live-score events collected during one refresh."""

    version: int
    collected_at: datetime
    coverage_note: str
    events: tuple[LiveEventScore, ...]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "LiveScoreSnapshot":
        events = _mapping_tuple(values, "events")
        return cls(
            version=_required_int(values, "version"),
            collected_at=datetime.fromisoformat(_required_str(values, "collected_at").replace("Z", "+00:00")),
            coverage_note=_required_str(values, "coverage_note"),
            events=tuple(LiveEventScore.from_mapping(item) for item in events),
        )

    @property
    def leader_count(self) -> int:
        return sum(event.leader_count for event in self.events)


def load_live_score_snapshot(path: Path | str = DATA_FILE) -> LiveScoreSnapshot:
    """Load the latest public live-score snapshot."""

    with Path(path).open(encoding="utf-8") as score_file:
        payload = json.load(score_file)

    return LiveScoreSnapshot.from_mapping(payload)


def current_live_events(
    snapshot: LiveScoreSnapshot,
    *,
    on_date: date | None = None,
) -> list[LiveEventScore]:
    """Return active or same-day event snapshots, ordered by event recency."""

    reference_date = on_date or snapshot.collected_at.date()
    return [
        event
        for event in sorted(snapshot.events, key=lambda item: item.event_date, reverse=True)
        if event.status == "active" or event.event_date <= reference_date <= event.event_end_date
    ]


def top_live_leaders(snapshot: LiveScoreSnapshot, *, limit: int = 5) -> list[LiveScoreLeader]:
    """Return the best available leader scores across the snapshot."""

    leaders = [leader for event in snapshot.events for leader in event.leaders]
    return sorted(leaders, key=lambda leader: (leader.score, leader.place, leader.rider_name))[:limit]


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_int(values: dict[str, object], key: str) -> int:
    value = values.get(key)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    return value


def _required_number(values: dict[str, object], key: str) -> float:
    value = values.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _mapping_tuple(values: dict[str, object], key: str) -> tuple[dict[str, object], ...]:
    value = values.get(key)
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        raise ValueError(f"{key} must be a list of objects")

    items = tuple(value)
    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"{key} must contain only objects")
    return items
