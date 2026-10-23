"""Upcoming event records and stores."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


DEFAULT_UPCOMING_EVENTS_FILE = Path(__file__).resolve().parents[1] / "data" / "upcoming_events.json"


@dataclass(frozen=True)
class UpcomingEvent:
    """One upcoming event discovered from a public eventing calendar."""

    source_id: str
    source_event_id: str
    source_priority: int
    name: str
    start_date: date
    end_date: date | None
    country: str
    discipline: str
    level: str
    source_url: str
    collected_at: datetime

    @property
    def event_key(self) -> tuple[str, date, str, str]:
        return (_slug(self.name), self.start_date, self.country.upper(), _slug(self.level))

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "UpcomingEvent":
        return cls(
            source_id=_required_str(values, "source_id"),
            source_event_id=_required_str(values, "source_event_id"),
            source_priority=_required_int(values, "source_priority"),
            name=_required_str(values, "name"),
            start_date=date.fromisoformat(_required_str(values, "start_date")),
            end_date=_optional_date(values, "end_date"),
            country=_required_str(values, "country"),
            discipline=_required_str(values, "discipline"),
            level=_required_str(values, "level"),
            source_url=_required_str(values, "source_url"),
            collected_at=datetime.fromisoformat(_required_str(values, "collected_at")),
        )


class UpcomingEventStore:
    """Persist upcoming events in the project's normalized JSON format."""

    def __init__(self, path: Path | str = DEFAULT_UPCOMING_EVENTS_FILE) -> None:
        self.path = Path(path)

    def load(self) -> list[UpcomingEvent]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as events_file:
            payload = json.load(events_file)
        return [UpcomingEvent.from_mapping(item) for item in payload.get("events", [])]

    def merge(self, new_events: list[UpcomingEvent]) -> list[UpcomingEvent]:
        return consolidate_upcoming_events([*self.load(), *new_events])

    def save(self, events: list[UpcomingEvent]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "events": [upcoming_event_to_mapping(event) for event in events],
        }
        with self.path.open("w", encoding="utf-8") as events_file:
            json.dump(payload, events_file, indent=2, sort_keys=True)
            events_file.write("\n")


def consolidate_upcoming_events(events: list[UpcomingEvent]) -> list[UpcomingEvent]:
    """Deduplicate calendar events, keeping higher-priority and fresher sources."""

    selected: dict[tuple[str, date, str, str], UpcomingEvent] = {}
    for event in events:
        existing = selected.get(event.event_key)
        if existing is None or _is_better_event(event, existing):
            selected[event.event_key] = event
    return sorted(selected.values(), key=lambda event: (event.start_date, event.name, event.country))


def upcoming_event_to_mapping(event: UpcomingEvent) -> dict[str, object]:
    return {
        "source_id": event.source_id,
        "source_event_id": event.source_event_id,
        "source_priority": event.source_priority,
        "name": event.name,
        "start_date": event.start_date.isoformat(),
        "end_date": event.end_date.isoformat() if event.end_date else None,
        "country": event.country,
        "discipline": event.discipline,
        "level": event.level,
        "source_url": event.source_url,
        "collected_at": event.collected_at.isoformat(),
    }


def _is_better_event(candidate: UpcomingEvent, existing: UpcomingEvent) -> bool:
    if candidate.source_priority != existing.source_priority:
        return candidate.source_priority < existing.source_priority
    return candidate.collected_at > existing.collected_at


def _slug(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")


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


def _optional_date(values: dict[str, object], key: str) -> date | None:
    value = values.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be null or a non-empty string")
    return date.fromisoformat(value)
