"""Live current-event scoring feed for StartBox eventing results."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


STARTBOX_CALENDAR_URL = "http://eventing.startboxscoring.com/"
DEFAULT_OUTPUT_FILE = Path(__file__).resolve().parents[1] / "data" / "live_event_scores.json"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "Chrome/124.0 Safari/537.36"
)

MONTHS = {
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
class Link:
    """A link found in a StartBox table cell."""

    label: str
    url: str


@dataclass(frozen=True)
class CalendarEvent:
    """One current or upcoming StartBox event calendar row."""

    id: str
    name: str
    date_label: str
    start_date: date
    end_date: date
    status: str
    source_url: str | None
    location: str
    country: str

    @property
    def is_results_available(self) -> bool:
        return self.source_url is not None and self.status.lower() in {"results", "times"}


@dataclass(frozen=True)
class LiveDivisionScore:
    """The leader for one division within an active event."""

    division: str
    phase: str
    phase_links: tuple[Link, ...]
    rider_name: str | None
    horse_name: str | None
    score: float | None


@dataclass(frozen=True)
class LiveEventScore:
    """Live leaderboard rows for one current event."""

    event: CalendarEvent
    divisions: tuple[LiveDivisionScore, ...]


class _TableParser(HTMLParser):
    """Minimal table parser for the simple StartBox calendar/leaderboard tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, object]]] = []
        self._current_row: list[dict[str, object]] | None = None
        self._current_cell: dict[str, object] | None = None
        self._current_link: dict[str, object] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "tr":
            self._current_row = []
        elif tag == "td" and self._current_row is not None:
            self._current_cell = {"text": [], "links": []}
        elif tag == "a" and self._current_cell is not None:
            self._current_link = {"href": attributes.get("href") or "", "text": []}
        elif tag == "br" and self._current_cell is not None:
            self._append_text(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_cell is not None and self._current_link is not None:
            links = self._current_cell["links"]
            assert isinstance(links, list)
            href = str(self._current_link["href"])
            label = _clean_text("".join(self._current_link["text"]))
            if href and label:
                links.append({"label": label, "href": href})
            self._current_link = None
        elif tag == "td" and self._current_row is not None and self._current_cell is not None:
            text_parts = self._current_cell["text"]
            assert isinstance(text_parts, list)
            links = self._current_cell["links"]
            assert isinstance(links, list)
            self._current_row.append(
                {
                    "text": _clean_text("".join(str(part) for part in text_parts)),
                    "links": links,
                }
            )
            self._current_cell = None
            self._current_link = None
        elif tag == "tr" and self._current_row is not None:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = None
            self._current_cell = None
            self._current_link = None

    def handle_data(self, data: str) -> None:
        if self._current_cell is not None:
            self._append_text(data)

    def _append_text(self, data: str) -> None:
        text_parts = self._current_cell["text"]
        assert isinstance(text_parts, list)
        text_parts.append(data)
        if self._current_link is not None:
            link_text = self._current_link["text"]
            assert isinstance(link_text, list)
            link_text.append(data)


class _ShowInfoParser(HTMLParser):
    """Extract the show title and date/location subtitle from a StartBox page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.show_name = ""
        self.subtitle = ""
        self._capture: str | None = None
        self._seen_show_name = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "h1" and "showname" in classes:
            self._capture = "show_name"
        elif tag == "h2" and self._seen_show_name and not self.subtitle:
            self._capture = "subtitle"

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2"}:
            if self._capture == "show_name":
                self._seen_show_name = True
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._capture == "show_name":
            self.show_name += data
        elif self._capture == "subtitle":
            self.subtitle += data


def fetch_html(url: str) -> str:
    """Fetch a StartBox page with headers accepted by the public scoreboard."""

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": STARTBOX_CALENDAR_URL,
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", "replace")


def parse_calendar(html: str, *, base_url: str = STARTBOX_CALENDAR_URL) -> list[CalendarEvent]:
    """Parse the StartBox event calendar into structured events."""

    parser = _TableParser()
    parser.feed(html)
    events: list[CalendarEvent] = []

    for row in parser.rows:
        if len(row) < 3:
            continue

        date_label = str(row[0]["text"])
        try:
            start_date, end_date = parse_date_range(date_label)
        except ValueError:
            continue

        status_cell = row[1]
        links = status_cell["links"]
        assert isinstance(links, list)
        status = str(status_cell["text"]) or "Listed"
        source_url = None
        if links:
            first_link = links[0]
            assert isinstance(first_link, dict)
            status = str(first_link["label"])
            source_url = normalize_startbox_url(urljoin(base_url, str(first_link["href"])))

        event_text = str(row[2]["text"])
        name, location, country = split_event_location(event_text)
        events.append(
            CalendarEvent(
                id=_event_id(source_url, name, start_date),
                name=name,
                date_label=date_label,
                start_date=start_date,
                end_date=end_date,
                status=status,
                source_url=source_url,
                location=location,
                country=country,
            )
        )

    return events


def parse_date_range(value: str) -> tuple[date, date]:
    """Parse StartBox labels like ``May 16-17, 2026`` into start/end dates."""

    cleaned = _clean_text(value.replace(".", " "))
    match = re.fullmatch(
        r"(?P<month>[A-Za-z]+)\s+"
        r"(?P<start_day>\d{1,2})"
        r"(?:\s*-\s*(?P<end_day>\d{1,2}))?"
        r",\s*(?P<year>\d{4})",
        cleaned,
    )
    if match is None:
        raise ValueError(f"Unsupported date range: {value}")

    month = MONTHS.get(match.group("month")[:3].lower())
    if month is None:
        raise ValueError(f"Unsupported month in date range: {value}")

    year = int(match.group("year"))
    start_day = int(match.group("start_day"))
    end_day = int(match.group("end_day") or start_day)
    return date(year, month, start_day), date(year, month, end_day)


def current_events(
    events: list[CalendarEvent],
    *,
    as_of: date,
    lookahead_days: int = 0,
) -> list[CalendarEvent]:
    """Return events that are active for the requested date window."""

    window_end = as_of + timedelta(days=lookahead_days)
    return [
        event
        for event in events
        if event.is_results_available
        and event.start_date <= window_end
        and event.end_date >= as_of
    ]


def parse_live_event_page(html: str, calendar_event: CalendarEvent) -> LiveEventScore:
    """Parse a current event page and return division leaders."""

    show_parser = _ShowInfoParser()
    show_parser.feed(html)
    event = _calendar_event_with_show_details(calendar_event, show_parser)

    table_parser = _TableParser()
    table_parser.feed(html)

    divisions: list[LiveDivisionScore] = []
    for row in table_parser.rows:
        if len(row) < 2:
            continue

        division = str(row[0]["text"])
        if not division or division.lower() in {"division", "rider"}:
            continue

        phase = str(row[1]["text"])
        phase_links = tuple(
            Link(
                label=str(link["label"]),
                url=urljoin(event.source_url or STARTBOX_CALENDAR_URL, str(link["href"])),
            )
            for link in row[1]["links"]
            if isinstance(link, dict)
        )

        rider_name = str(row[2]["text"]) if len(row) > 2 else None
        horse_name = str(row[3]["text"]) if len(row) > 3 else None
        score = parse_score(str(row[4]["text"])) if len(row) > 4 else None

        divisions.append(
            LiveDivisionScore(
                division=division,
                phase=phase,
                phase_links=phase_links,
                rider_name=rider_name or None,
                horse_name=horse_name or None,
                score=score,
            )
        )

    return LiveEventScore(event=event, divisions=tuple(divisions))


def refresh_live_scores(
    *,
    as_of: date | None = None,
    generated_at: datetime | None = None,
    calendar_url: str = STARTBOX_CALENDAR_URL,
    fetcher: Callable[[str], str] = fetch_html,
    lookahead_days: int = 0,
    max_events: int | None = None,
) -> dict[str, object]:
    """Fetch the current StartBox calendar and live leaderboards."""

    generated_at = generated_at or datetime.now(timezone.utc)
    as_of = as_of or generated_at.date()
    calendar_html = fetcher(calendar_url)
    events = current_events(
        parse_calendar(calendar_html, base_url=calendar_url),
        as_of=as_of,
        lookahead_days=lookahead_days,
    )
    if max_events is not None:
        events = events[:max_events]

    live_events: list[LiveEventScore] = []
    for event in events:
        if event.source_url is None:
            continue
        live_events.append(parse_live_event_page(fetcher(event.source_url), event))

    return serialize_feed(
        live_events,
        as_of=as_of,
        generated_at=generated_at,
        calendar_url=calendar_url,
    )


def serialize_feed(
    live_events: list[LiveEventScore],
    *,
    as_of: date,
    generated_at: datetime,
    calendar_url: str = STARTBOX_CALENDAR_URL,
) -> dict[str, object]:
    """Convert live score dataclasses into the JSON contract used by the app."""

    return {
        "version": 1,
        "generated_at": generated_at.astimezone(timezone.utc).isoformat(),
        "as_of_date": as_of.isoformat(),
        "source_id": "startbox_current_events",
        "source_name": "StartBox current eventing scores",
        "source_url": calendar_url,
        "events": [
            {
                "id": live_event.event.id,
                "name": live_event.event.name,
                "date_label": live_event.event.date_label,
                "start_date": live_event.event.start_date.isoformat(),
                "end_date": live_event.event.end_date.isoformat(),
                "location": live_event.event.location,
                "country": live_event.event.country,
                "status": live_event.event.status,
                "source_url": live_event.event.source_url,
                "divisions": [
                    {
                        "division": division.division,
                        "phase": division.phase,
                        "phase_links": [
                            {"label": link.label, "url": link.url}
                            for link in division.phase_links
                        ],
                        "leader": (
                            {
                                "rider": division.rider_name,
                                "horse": division.horse_name,
                                "score": division.score,
                            }
                            if division.rider_name and division.horse_name and division.score is not None
                            else None
                        ),
                    }
                    for division in live_event.divisions
                ],
            }
            for live_event in live_events
        ],
    }


def write_live_scores(feed: dict[str, object], path: Path | str = DEFAULT_OUTPUT_FILE) -> None:
    """Write the live score feed with stable formatting."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(feed, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_score(value: str) -> float | None:
    """Parse a leaderboard score while ignoring status-only cells."""

    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else None


def normalize_startbox_url(url: str) -> str:
    """Route eventingscores.com links through the StartBox host that serves HTTPS."""

    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    if netloc == "eventingscores.com":
        parsed = parsed._replace(scheme="https", netloc="eventing.startboxscoring.com")
    elif netloc == "eventing.startboxscoring.com":
        parsed = parsed._replace(scheme="https")

    normalized = urlunparse(parsed)
    if not normalized.endswith("/") and "." not in Path(parsed.path).name:
        normalized += "/"
    return normalized


def split_event_location(value: str) -> tuple[str, str, str]:
    """Best-effort split of calendar text into event name, location, and country."""

    cleaned = _clean_text(value)
    tokens = cleaned.split()
    country = ""
    if tokens and re.fullmatch(r"[A-Z]{2,3}", tokens[-1]):
        country = tokens.pop()
    location_tokens: list[str] = []
    while tokens:
        token = tokens[-1]
        location_tokens.append(tokens.pop())
        if "," in token:
            break

    location_tokens.reverse()
    location = " ".join(location_tokens).strip(" ,")
    name = " ".join(tokens).strip(" ,") or cleaned
    return name, location, country


def _calendar_event_with_show_details(
    calendar_event: CalendarEvent,
    show_parser: _ShowInfoParser,
) -> CalendarEvent:
    show_name = _clean_text(unescape(show_parser.show_name)) or calendar_event.name
    subtitle = _clean_text(unescape(show_parser.subtitle))
    location = calendar_event.location
    if " - " in subtitle:
        _, location = subtitle.split(" - ", 1)

    return CalendarEvent(
        id=calendar_event.id,
        name=show_name,
        date_label=calendar_event.date_label,
        start_date=calendar_event.start_date,
        end_date=calendar_event.end_date,
        status=calendar_event.status,
        source_url=calendar_event.source_url,
        location=location,
        country=calendar_event.country,
    )


def _event_id(source_url: str | None, name: str, start_date: date) -> str:
    if source_url:
        parsed = urlparse(source_url)
        return "startbox-" + _slug(parsed.path)
    return f"startbox-{start_date.isoformat()}-{_slug(name)}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value)).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh current StartBox eventing leaderboards.")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None, help="Date to treat as current.")
    parser.add_argument("--lookahead-days", type=int, default=0, help="Include events starting within this many days.")
    parser.add_argument("--max-events", type=int, default=None, help="Limit fetched current events.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_FILE, help="JSON feed path to write.")
    args = parser.parse_args(argv)

    feed = refresh_live_scores(
        as_of=args.as_of,
        lookahead_days=args.lookahead_days,
        max_events=args.max_events,
    )
    write_live_scores(feed, args.output)
    print(f"Wrote {len(feed['events'])} current events to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
