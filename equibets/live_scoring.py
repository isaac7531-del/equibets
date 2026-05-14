"""Search public event calendars and pull live eventing score leaders."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse


STARTBOX_CALENDAR_URL = "https://eventing.startboxscoring.com/"
STARTBOX_SOURCE_ID = "startbox_scoring"
STARTBOX_SOURCE_PRIORITY = 45


@dataclass(frozen=True)
class CurrentEvent:
    """A current or recently completed event discovered from a public calendar."""

    event_id: str
    name: str
    date_label: str
    start_date: date
    end_date: date
    location: str
    country: str
    status: str
    source_id: str
    source_url: str


@dataclass(frozen=True)
class LiveScore:
    """A division leader from a current event results page."""

    event_id: str
    event_name: str
    event_date: date
    location: str
    country: str
    division: str
    phase: str
    rider_name: str
    horse_name: str
    score: float
    source_id: str
    source_priority: int
    source_url: str
    collected_at: datetime


def refresh_startbox_live_scores(
    *,
    today: date | None = None,
    lookback_days: int = 7,
    lookahead_days: int = 7,
    calendar_url: str = STARTBOX_CALENDAR_URL,
) -> dict[str, object]:
    """Search StartBox's calendar and pull leader scores for current events."""

    today = today or date.today()
    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    calendar_html = _fetch_text(calendar_url)
    events = parse_startbox_calendar(
        calendar_html,
        today=today,
        lookback_days=lookback_days,
        lookahead_days=lookahead_days,
        calendar_url=calendar_url,
    )

    scores: list[LiveScore] = []
    for event in events:
        event_html = _fetch_text(event.source_url)
        scores.extend(parse_startbox_leaders(event_html, event=event, collected_at=collected_at))

    return live_scores_feed(events, scores, collected_at=collected_at)


def live_scores_feed(
    events: Iterable[CurrentEvent],
    scores: Iterable[LiveScore],
    *,
    collected_at: datetime,
) -> dict[str, object]:
    """Serialize live events and leader scores for the web app."""

    return {
        "version": 1,
        "generated_at": _format_datetime(collected_at),
        "source": {
            "id": STARTBOX_SOURCE_ID,
            "name": "StartBox Scoring",
            "url": STARTBOX_CALENDAR_URL,
        },
        "events": [_event_to_mapping(event) for event in events],
        "scores": [_score_to_mapping(score) for score in sorted(scores, key=_score_sort_key)],
    }


def parse_startbox_calendar(
    html: str,
    *,
    today: date,
    lookback_days: int = 7,
    lookahead_days: int = 7,
    calendar_url: str = STARTBOX_CALENDAR_URL,
) -> list[CurrentEvent]:
    """Parse StartBox calendar rows near ``today`` into current events."""

    window_start = today - timedelta(days=lookback_days)
    window_end = today + timedelta(days=lookahead_days)
    events: list[CurrentEvent] = []

    for row in _extract_tables(html):
        if len(row) < 2:
            continue

        date_text = _clean_spaces(row[0].text)
        date_range = _parse_startbox_date_range(date_text, default_year=today.year)
        if date_range is None:
            continue

        start_date, end_date = date_range
        if end_date < window_start or start_date > window_end:
            continue

        link_cell = row[1] if len(row) > 2 else _empty_cell()
        details_cell = row[2] if len(row) > 2 else row[1]
        link_label = _clean_spaces(link_cell.text)
        event_text = _clean_spaces(details_cell.text)
        href = link_cell.links[0] if link_cell.links else None
        if not event_text or href is None:
            continue

        country = _country_from_event_text(event_text)
        location = _location_from_event_text(event_text, country=country)
        name = _event_name_from_event_text(event_text, location=location)
        source_url = urljoin(calendar_url, href)
        events.append(
            CurrentEvent(
                event_id=_event_id_from_url(source_url),
                name=name,
                date_label=date_text,
                start_date=start_date,
                end_date=end_date,
                location=location,
                country=country,
                status=_status_from_link_label(link_label, start_date=start_date, end_date=end_date, today=today),
                source_id=STARTBOX_SOURCE_ID,
                source_url=source_url,
            )
        )

    return sorted(events, key=lambda event: (event.start_date, event.name))


def parse_startbox_leaders(
    html: str,
    *,
    event: CurrentEvent,
    collected_at: datetime,
) -> list[LiveScore]:
    """Parse division leader rows from a StartBox event page."""

    leaders: list[LiveScore] = []
    for row in _extract_tables(html):
        if len(row) < 5:
            continue

        division = _clean_spaces(row[0].text)
        phase = _clean_spaces(row[1].text)
        rider = _clean_spaces(row[2].text)
        horse = _clean_spaces(row[3].text)
        score = _parse_float(row[4].text)
        if not division or not rider or not horse or score is None:
            continue
        if division.lower() in {"division", "rider"}:
            continue
        if not row[1].links:
            continue

        leaders.append(
            LiveScore(
                event_id=event.event_id,
                event_name=event.name,
                event_date=event.start_date,
                location=event.location,
                country=event.country,
                division=division,
                phase=phase,
                rider_name=rider,
                horse_name=horse,
                score=score,
                source_id=event.source_id,
                source_priority=STARTBOX_SOURCE_PRIORITY,
                source_url=urljoin(_directory_url(event.source_url), row[1].links[0]),
                collected_at=collected_at,
            )
        )

    return sorted(leaders, key=lambda score: (score.event_name, score.division, score.score))


def write_live_scores_feed(feed: dict[str, object], path: Path | str) -> None:
    """Write a JSON live-scoring feed with stable formatting."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(feed, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class _Cell:
    text: str
    links: tuple[str, ...] = ()


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[_Cell]]] = []
        self._table_depth = 0
        self._current_table: list[list[_Cell]] | None = None
        self._current_row: list[_Cell] | None = None
        self._current_cell_text: list[str] | None = None
        self._current_cell_links: list[str] | None = None
        self._current_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._current_table = []
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
        elif tag in {"td", "th"} and self._current_row is not None:
            self._current_cell_text = []
            self._current_cell_links = []
        elif tag == "a" and self._current_cell_text is not None:
            href = dict(attrs).get("href")
            self._current_href = href
            if href:
                self._current_cell_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._current_row is not None and self._current_cell_text is not None:
            self._current_row.append(
                _Cell(
                    text=_clean_spaces(" ".join(self._current_cell_text)),
                    links=tuple(self._current_cell_links or ()),
                )
            )
            self._current_cell_text = None
            self._current_cell_links = None
        elif tag == "tr" and self._current_table is not None and self._current_row is not None:
            if self._current_row:
                self._current_table.append(self._current_row)
            self._current_row = None
        elif tag == "a":
            self._current_href = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1
            if self._table_depth == 0 and self._current_table is not None:
                self.tables.extend(self._current_table)
                self._current_table = None

    def handle_data(self, data: str) -> None:
        if self._current_cell_text is not None:
            self._current_cell_text.append(data)


def _extract_tables(html: str) -> list[list[_Cell]]:
    parser = _TableParser()
    parser.feed(html)
    return parser.tables


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Equibets live scoring refresher/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_startbox_date_range(value: str, *, default_year: int) -> tuple[date, date] | None:
    normalized = value.replace("..", " ").replace(".", " ")
    normalized = _clean_spaces(normalized)
    match = re.match(
        r"^(?P<month>[A-Za-z]+)\s+(?P<start>\d{1,2})(?:-(?P<end>\d{1,2}))?(?:,\s*(?P<year>\d{4}))?$",
        normalized,
    )
    if match is None:
        return None

    month = _month_number(match.group("month"))
    if month is None:
        return None

    year = int(match.group("year") or default_year)
    start_day = int(match.group("start"))
    end_day = int(match.group("end") or start_day)
    return date(year, month, start_day), date(year, month, end_day)


def _month_number(month: str) -> int | None:
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
        "sept": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    return months.get(month.lower()[:3])


def _status_from_link_label(link_label: str, *, start_date: date, end_date: date, today: date) -> str:
    normalized = link_label.lower()
    if "result" in normalized:
        return "results"
    if start_date <= today <= end_date:
        return "running"
    if "time" in normalized:
        return "times_posted"
    if "entr" in normalized:
        return "entries_open"
    return "scheduled"


def _event_id_from_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "-")
    return _slug(path or parsed.netloc)


def _event_name_from_event_text(event_text: str, *, location: str) -> str:
    if location and location in event_text:
        return event_text[: event_text.rfind(location)].strip(" -")
    return event_text


def _location_from_event_text(event_text: str, *, country: str) -> str:
    if not country:
        return ""
    suffix = " Canada" if country == "CAN" else " US"
    without_country = event_text[: -len(suffix)] if event_text.endswith(suffix) else event_text
    if "," not in without_country:
        return ""

    before_comma, state = without_country.rsplit(",", 1)
    words = before_comma.split()
    if not words:
        return ""

    city_word_count = 1
    if len(words) >= 2 and words[-2].rstrip(".") in {
        "St",
        "Saint",
        "New",
        "North",
        "South",
        "East",
        "West",
        "Red",
        "Maple",
    }:
        city_word_count = 2

    city = " ".join(words[-city_word_count:])
    return f"{city}, {state.strip()}"


def _country_from_event_text(event_text: str) -> str:
    if event_text.endswith(" Canada"):
        return "CAN"
    if event_text.endswith(" US"):
        return "USA"
    return ""


def _parse_float(value: str) -> float | None:
    normalized = _clean_spaces(value)
    if normalized in {"", "---", "E", "R", "W", "TE"}:
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def _score_sort_key(score: LiveScore) -> tuple[str, str, float, str, str]:
    return (score.event_name, score.division, score.score, score.rider_name, score.horse_name)


def _event_to_mapping(event: CurrentEvent) -> dict[str, object]:
    values = asdict(event)
    values["start_date"] = event.start_date.isoformat()
    values["end_date"] = event.end_date.isoformat()
    return values


def _score_to_mapping(score: LiveScore) -> dict[str, object]:
    values = asdict(score)
    values["event_date"] = score.event_date.isoformat()
    values["collected_at"] = _format_datetime(score.collected_at)
    return values


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        return value.isoformat()
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _directory_url(value: str) -> str:
    return value if value.endswith("/") else f"{value}/"


def _empty_cell() -> _Cell:
    return _Cell("")


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh current StartBox eventing leader scores.")
    parser.add_argument(
        "--output",
        default="data/current_live_scores.json",
        help="Path for the generated JSON feed.",
    )
    parser.add_argument("--today", help="Override today's date as YYYY-MM-DD for reproducible refreshes.")
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--lookahead-days", type=int, default=7)
    args = parser.parse_args()

    today = date.fromisoformat(args.today) if args.today else None
    feed = refresh_startbox_live_scores(
        today=today,
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
    )
    write_live_scores_feed(feed, args.output)


if __name__ == "__main__":
    main()
