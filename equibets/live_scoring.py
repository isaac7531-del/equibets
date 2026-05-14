"""Live/current-event score feed helpers.

The live feed is intentionally small and source-shaped: provider pages are
normalized into phase scores while preserving source URLs and collection times.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "live_scores.json"


@dataclass(frozen=True)
class LiveScore:
    """One live-scoring row for a combination at a current event."""

    horse_name: str
    rider_name: str
    division: str
    place: str
    dressage_score: float
    show_jumping_penalties: float
    show_jumping_time_penalties: float
    cross_country_jump_penalties: float
    cross_country_time_penalties: float
    total_penalties: float
    status: str = "final"

    @property
    def phase_total(self) -> float:
        return round(
            self.dressage_score
            + self.show_jumping_penalties
            + self.show_jumping_time_penalties
            + self.cross_country_jump_penalties
            + self.cross_country_time_penalties,
            1,
        )

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "LiveScore":
        return cls(
            horse_name=_required_str(values, "horse_name"),
            rider_name=_required_str(values, "rider_name"),
            division=_required_str(values, "division"),
            place=_required_str(values, "place"),
            dressage_score=_required_number(values, "dressage_score"),
            show_jumping_penalties=_required_number(values, "show_jumping_penalties"),
            show_jumping_time_penalties=_required_number(
                values,
                "show_jumping_time_penalties",
            ),
            cross_country_jump_penalties=_required_number(
                values,
                "cross_country_jump_penalties",
            ),
            cross_country_time_penalties=_required_number(
                values,
                "cross_country_time_penalties",
            ),
            total_penalties=_required_number(values, "total_penalties"),
            status=_optional_str(values, "status", "final"),
        )


@dataclass(frozen=True)
class LiveEvent:
    """A current event with normalized live-scoring rows."""

    id: str
    name: str
    source_id: str
    source_name: str
    source_url: str
    country: str
    date_label: str
    collected_at: datetime
    status: str
    scores: tuple[LiveScore, ...]

    @property
    def leader(self) -> LiveScore | None:
        if not self.scores:
            return None
        return sorted_live_scores(self.scores)[0]

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "LiveEvent":
        return cls(
            id=_required_str(values, "id"),
            name=_required_str(values, "name"),
            source_id=_required_str(values, "source_id"),
            source_name=_required_str(values, "source_name"),
            source_url=_required_str(values, "source_url"),
            country=_required_str(values, "country"),
            date_label=_required_str(values, "date_label"),
            collected_at=datetime.fromisoformat(_required_str(values, "collected_at")),
            status=_required_str(values, "status"),
            scores=tuple(
                LiveScore.from_mapping(item)
                for item in _required_list(values, "scores")
                if isinstance(item, dict)
            ),
        )


def load_live_events(path: Path | str = DATA_FILE) -> list[LiveEvent]:
    """Load current live-scoring events from JSON."""

    with Path(path).open(encoding="utf-8") as scores_file:
        payload = json.load(scores_file)

    return [LiveEvent.from_mapping(item) for item in payload["events"]]


def sorted_live_scores(scores: tuple[LiveScore, ...] | list[LiveScore]) -> list[LiveScore]:
    """Sort live rows by final place when available, then by penalties."""

    return sorted(scores, key=lambda score: (_place_key(score.place), score.total_penalties))


def current_event_leaders(events: list[LiveEvent], *, limit: int = 10) -> list[LiveScore]:
    """Return the best current scores across all loaded events."""

    scores = [score for event in events for score in event.scores]
    return sorted_live_scores(scores)[:limit]


def parse_usea_results_markdown(
    markdown: str,
    *,
    event_id: str,
    event_name: str,
    date_label: str,
    source_url: str,
    collected_at: datetime,
    country: str = "USA",
) -> LiveEvent:
    """Parse USEA result-page markdown into a normalized live event.

    USEA pages expose phase columns in this order: D-S, XC-J, XC-T, SJ-J, SJ-T,
    final score, final place, USEA points, and upgrade points.
    """

    scores: list[LiveScore] = []
    division = ""
    starters = ""
    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    index = 0

    while index < len(lines):
        heading = _USEA_DIVISION_RE.match(lines[index])
        if heading:
            division = heading.group("division")
            starters = heading.group("starters")
            index += 1
            continue

        competitor = _USEA_COMPETITOR_RE.search(lines[index])
        if division and competitor:
            tokens = lines[index + 1 : index + 10]
            if len(tokens) == 9:
                score = _score_from_usea_tokens(
                    horse_name=competitor.group("horse"),
                    rider_name=competitor.group("rider"),
                    division=f"{division} ({starters} starters)",
                    tokens=tokens,
                )
                if score is not None:
                    scores.append(score)
                index += 10
                continue

        index += 1

    return LiveEvent(
        id=event_id,
        name=event_name,
        source_id="usea",
        source_name="United States Eventing Association",
        source_url=source_url,
        country=country,
        date_label=date_label,
        collected_at=collected_at,
        status="results_posted",
        scores=tuple(sorted_live_scores(scores)),
    )


def _score_from_usea_tokens(
    *,
    horse_name: str,
    rider_name: str,
    division: str,
    tokens: list[str],
) -> LiveScore | None:
    dressage = _optional_number(tokens[0])
    xc_jump = _optional_number(tokens[1])
    xc_time = _optional_number(tokens[2])
    sj_jump = _optional_number(tokens[3])
    sj_time = _optional_number(tokens[4])
    total = _optional_number(tokens[5])
    place = tokens[6]

    if None in (dressage, xc_jump, xc_time, sj_jump, sj_time, total):
        return None

    return LiveScore(
        horse_name=horse_name,
        rider_name=_title_name(rider_name),
        division=division,
        place=place,
        dressage_score=dressage,
        show_jumping_penalties=sj_jump,
        show_jumping_time_penalties=sj_time,
        cross_country_jump_penalties=xc_jump,
        cross_country_time_penalties=xc_time,
        total_penalties=total,
    )


def _place_key(place: str) -> tuple[int, str]:
    if place.isdigit():
        return (int(place), "")
    return (9999, place)


def _optional_number(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _title_name(value: str) -> str:
    return " ".join(part.capitalize() for part in value.split())


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_str(values: dict[str, object], key: str, default: str) -> str:
    value = values.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_number(values: dict[str, object], key: str) -> float:
    value = values.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _required_list(values: dict[str, object], key: str) -> list[object]:
    value = values.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    return value


_USEA_DIVISION_RE = re.compile(r"^###### (?P<division>.+) \(Starters: (?P<starters>\d+)\)$")
_USEA_COMPETITOR_RE = re.compile(
    r"\[(?P<horse>[^\]]+)\]\([^)]+\)\s*/\s*\[(?P<rider>[^\]]+)\]\([^)]+\)",
)
