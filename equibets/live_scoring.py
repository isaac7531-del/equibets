"""Live current-event score ingestion, search, and ranking helpers."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

from .results import EventingResult, consolidate_results


COMPETITIVE_STATUSES = {"entered", "live", "complete"}
LIVE_STATUSES = COMPETITIVE_STATUSES | {"withdrawn", "eliminated", "retired"}
PHASE_STATUSES = {"not_started", "in_progress", "complete"}
PHASE_NAMES = ("dressage", "show_jumping", "cross_country")
STARTBOX_SOURCE_ID = "startbox_scoring"
STARTBOX_SOURCE_PRIORITY = 45
STARTBOX_CALENDAR_URL = "https://eventing.startboxscoring.com/"


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


@dataclass(frozen=True)
class StartBoxEvent:
    """A current or near-current event discovered from StartBox Scoring."""

    id: str
    name: str
    starts_on: date
    ends_on: date
    location: str
    country: str
    status: str
    score_status: str
    result_url: str


@dataclass(frozen=True)
class StartBoxDivision:
    """A StartBox division with links to published scores and timings."""

    name: str
    phase_status: str
    entry_status_url: str | None = None
    times_url: str | None = None
    scores_url: str | None = None


@dataclass(frozen=True)
class StartBoxScoreEntry:
    """One row parsed from a StartBox leader or division score page."""

    id: str
    rider_name: str
    horse_name: str
    division: str
    status: str
    dressage_penalties: float | None
    total_penalties: float | None
    source_url: str


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


def pull_startbox_current_event_scores(
    *,
    calendar_url: str = STARTBOX_CALENDAR_URL,
    as_of: date | None = None,
    lookback_days: int = 1,
    lookahead_days: int = 7,
    timeout_seconds: int = 20,
) -> list[LiveEventScore]:
    """Discover StartBox current events and return normalized live score rows."""

    effective_date = as_of or date.today()
    collected_at = datetime.now(timezone.utc)
    calendar_content = _fetch_startbox_url(calendar_url, timeout_seconds=timeout_seconds)
    events = [
        event
        for event in parse_startbox_calendar(calendar_content, as_of=effective_date, base_url=calendar_url)
        if _is_within_window(event, effective_date, lookback_days, lookahead_days)
    ]

    scores: list[LiveEventScore] = []
    for event in events:
        event_page = _fetch_startbox_url(event.result_url, timeout_seconds=timeout_seconds)
        divisions = parse_startbox_event_page(event_page, base_url=event.result_url)
        leader_entries = parse_startbox_event_leaders(event_page, base_url=event.result_url)
        leader_statuses = {entry.division: entry.status for entry in leader_entries}
        score_entries: list[StartBoxScoreEntry] = []
        scored_divisions: set[str] = set()

        for division in divisions:
            if not division.scores_url:
                continue

            scores_page = _fetch_startbox_url(division.scores_url, timeout_seconds=timeout_seconds)
            entries = parse_startbox_scores_page(
                scores_page,
                division=division.name,
                status=leader_statuses.get(division.name, _score_status_from_url(division.scores_url)),
                source_url=division.scores_url,
            )
            if entries:
                scored_divisions.add(division.name)
                score_entries.extend(entries)

        score_entries.extend(entry for entry in leader_entries if entry.division not in scored_divisions)
        scores.extend(_live_scores_from_startbox_entries(event, score_entries, collected_at=collected_at))

    return consolidate_live_scores(scores)


def parse_startbox_calendar(
    content: str,
    *,
    as_of: date | None = None,
    base_url: str = STARTBOX_CALENDAR_URL,
) -> list[StartBoxEvent]:
    """Parse StartBox's event calendar into normalized current-event records."""

    effective_date = as_of or date.today()
    rows = _markdown_calendar_rows(content)
    if not rows:
        rows = _html_calendar_rows(content)

    events: list[StartBoxEvent] = []
    for date_label, link_label, link_url, description in rows:
        parsed_dates = _parse_date_label(date_label)
        if parsed_dates is None or not link_url:
            continue

        starts_on, ends_on = parsed_dates
        name, location, country = _split_event_description(description)
        result_url = urljoin(base_url, link_url)
        events.append(
            StartBoxEvent(
                id=_event_id(STARTBOX_SOURCE_ID, result_url, name),
                name=name,
                starts_on=starts_on,
                ends_on=ends_on,
                location=location,
                country=country,
                status=_event_status(starts_on, ends_on, effective_date),
                score_status=link_label.strip().lower() or "unknown",
                result_url=result_url,
            )
        )

    return events


def parse_startbox_event_page(content: str, *, base_url: str = STARTBOX_CALENDAR_URL) -> tuple[StartBoxDivision, ...]:
    """Parse division phase/timing rows from a StartBox event page."""

    normalized_base_url = _directory_base_url(base_url)
    divisions: list[StartBoxDivision] = []
    for name, phase_cell in _markdown_division_rows(content):
        if name.lower() in {"division", "phase", "rider"} or not name.strip("- "):
            continue

        links = {
            label.lower(): urljoin(normalized_base_url, url)
            for label, url in _markdown_links(phase_cell)
        }
        phase_status = _strip_markdown_links(phase_cell).strip(" -")
        divisions.append(
            StartBoxDivision(
                name=name.strip(),
                phase_status=phase_status,
                entry_status_url=links.get("entry status"),
                times_url=links.get("times"),
                scores_url=_score_url_from_links(links),
            )
        )

    if divisions:
        return tuple(divisions)

    for name, phase_status, entry_status_url, times_url, scores_url in _html_division_rows(
        content,
        base_url=normalized_base_url,
    ):
        if name.lower() in {"division", "phase", "rider"} or not name.strip("- "):
            continue

        divisions.append(
            StartBoxDivision(
                name=name.strip(),
                phase_status=phase_status,
                entry_status_url=entry_status_url,
                times_url=times_url,
                scores_url=scores_url,
            )
        )

    return tuple(divisions)


def parse_startbox_event_leaders(
    content: str,
    *,
    base_url: str = STARTBOX_CALENDAR_URL,
) -> tuple[StartBoxScoreEntry, ...]:
    """Parse current leader rows from a StartBox event division listing."""

    normalized_base_url = _directory_base_url(base_url)
    entries: list[StartBoxScoreEntry] = []
    for row in _html_table_rows(content):
        if len(row) < 5:
            continue

        division = _strip_tags(row[0])
        rider_name = _strip_tags(row[2])
        horse_name = _strip_tags(row[3])
        total_penalties = _parse_score_number(_strip_tags(row[4]))
        if not division or division.lower() in {"division", "rider"} or not rider_name or not horse_name:
            continue
        if total_penalties is None:
            continue

        links = {
            label.lower(): urljoin(normalized_base_url, url)
            for label, url in _html_links(row[1])
        }
        entries.append(
            StartBoxScoreEntry(
                id=_entry_id(division, rider_name, horse_name),
                rider_name=rider_name,
                horse_name=horse_name,
                division=division,
                status=_score_status_from_links(links),
                dressage_penalties=None,
                total_penalties=total_penalties,
                source_url=base_url,
            )
        )

    return tuple(entries)


def parse_startbox_scores_page(
    content: str,
    *,
    division: str,
    status: str = "scores",
    source_url: str = STARTBOX_CALENDAR_URL,
) -> tuple[StartBoxScoreEntry, ...]:
    """Parse all scored rows from a StartBox division score page."""

    entries: list[StartBoxScoreEntry] = []
    for row in _html_table_rows(content):
        if len(row) < 5:
            continue

        start_number = _strip_tags(row[0])
        rider_name = _strip_tags(row[1])
        horse_name = _horse_name_from_cell(row[2])
        if not start_number or not rider_name or not horse_name:
            continue
        if start_number.lower() in {"no.", "no", "score"}:
            continue
        if rider_name.lower() == "rider" or horse_name.lower().startswith("horse"):
            continue

        dressage_penalties = _parse_score_number(_strip_tags(row[3]))
        total_penalties = _parse_score_number(_strip_tags(_total_score_cell(row)))
        entries.append(
            StartBoxScoreEntry(
                id=_entry_id(division, rider_name, horse_name, start_number),
                rider_name=rider_name,
                horse_name=horse_name,
                division=division,
                status=_row_status(row, status),
                dressage_penalties=dressage_penalties,
                total_penalties=total_penalties,
                source_url=source_url,
            )
        )

    return tuple(entries)


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
    parser.add_argument("--startbox", action="store_true", help="Discover and pull current StartBox Scoring results.")
    parser.add_argument("--startbox-calendar-url", default=STARTBOX_CALENDAR_URL, help="StartBox calendar URL to fetch.")
    parser.add_argument("--as-of", help="Current date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--lookback-days", type=int, default=1, help="Completed-event lookback window for StartBox.")
    parser.add_argument("--lookahead-days", type=int, default=7, help="Upcoming-event lookahead window for StartBox.")
    parser.add_argument("--timeout-seconds", type=int, default=20, help="HTTP timeout per StartBox request.")
    parser.add_argument("--query", default="", help="Optional rider, horse, event, or source search query.")
    parser.add_argument("--output", help="Write normalized live score payload to this path.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    scores = pull_current_event_scores(feed_urls=args.feed_url, feed_paths=args.input)
    if args.startbox:
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
        scores = consolidate_live_scores(
            [
                *scores,
                *pull_startbox_current_event_scores(
                    calendar_url=args.startbox_calendar_url,
                    as_of=as_of,
                    lookback_days=args.lookback_days,
                    lookahead_days=args.lookahead_days,
                    timeout_seconds=args.timeout_seconds,
                ),
            ]
        )
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


def _live_scores_from_startbox_entries(
    event: StartBoxEvent,
    entries: Iterable[StartBoxScoreEntry],
    *,
    collected_at: datetime,
) -> list[LiveEventScore]:
    scores: list[LiveEventScore] = []
    for entry in _deduplicate_startbox_entries(entries):
        if entry.total_penalties is None and entry.dressage_penalties is None:
            continue

        dressage_score = entry.dressage_penalties
        show_jumping_penalties = _difference_or_none(entry.total_penalties, entry.dressage_penalties)

        # Some StartBox leader tables expose only a current total. Preserve it
        # as the available live total so the frontend can rank the row.
        if dressage_score is None and entry.total_penalties is not None:
            dressage_score = entry.total_penalties

        phase_statuses = _phase_statuses_from_startbox_score(dressage_score, show_jumping_penalties, event.status)
        scores.append(
            LiveEventScore(
                source_id=STARTBOX_SOURCE_ID,
                source_record_id=f"{event.id}-{entry.id}",
                source_priority=STARTBOX_SOURCE_PRIORITY,
                rider_name=entry.rider_name,
                horse_name=entry.horse_name,
                event_name=event.name,
                event_date=event.starts_on,
                level=entry.division,
                country=event.country or "USA",
                collected_at=collected_at,
                status=_live_status_from_startbox(entry.status, event.status, phase_statuses),
                dressage_score=dressage_score,
                show_jumping_penalties=show_jumping_penalties,
                cross_country_jump_penalties=None,
                cross_country_time_penalties=None,
                dressage_status=phase_statuses["dressage"],
                show_jumping_status=phase_statuses["show_jumping"],
                cross_country_status=phase_statuses["cross_country"],
                source_url=entry.source_url,
            )
        )

    return scores


def _phase_statuses_from_startbox_score(
    dressage_score: float | None,
    show_jumping_penalties: float | None,
    event_status: str,
) -> dict[str, str]:
    cross_country_status = "complete" if event_status == "completed" and show_jumping_penalties is not None else "not_started"
    return {
        "dressage": "complete" if dressage_score is not None else "not_started",
        "show_jumping": "complete" if show_jumping_penalties is not None else "not_started",
        "cross_country": cross_country_status,
    }


def _live_status_from_startbox(entry_status: str, event_status: str, phase_statuses: dict[str, str]) -> str:
    normalized = _slug(entry_status).replace("-", "_")
    if "withdraw" in normalized:
        return "withdrawn"
    if "elimin" in normalized:
        return "eliminated"
    if "retir" in normalized:
        return "retired"
    if normalized == "final" or event_status == "completed" or _all_phases_complete(phase_statuses):
        return "complete"
    if event_status == "upcoming":
        return "entered"
    return "live"


def _fetch_startbox_url(url: str, *, timeout_seconds: int) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 "
                "EquibetsLiveScoring/0.1"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def _markdown_calendar_rows(content: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    row_pattern = re.compile(
        r"^\|\s*(?P<date>[^|]+?)\s*\|\s*(?P<link>[^|]+?)\s*\|\s*(?P<description>[^|]+?)\s*\|",
        re.MULTILINE,
    )
    for match in row_pattern.finditer(content):
        date_label = match.group("date").strip()
        if date_label == "---" or date_label.lower() == "division":
            continue

        link_label, link_url = _first_markdown_link(match.group("link"))
        if not link_label:
            link_label = match.group("link").strip()
        rows.append((date_label, link_label, link_url, match.group("description").strip()))
    return rows


def _markdown_division_rows(content: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    row_pattern = re.compile(
        r"^\|\s*(?P<division>[^|]+?)\s*\|\s*(?P<phase>[^|]+?)\s*\|",
        re.MULTILINE,
    )
    for match in row_pattern.finditer(content):
        division = match.group("division").strip()
        phase = match.group("phase").strip()
        if division == "---":
            continue
        rows.append((division, phase))
    return rows


def _html_calendar_rows(content: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for row_match in re.finditer(r"<tr[^>]*>(?P<row>.*?)</tr>", content, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_match.group("row"), flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 3:
            continue

        first = _strip_tags(cells[0])
        second_label, second_url = _first_html_link(cells[1])
        show_name = _html_class_text(cells[2], "calshowname")
        location = _html_class_text(cells[2], "callocation")
        third = f"{show_name} {location}".strip() if show_name else _strip_tags(cells[2])
        rows.append((first, second_label, second_url, third))
    return rows


def _html_division_rows(
    content: str,
    *,
    base_url: str,
) -> list[tuple[str, str, str | None, str | None, str | None]]:
    rows: list[tuple[str, str, str | None, str | None, str | None]] = []
    for cells in _html_table_rows(content):
        if len(cells) < 2:
            continue

        name = _strip_tags(cells[0])
        links = {
            label.lower(): urljoin(base_url, url)
            for label, url in _html_links(cells[1])
        }
        phase_without_links = re.sub(
            r"<a\b[^>]*>.*?</a>",
            " ",
            cells[1],
            flags=re.IGNORECASE | re.DOTALL,
        )
        rows.append(
            (
                name,
                _strip_tags(phase_without_links),
                links.get("entry status"),
                links.get("times"),
                _score_url_from_links(links),
            )
        )
    return rows


def _html_table_rows(content: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_match in re.finditer(r"<tr[^>]*>(?P<row>.*?)</tr>", content, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_match.group("row"), flags=re.IGNORECASE | re.DOTALL)
        if cells:
            rows.append(cells)
    return rows


def _parse_date_label(date_label: str) -> tuple[date, date] | None:
    match = re.fullmatch(
        r"(?P<month>[A-Za-z]+)\s+(?P<start>\d{1,2})(?:-(?P<end>\d{1,2}))?,\s+(?P<year>\d{4})",
        date_label.strip(),
    )
    if not match:
        return None

    month = _month_number(match.group("month"))
    if month is None:
        return None

    year = int(match.group("year"))
    start_day = int(match.group("start"))
    end_day = int(match.group("end") or start_day)
    return date(year, month, start_day), date(year, month, end_day)


def _month_number(month_name: str) -> int | None:
    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    return months.get(month_name[:3].lower())


def _split_event_description(description: str) -> tuple[str, str, str]:
    normalized = " ".join(description.split())
    match = re.fullmatch(
        r"(?P<name>.+)\s+(?P<location>[A-Z][A-Za-z .'-]+,\s*[A-Z]{2}\s+(?P<country>US|Canada))",
        normalized,
    )
    if match:
        country = "CAN" if match.group("country") == "Canada" else "USA"
        return match.group("name"), match.group("location"), country

    country_match = re.search(r"\b(?P<country>US|Canada)\b$", normalized)
    if not country_match:
        return normalized, "", ""
    country = "CAN" if country_match.group("country") == "Canada" else "USA"
    return normalized, "", country


def _event_status(starts_on: date, ends_on: date, as_of: date) -> str:
    if starts_on <= as_of <= ends_on:
        return "live"
    if ends_on < as_of:
        return "completed"
    return "upcoming"


def _is_within_window(event: StartBoxEvent, as_of: date, lookback_days: int, lookahead_days: int) -> bool:
    earliest = as_of - timedelta(days=lookback_days)
    latest = as_of + timedelta(days=lookahead_days)
    return event.ends_on >= earliest and event.starts_on <= latest


def _event_id(source_id: str, result_url: str, name: str) -> str:
    parsed = urlparse(result_url)
    path_slug = _slug(parsed.path.strip("/").replace("/", "-"))
    if path_slug:
        return f"{source_id}-{path_slug}"
    return f"{source_id}-{_slug(name)}"


def _directory_base_url(url: str) -> str:
    parsed = urlparse(url)
    last_path_part = parsed.path.rsplit("/", 1)[-1]
    if parsed.path.endswith("/") or "." in last_path_part:
        return url
    return f"{url.rstrip('/')}/"


def _markdown_links(content: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)


def _first_markdown_link(content: str) -> tuple[str, str]:
    links = _markdown_links(content)
    return links[0] if links else ("", "")


def _first_html_link(content: str) -> tuple[str, str]:
    links = _html_links(content)
    if not links:
        return _strip_tags(content), ""
    return links[0]


def _html_links(content: str) -> list[tuple[str, str]]:
    return [
        (_strip_tags(match.group("label")), match.group("href"))
        for match in re.finditer(
            r"<a[^>]+href=[\"'](?P<href>[^\"']+)[\"'][^>]*>(?P<label>.*?)</a>",
            content,
            flags=re.IGNORECASE | re.DOTALL,
        )
    ]


def _score_url_from_links(links: dict[str, str]) -> str | None:
    for label, url in links.items():
        if "score" in label:
            return url
    return None


def _score_status_from_links(links: dict[str, str]) -> str:
    for label in links:
        if "final" in label and "score" in label:
            return "final"
        if "provisional" in label and "score" in label:
            return "provisional"
        if "score" in label:
            return "in_progress"
    return "unknown"


def _score_status_from_url(url: str) -> str:
    if "phase2" in url.lower():
        return "in_progress"
    return "in_progress"


def _horse_name_from_cell(content: str) -> str:
    horse_part = re.split(r"<br\b|<br\s*\\", content, maxsplit=1, flags=re.IGNORECASE)[0]
    return _strip_tags(horse_part)


def _parse_score_number(value: str) -> float | None:
    normalized = value.replace("\xa0", " ").strip()
    if not normalized or normalized in {"---", "--"}:
        return None
    match = re.search(r"\d+(?:\.\d+)?", normalized)
    if not match:
        return None
    return float(match.group(0))


def _total_score_cell(row: list[str]) -> str:
    if len(row) >= 9:
        return row[-3]
    return row[-2]


def _row_status(row: list[str], default: str) -> str:
    final_cell = _strip_tags(row[-1]).strip()
    if final_cell and _parse_score_number(final_cell) is None and final_cell not in {"---", "--"}:
        return final_cell.lower()
    return default


def _difference_or_none(total: float | None, base: float | None) -> float | None:
    if total is None or base is None:
        return None
    return round(max(0.0, total - base), 1)


def _deduplicate_startbox_entries(entries: Iterable[StartBoxScoreEntry]) -> list[StartBoxScoreEntry]:
    deduplicated: dict[str, StartBoxScoreEntry] = {}
    for entry in entries:
        deduplicated.setdefault(entry.id, entry)
    return list(deduplicated.values())


def _entry_id(division: str, rider_name: str, horse_name: str, start_number: str | None = None) -> str:
    parts = [division, start_number or "", rider_name, horse_name]
    return _slug("-".join(part for part in parts if part))


def _html_class_text(content: str, class_name: str) -> str:
    match = re.search(
        rf"<span[^>]+class=[\"'][^\"']*\b{re.escape(class_name)}\b[^\"']*[\"'][^>]*>(?P<value>.*?)</span>",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _strip_tags(match.group("value")) if match else ""


def _strip_markdown_links(content: str) -> str:
    return re.sub(r"\[[^\]]+\]\([^)]+\)", "", content)


def _strip_tags(content: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", content)
    return " ".join(without_tags.replace("&nbsp;", " ").split())


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
