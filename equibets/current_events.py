"""Current event discovery and live-scoring feed generation."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


STARTBOX_EVENTING_URL = "https://eventing.startboxscoring.com/"
DEFAULT_OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "current_event_scores.json"
STARTBOX_SOURCE_ID = "startbox_eventing"
STARTBOX_SOURCE_PRIORITY = 55

_DATE_RANGE_RE = re.compile(
    r"^(?P<month>[A-Z][a-z]{2}) (?P<start_day>\d{1,2})"
    r"(?:-(?P<end_day>\d{1,2}))?, (?P<year>\d{4})$",
)
_MARKDOWN_ROW_RE = re.compile(
    r"^\|\s*(?P<date>[^|]+?)\s*\|\s*"
    r"\[(?P<label>[^\]]+)\]\((?P<url>[^)]+)\)\s*\|\s*"
    r"(?P<summary>[^|]+?)\s*\|",
    re.MULTILINE,
)


@dataclass(frozen=True)
class CurrentEventScore:
    """A current event with an external live-scoring entry point."""

    source_id: str
    source_event_id: str
    source_priority: int
    event_name: str
    start_date: date
    end_date: date
    country: str
    status: str
    scoring_url: str
    collected_at: datetime

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> "CurrentEventScore":
        return cls(
            source_id=_required_str(values, "source_id"),
            source_event_id=_required_str(values, "source_event_id"),
            source_priority=_required_int(values, "source_priority"),
            event_name=_required_str(values, "event_name"),
            start_date=date.fromisoformat(_required_str(values, "start_date")),
            end_date=date.fromisoformat(_required_str(values, "end_date")),
            country=_required_str(values, "country"),
            status=_required_status(values, "status"),
            scoring_url=_required_str(values, "scoring_url"),
            collected_at=datetime.fromisoformat(_required_str(values, "collected_at")),
        )

    @property
    def is_resulted(self) -> bool:
        return self.status == "results"

    def to_mapping(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "source_event_id": self.source_event_id,
            "source_priority": self.source_priority,
            "event_name": self.event_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "country": self.country,
            "status": self.status,
            "scoring_url": self.scoring_url,
            "collected_at": self.collected_at.isoformat(),
        }


def load_current_event_scores(path: Path | str = DEFAULT_OUTPUT_FILE) -> list[CurrentEventScore]:
    """Load current live-scoring entries from JSON."""

    with Path(path).open(encoding="utf-8") as scores_file:
        payload = json.load(scores_file)

    return [CurrentEventScore.from_mapping(item) for item in payload["events"]]


def parse_startbox_calendar(
    calendar_payload: str,
    *,
    collected_at: datetime,
    source_priority: int = STARTBOX_SOURCE_PRIORITY,
) -> list[CurrentEventScore]:
    """Parse StartBox calendar HTML or markdown into current-event records."""

    rows = _parse_calendar_rows(calendar_payload)
    events: list[CurrentEventScore] = []
    for row_date, label, url, summary in rows:
        start_date, end_date = _parse_date_range(row_date)
        events.append(
            CurrentEventScore(
                source_id=STARTBOX_SOURCE_ID,
                source_event_id=_source_event_id(url),
                source_priority=source_priority,
                event_name=_clean(summary),
                start_date=start_date,
                end_date=end_date,
                country=_country_from_summary(summary),
                status=_status_from_label(label),
                scoring_url=url,
                collected_at=collected_at,
            ),
        )

    return events


def select_live_scoring_events(
    events: list[CurrentEventScore],
    *,
    today: date,
    lookback_days: int = 7,
    lookahead_days: int = 21,
) -> list[CurrentEventScore]:
    """Return events close enough to today to matter for live scoring."""

    earliest = today - timedelta(days=lookback_days)
    latest = today + timedelta(days=lookahead_days)
    selected = [
        event
        for event in events
        if event.end_date >= earliest and event.start_date <= latest
    ]

    return sorted(selected, key=lambda event: (_live_sort_key(event, today), event.event_name))


def build_current_event_feed(
    calendar_payload: str,
    *,
    source_url: str = STARTBOX_EVENTING_URL,
    collected_at: datetime | None = None,
    today: date | None = None,
    lookback_days: int = 7,
    lookahead_days: int = 21,
) -> dict[str, object]:
    """Build the JSON feed used by the website's current-events panel."""

    collected_at = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    today = today or collected_at.date()
    parsed_events = parse_startbox_calendar(calendar_payload, collected_at=collected_at)
    current_events = select_live_scoring_events(
        parsed_events,
        today=today,
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
    )

    return {
        "version": 1,
        "source_id": STARTBOX_SOURCE_ID,
        "source_url": source_url,
        "collected_at": collected_at.isoformat(),
        "lookback_days": lookback_days,
        "lookahead_days": lookahead_days,
        "events": [event.to_mapping() for event in current_events],
    }


def fetch_calendar_payload(source_url: str = STARTBOX_EVENTING_URL) -> str:
    """Fetch the configured public eventing calendar."""

    request = Request(
        source_url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def write_current_event_feed(
    output_path: Path | str = DEFAULT_OUTPUT_FILE,
    *,
    source_url: str = STARTBOX_EVENTING_URL,
    today: date | None = None,
    lookback_days: int = 7,
    lookahead_days: int = 21,
) -> dict[str, object]:
    """Fetch current events and write the website JSON feed."""

    payload = fetch_calendar_payload(source_url)
    feed = build_current_event_feed(
        payload,
        source_url=source_url,
        today=today,
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(feed, indent=2) + "\n", encoding="utf-8")
    return feed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull current eventing live-scoring links.")
    parser.add_argument("--source-url", default=STARTBOX_EVENTING_URL)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_FILE))
    parser.add_argument("--today", help="Override today's date as YYYY-MM-DD for repeatable pulls.")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--lookahead-days", type=int, default=21)
    args = parser.parse_args(argv)

    today = date.fromisoformat(args.today) if args.today else None
    write_current_event_feed(
        args.output,
        source_url=args.source_url,
        today=today,
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
    )
    return 0


class _CalendarTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[tuple[str, str, str, str]] = []
        self._in_row = False
        self._in_cell = False
        self._cell_text: list[str] = []
        self._cell_href: str | None = None
        self._cells: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._in_row = True
            self._cells = []
        elif self._in_row and tag == "td":
            self._in_cell = True
            self._cell_text = []
            self._cell_href = None
        elif self._in_cell and tag == "a":
            self._cell_href = dict(attrs).get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            self._cells.append((_clean(" ".join(self._cell_text)), self._cell_href))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            self._append_row()
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_text.append(data)

    def _append_row(self) -> None:
        if len(self._cells) < 3:
            return

        row_date = self._cells[0][0]
        label = self._cells[1][0]
        url = self._cells[1][1]
        summary = self._cells[2][0]
        if row_date and label and url and summary:
            self.rows.append((row_date, label, url, summary))


def _parse_calendar_rows(payload: str) -> list[tuple[str, str, str, str]]:
    if "<tr" in payload.lower():
        parser = _CalendarTableParser()
        parser.feed(payload)
        return parser.rows

    return [
        (
            _clean(match.group("date")),
            _clean(match.group("label")),
            _clean(match.group("url")),
            _clean(match.group("summary")),
        )
        for match in _MARKDOWN_ROW_RE.finditer(payload)
    ]


def _parse_date_range(value: str) -> tuple[date, date]:
    match = _DATE_RANGE_RE.match(value)
    if not match:
        raise ValueError(f"Unsupported event date range: {value}")

    month = datetime.strptime(match.group("month"), "%b").month
    year = int(match.group("year"))
    start_day = int(match.group("start_day"))
    end_day = int(match.group("end_day") or start_day)
    return date(year, month, start_day), date(year, month, end_day)


def _live_sort_key(event: CurrentEventScore, today: date) -> tuple[int, date, int]:
    if event.start_date <= today <= event.end_date:
        state_rank = 0
    elif event.status == "ride_times":
        state_rank = 1
    elif event.status == "results":
        state_rank = 2
    else:
        state_rank = 3

    return (state_rank, event.start_date, event.source_priority)


def _status_from_label(label: str) -> str:
    normalized = label.strip().lower()
    if normalized == "results":
        return "results"
    if normalized == "times":
        return "ride_times"
    return "entries"


def _country_from_summary(summary: str) -> str:
    match = re.search(r"\b([A-Z]{2,3})$", summary.strip())
    return match.group(1) if match else "unknown"


def _source_event_id(url: str) -> str:
    parsed = urlparse(url)
    path_slug = re.sub(r"[^a-z0-9]+", "-", parsed.path.lower()).strip("-")
    return f"startbox-{path_slug}"


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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


def _required_status(values: dict[str, object], key: str) -> str:
    value = _required_str(values, key)
    if value not in {"entries", "ride_times", "results"}:
        raise ValueError(f"{key} must be entries, ride_times, or results")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
