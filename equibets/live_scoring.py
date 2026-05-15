"""Live-score discovery and snapshot helpers for current eventing results."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence


STARTBOX_ARCHIVE_URL = "https://eventing.startboxscoring.com/archives.php?Year={year}"
_MONTHS = {
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


@dataclass(frozen=True)
class CurrentEvent:
    """A current or recently completed event discovered from a results archive."""

    event_name: str
    event_date: date
    status: str
    source_url: str


@dataclass(frozen=True)
class LiveLeader:
    """A division leader pulled from an active event results page."""

    event_name: str
    event_date: date
    location: str
    division: str
    phase: str
    rider_name: str
    horse_name: str
    score: float
    source_url: str
    collected_at: datetime


def parse_startbox_archive(
    text: str,
    *,
    as_of: date,
    lookback_days: int = 7,
    lookahead_days: int = 3,
) -> list[CurrentEvent]:
    """Extract current StartBox/EventingScores event links from archive text.

    The parser accepts either the raw page text or markdown extracted from the
    page. It keeps events close to ``as_of`` because those are most useful for
    hourly refreshes and live-score display.
    """

    events: list[CurrentEvent] = []
    for line in text.splitlines():
        cells = _markdown_table_cells(line)
        if len(cells) < 3:
            continue

        event_date = _parse_archive_date(cells[0])
        if event_date is None or abs((event_date - as_of).days) > max(lookback_days, lookahead_days):
            continue

        link = _parse_markdown_link(cells[1])
        if link is None:
            continue

        status, source_url = link
        if status.lower() not in {"results", "times", "scores"}:
            continue
        if event_date < as_of and (as_of - event_date).days > lookback_days:
            continue
        if event_date > as_of and (event_date - as_of).days > lookahead_days:
            continue

        events.append(
            CurrentEvent(
                event_name=_clean_text(cells[2]),
                event_date=event_date,
                status=status.lower(),
                source_url=source_url,
            )
        )

    return sorted(events, key=lambda event: (event.event_date, event.event_name))


def parse_startbox_leaders(
    text: str,
    *,
    source_url: str,
    collected_at: datetime | None = None,
) -> list[LiveLeader]:
    """Extract division leaders from a StartBox/EventingScores event page."""

    event_name = _first_match(text, r"^#\s+(.+?)\s*$")
    event_details = _first_match(text, r"^##\s+(.+?)\s+-\s+(.+?)\s*$")
    if event_name is None or event_details is None:
        return []

    event_date_text, location = event_details
    event_date = _parse_event_date(event_date_text)
    if event_date is None:
        return []

    collected = collected_at or datetime.now(timezone.utc)
    leaders: list[LiveLeader] = []
    for line in text.splitlines():
        cells = _markdown_table_cells(line)
        if len(cells) < 5 or cells[0].lower() in {"division", "rider", "---"}:
            continue

        score = _parse_score(cells[4])
        if score is None:
            continue

        leaders.append(
            LiveLeader(
                event_name=_clean_text(event_name),
                event_date=event_date,
                location=_clean_text(location),
                division=_clean_text(cells[0]),
                phase=_phase_label(cells[1]),
                rider_name=_clean_text(cells[2]),
                horse_name=_clean_text(cells[3]),
                score=score,
                source_url=source_url,
                collected_at=collected,
            )
        )

    return sorted(leaders, key=lambda leader: (leader.event_date, leader.event_name, leader.division))


def build_live_score_snapshot(
    leaders: Sequence[LiveLeader],
    *,
    generated_at: datetime | None = None,
    source_url: str = STARTBOX_ARCHIVE_URL,
) -> dict[str, object]:
    """Build a JSON-serializable live-score snapshot from parsed leaders."""

    generated = generated_at or datetime.now(timezone.utc)
    grouped: dict[tuple[str, date, str, str], list[LiveLeader]] = {}
    for leader in leaders:
        key = (leader.event_name, leader.event_date, leader.location, leader.source_url)
        grouped.setdefault(key, []).append(leader)

    events: list[dict[str, object]] = []
    for (event_name, event_date, location, event_url), event_leaders in sorted(
        grouped.items(),
        key=lambda item: (item[0][1], item[0][0]),
        reverse=True,
    ):
        event_leaders = sorted(event_leaders, key=lambda leader: (leader.score, leader.division))
        events.append(
            {
                "event_name": event_name,
                "event_date": event_date.isoformat(),
                "location": location,
                "source_url": event_url,
                "leaders": [_leader_to_mapping(leader) for leader in event_leaders],
            }
        )

    return {
        "version": 1,
        "generated_at": _format_datetime(generated),
        "source": "StartBox/EventingScores",
        "source_url": source_url,
        "summary": {
            "event_count": len(events),
            "leader_count": sum(len(event["leaders"]) for event in events),
        },
        "events": events,
    }


def write_live_score_snapshot(
    leaders: Sequence[LiveLeader],
    output_path: Path | str,
    *,
    generated_at: datetime | None = None,
    source_url: str = STARTBOX_ARCHIVE_URL,
) -> dict[str, object]:
    """Write a live-score snapshot to disk and return the payload."""

    snapshot = build_live_score_snapshot(leaders, generated_at=generated_at, source_url=source_url)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    return snapshot


def _leader_to_mapping(leader: LiveLeader) -> dict[str, object]:
    return {
        "division": leader.division,
        "phase": leader.phase,
        "rider_name": leader.rider_name,
        "horse_name": leader.horse_name,
        "score": leader.score,
        "collected_at": _format_datetime(leader.collected_at),
    }


def _markdown_table_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _parse_archive_date(value: str) -> date | None:
    normalized = value.replace(".", " ")
    match = re.search(r"([A-Za-z]{3,})\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?,\s*(\d{4})", normalized)
    if not match:
        return None
    month_text, start_day, end_day, year = match.groups()
    month = _MONTHS.get(month_text[:3].lower())
    if month is None:
        return None
    return date(int(year), month, int(end_day or start_day))


def _parse_event_date(value: str) -> date | None:
    normalized = value.replace(".", " ")
    match = re.search(r"([A-Za-z]{3,})\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?,\s*(\d{4})", normalized)
    if not match:
        return None
    month_text, start_day, end_day, year = match.groups()
    month = _MONTHS.get(month_text[:3].lower())
    if month is None:
        return None
    return date(int(year), month, int(end_day or start_day))


def _parse_markdown_link(value: str) -> tuple[str, str] | None:
    match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", value)
    if not match:
        return None
    label, url = match.groups()
    return _clean_text(label), url


def _parse_score(value: str) -> float | None:
    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None
    return float(match.group(0))


def _phase_label(value: str) -> str:
    if "Final Scores" in value:
        return "Final"
    if "Stadium" in value:
        return "Stadium"
    if "Scores" in value:
        return "Scores"
    if "Times" in value:
        return "Times"
    return _clean_text(re.sub(r"\[[^\]]+\]\([^)]+\)", "", value)) or "Current"


def _first_match(text: str, pattern: str) -> str | tuple[str, ...] | None:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if match is None:
        return None
    groups = match.groups()
    if len(groups) == 1:
        return groups[0]
    return groups


def _clean_text(value: str) -> str:
    value = re.sub(r"\[[^\]]+\]\([^)]+\)", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a live-score JSON snapshot from StartBox page captures.")
    parser.add_argument("output", help="Path to write the live-score JSON snapshot.")
    parser.add_argument("event_pages", nargs="+", help="Markdown/text captures of StartBox event pages.")
    parser.add_argument("--source-url", default=STARTBOX_ARCHIVE_URL, help="Archive or search URL used for discovery.")
    parser.add_argument("--collected-at", help="ISO timestamp for the page collection time.")
    args = parser.parse_args(argv)

    collected_at = (
        datetime.fromisoformat(args.collected_at.replace("Z", "+00:00")) if args.collected_at else datetime.now(timezone.utc)
    )
    leaders: list[LiveLeader] = []
    for event_page in args.event_pages:
        page_path = Path(event_page)
        leaders.extend(
            parse_startbox_leaders(
                page_path.read_text(encoding="utf-8"),
                source_url=page_path.stem,
                collected_at=collected_at,
            )
        )

    write_live_score_snapshot(leaders, args.output, generated_at=collected_at, source_url=args.source_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
