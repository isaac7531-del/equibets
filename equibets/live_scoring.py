"""Live-score discovery and snapshot helpers for current eventing results."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Sequence
from urllib.parse import urljoin
from urllib.request import Request, urlopen


STARTBOX_ARCHIVE_URL = "https://eventing.startboxscoring.com/archives.php?Year={year}"
STARTBOX_USER_AGENT = "Mozilla/5.0 Equibets live scoring refresh"
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

    rows = _StartboxArchiveParser.parse(text) if "<table" in text.lower() else []
    rows.extend(_markdown_rows(text))

    events: list[CurrentEvent] = []
    for cells in rows:
        if len(cells) < 3:
            continue

        event_date = _parse_archive_date(cells[0].text)
        if event_date is None:
            continue
        link = cells[1].first_link()
        if link is None:
            link = _parse_markdown_link(cells[1].text)
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
                event_name=_clean_text(cells[2].text),
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

    parsed_page = _StartboxEventPageParser.parse(text) if "<table" in text.lower() else None
    event_name = parsed_page.event_name if parsed_page is not None else _first_match(text, r"^#\s+(.+?)\s*$")
    event_details = parsed_page.event_details if parsed_page is not None else _first_match(text, r"^##\s+(.+?)\s+-\s+(.+?)\s*$")
    if event_name is None or event_details is None:
        return []

    event_date_text, location = event_details
    event_date = _parse_event_date(event_date_text)
    if event_date is None:
        return []

    collected = collected_at or datetime.now(timezone.utc)
    leaders: list[LiveLeader] = []
    rows = parsed_page.leader_rows if parsed_page is not None else _markdown_rows(text)
    for cells in rows:
        if len(cells) < 5 or cells[0].lower() in {"division", "rider", "---"}:
            continue

        score = _parse_score(cells[4].text)
        if score is None:
            continue

        leaders.append(
            LiveLeader(
                event_name=_clean_text(event_name),
                event_date=event_date,
                location=_clean_text(location),
                division=_clean_text(cells[0].text),
                phase=_phase_label(cells[1].text),
                rider_name=_clean_text(cells[2].text),
                horse_name=_clean_text(cells[3].text),
                score=score,
                source_url=source_url,
                collected_at=collected,
            )
        )

    return sorted(leaders, key=lambda leader: (leader.event_date, leader.event_name, leader.division))


def refresh_startbox_live_scores(
    output_path: Path | str,
    *,
    as_of: date | None = None,
    generated_at: datetime | None = None,
    lookback_days: int = 7,
    lookahead_days: int = 3,
    max_events: int = 12,
) -> dict[str, object]:
    """Fetch current StartBox events, pull leaders, and write a live snapshot."""

    collected_at = generated_at or datetime.now(timezone.utc)
    refresh_date = as_of or collected_at.date()
    archive_url = STARTBOX_ARCHIVE_URL.format(year=refresh_date.year)
    archive_text = _fetch_text(archive_url)
    current_events = parse_startbox_archive(
        archive_text,
        as_of=refresh_date,
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
    )

    leaders: list[LiveLeader] = []
    for event in current_events[:max_events]:
        event_text = _fetch_text(event.source_url)
        leaders.extend(parse_startbox_leaders(event_text, source_url=event.source_url, collected_at=collected_at))

    return write_live_score_snapshot(leaders, output_path, generated_at=collected_at, source_url=archive_url)


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


@dataclass(frozen=True)
class _ParsedCell:
    text: str
    links: tuple[tuple[str, str], ...] = ()

    def lower(self) -> str:
        return self.text.lower()

    def first_link(self) -> tuple[str, str] | None:
        return self.links[0] if self.links else None


def _markdown_rows(text: str) -> list[list[_ParsedCell]]:
    return [[_ParsedCell(cell) for cell in _markdown_table_cells(line)] for line in text.splitlines()]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[_ParsedCell]] = []
        self._row: list[_ParsedCell] | None = None
        self._cell_text: list[str] | None = None
        self._cell_links: list[tuple[str, str]] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_text = []
            self._cell_links = []
        elif tag == "a" and self._cell_text is not None:
            self._anchor_href = dict(attrs).get("href")
            self._anchor_text = []
        elif tag == "br" and self._cell_text is not None:
            self._cell_text.append(" ")

    def handle_data(self, data: str) -> None:
        if self._cell_text is None:
            return
        self._cell_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._anchor_href is not None:
            label = _clean_text("".join(self._anchor_text))
            if label:
                self._cell_links.append((label, self._anchor_href))
            self._anchor_href = None
            self._anchor_text = []
        elif tag in {"td", "th"} and self._row is not None and self._cell_text is not None:
            self._row.append(_ParsedCell(_clean_text(" ".join(self._cell_text)), tuple(self._cell_links)))
            self._cell_text = None
            self._cell_links = []
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


class _StartboxArchiveParser(_TableParser):
    @classmethod
    def parse(cls, text: str) -> list[list[_ParsedCell]]:
        parser = cls()
        parser.feed(text)
        rows: list[list[_ParsedCell]] = []
        for row in parser.rows:
            if len(row) < 3:
                continue
            rows.append(
                [
                    row[0],
                    _ParsedCell(row[1].text, tuple((label, urljoin(STARTBOX_ARCHIVE_URL, url)) for label, url in row[1].links)),
                    row[2],
                ]
            )
        return rows


class _StartboxEventPageParser(_TableParser):
    def __init__(self) -> None:
        super().__init__()
        self.event_name: str | None = None
        self.event_details: tuple[str, str] | None = None
        self._capture_heading: str | None = None
        self._heading_text: list[str] = []

    @property
    def leader_rows(self) -> list[list[_ParsedCell]]:
        return [row for row in self.rows if len(row) >= 5]

    @classmethod
    def parse(cls, text: str) -> "_StartboxEventPageParser":
        parser = cls()
        parser.feed(text)
        return parser

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = dict(attrs)
        class_names = set((attrs_by_name.get("class") or "").split())
        if tag == "h1" and "showname" in class_names:
            self._capture_heading = "event_name"
            self._heading_text = []
        elif tag == "h2" and self.event_name is not None and self.event_details is None:
            self._capture_heading = "event_details"
            self._heading_text = []
        super().handle_starttag(tag, attrs)

    def handle_data(self, data: str) -> None:
        if self._capture_heading is not None:
            self._heading_text.append(data)
        super().handle_data(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2"} and self._capture_heading is not None:
            text = _clean_text(" ".join(self._heading_text))
            if self._capture_heading == "event_name":
                self.event_name = text
            elif self._capture_heading == "event_details":
                match = re.match(r"(.+?)\s+-\s+(.+)", text)
                if match:
                    self.event_details = (match.group(1), match.group(2))
            self._capture_heading = None
            self._heading_text = []
        super().handle_endtag(tag)


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


def _fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": STARTBOX_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a live-score JSON snapshot from current StartBox event pages.")
    parser.add_argument("output", help="Path to write the live-score JSON snapshot.")
    parser.add_argument("event_pages", nargs="*", help="Optional Markdown/text captures of StartBox event pages.")
    parser.add_argument("--source-url", default=STARTBOX_ARCHIVE_URL, help="Archive or search URL used for discovery.")
    parser.add_argument("--collected-at", help="ISO timestamp for the page collection time.")
    parser.add_argument("--as-of", help="Refresh date for current-event discovery, formatted YYYY-MM-DD.")
    parser.add_argument("--lookback-days", type=int, default=7, help="Past event window to include from the archive.")
    parser.add_argument("--lookahead-days", type=int, default=3, help="Upcoming event window to include from the archive.")
    parser.add_argument("--max-events", type=int, default=12, help="Maximum current-event pages to fetch.")
    args = parser.parse_args(argv)

    collected_at = (
        datetime.fromisoformat(args.collected_at.replace("Z", "+00:00")) if args.collected_at else datetime.now(timezone.utc)
    )
    as_of = date.fromisoformat(args.as_of) if args.as_of else collected_at.date()
    if not args.event_pages:
        refresh_startbox_live_scores(
            args.output,
            as_of=as_of,
            generated_at=collected_at,
            lookback_days=args.lookback_days,
            lookahead_days=args.lookahead_days,
            max_events=args.max_events,
        )
        return 0

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

    source_url = args.source_url.format(year=as_of.year)
    write_live_score_snapshot(leaders, args.output, generated_at=collected_at, source_url=source_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
