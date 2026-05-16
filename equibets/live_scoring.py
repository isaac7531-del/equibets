"""Current-event live scoring discovery and snapshot helpers."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


STARTBOX_SOURCE_ID = "startbox_scoring"
STARTBOX_SOURCE_NAME = "StartBox Scoring current event calendar"
STARTBOX_CALENDAR_URL = "https://eventing.startboxscoring.com/"
SNAPSHOT_FILE = Path(__file__).resolve().parents[1] / "data" / "current_event_live_scores.json"


@dataclass(frozen=True)
class LiveDivision:
    """A live event division and its current published phase state."""

    name: str
    phase_status: str
    entry_status_url: str | None = None
    times_url: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "phase_status": self.phase_status,
            "entry_status_url": self.entry_status_url,
            "times_url": self.times_url,
        }


@dataclass(frozen=True)
class CurrentEvent:
    """A current or near-current event found from a live scoring source."""

    id: str
    source_id: str
    source_name: str
    name: str
    date_label: str
    starts_on: date
    ends_on: date
    location: str
    country: str
    status: str
    score_status: str
    result_url: str
    divisions: tuple[LiveDivision, ...] = ()

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "name": self.name,
            "date_label": self.date_label,
            "starts_on": self.starts_on.isoformat(),
            "ends_on": self.ends_on.isoformat(),
            "location": self.location,
            "country": self.country,
            "status": self.status,
            "score_status": self.score_status,
            "result_url": self.result_url,
            "divisions": [division.to_mapping() for division in self.divisions],
            "entries": [],
        }


def parse_startbox_calendar(
    content: str,
    *,
    as_of: date | None = None,
    base_url: str = STARTBOX_CALENDAR_URL,
) -> list[CurrentEvent]:
    """Parse StartBox's event calendar into normalized current-event records."""

    effective_date = as_of or date.today()
    rows = _markdown_calendar_rows(content)
    if not rows:
        rows = _html_table_rows(content)

    events: list[CurrentEvent] = []
    for date_label, link_label, link_url, description in rows:
        parsed_dates = _parse_date_label(date_label)
        if parsed_dates is None or not link_url:
            continue

        starts_on, ends_on = parsed_dates
        name, location, country = _split_event_description(description)
        result_url = urljoin(base_url, link_url)
        events.append(
            CurrentEvent(
                id=_event_id(STARTBOX_SOURCE_ID, result_url, name),
                source_id=STARTBOX_SOURCE_ID,
                source_name=STARTBOX_SOURCE_NAME,
                name=name,
                date_label=date_label,
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


def parse_startbox_event_page(content: str, *, base_url: str = STARTBOX_CALENDAR_URL) -> tuple[LiveDivision, ...]:
    """Parse division phase/timing rows from a StartBox event page."""

    rows = _markdown_division_rows(content)
    if not rows:
        rows = _html_table_rows(content)

    divisions: list[LiveDivision] = []
    for name, phase_cell, *_ in rows:
        if name.lower() in {"division", "phase"} or not name.strip("- "):
            continue

        links = {
            label.lower(): urljoin(base_url, url)
            for label, url in _markdown_links(phase_cell)
        }
        phase_status = _strip_markdown_links(phase_cell).strip(" -")
        divisions.append(
            LiveDivision(
                name=name.strip(),
                phase_status=phase_status,
                entry_status_url=links.get("entry status"),
                times_url=links.get("times"),
            )
        )

    return tuple(divisions)


def build_live_snapshot(
    events: list[CurrentEvent],
    *,
    generated_at: datetime | None = None,
    source_url: str = STARTBOX_CALENDAR_URL,
    source_errors: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Build the JSON payload consumed by the website live-scoring panel."""

    timestamp = generated_at or datetime.now(timezone.utc)
    snapshot: dict[str, object] = {
        "version": 1,
        "generated_at": _isoformat_utc(timestamp),
        "sources": [
            {
                "id": STARTBOX_SOURCE_ID,
                "name": STARTBOX_SOURCE_NAME,
                "url": source_url,
            }
        ],
        "events": [event.to_mapping() for event in events],
    }
    if source_errors:
        snapshot["source_errors"] = source_errors
    return snapshot


def refresh_startbox_live_snapshot(
    output_path: Path | str = SNAPSHOT_FILE,
    *,
    calendar_url: str = STARTBOX_CALENDAR_URL,
    as_of: date | None = None,
    lookback_days: int = 1,
    lookahead_days: int = 7,
    timeout_seconds: int = 20,
) -> dict[str, object]:
    """Fetch StartBox current events and write a live-scoring snapshot."""

    effective_date = as_of or date.today()
    calendar_content = _fetch_url(calendar_url, timeout_seconds=timeout_seconds)
    events = [
        event
        for event in parse_startbox_calendar(calendar_content, as_of=effective_date, base_url=calendar_url)
        if _is_within_window(event, effective_date, lookback_days, lookahead_days)
    ]

    enriched_events: list[CurrentEvent] = []
    source_errors: list[dict[str, str]] = []
    for event in events:
        try:
            page_content = _fetch_url(event.result_url, timeout_seconds=timeout_seconds)
        except Exception as exc:  # pragma: no cover - exercised by real source behavior
            source_errors.append(
                {
                    "event_id": event.id,
                    "url": event.result_url,
                    "message": str(exc),
                }
            )
            enriched_events.append(event)
            continue

        enriched_events.append(
            replace(
                event,
                divisions=parse_startbox_event_page(page_content, base_url=event.result_url),
            )
        )

    snapshot = build_live_snapshot(
        enriched_events,
        source_url=calendar_url,
        source_errors=source_errors,
    )
    _write_snapshot(snapshot, output_path)
    return snapshot


def load_live_snapshot(path: Path | str = SNAPSHOT_FILE) -> dict[str, object]:
    """Load a generated live-scoring snapshot."""

    with Path(path).open(encoding="utf-8") as snapshot_file:
        payload = json.load(snapshot_file)
    if not isinstance(payload, dict):
        raise ValueError("Live scoring snapshot must be a JSON object")
    return payload


def _fetch_url(url: str, *, timeout_seconds: int) -> str:
    request = Request(
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
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def _write_snapshot(snapshot: dict[str, object], output_path: Path | str) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as snapshot_file:
        json.dump(snapshot, snapshot_file, indent=2)
        snapshot_file.write("\n")


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


def _html_table_rows(content: str) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for row_match in re.finditer(r"<tr[^>]*>(?P<row>.*?)</tr>", content, flags=re.IGNORECASE | re.DOTALL):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_match.group("row"), flags=re.IGNORECASE | re.DOTALL)
        if len(cells) < 2:
            continue

        first = _strip_tags(cells[0])
        second_label, second_url = _first_html_link(cells[1])
        if len(cells) >= 3:
            third = _strip_tags(cells[2])
            rows.append((first, second_label, second_url, third))
        else:
            rows.append((first, _strip_tags(cells[1]), second_url, ""))
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
        r"(?P<name>.+?)\s+(?P<location>[A-Z][A-Za-z .'-]+,\s*[A-Z]{2}\s+(?P<country>US|Canada))",
        normalized,
    )
    if match:
        return match.group("name"), match.group("location"), match.group("country")

    country_match = re.search(r"\b(?P<country>US|Canada)\b$", normalized)
    return normalized, "", country_match.group("country") if country_match else ""


def _event_status(starts_on: date, ends_on: date, as_of: date) -> str:
    if starts_on <= as_of <= ends_on:
        return "live"
    if ends_on < as_of:
        return "completed"
    return "upcoming"


def _is_within_window(event: CurrentEvent, as_of: date, lookback_days: int, lookahead_days: int) -> bool:
    earliest = as_of - timedelta(days=lookback_days)
    latest = as_of + timedelta(days=lookahead_days)
    return event.ends_on >= earliest and event.starts_on <= latest


def _event_id(source_id: str, result_url: str, name: str) -> str:
    parsed = urlparse(result_url)
    path_slug = _slug(parsed.path.strip("/").replace("/", "-"))
    if path_slug:
        return f"{source_id}-{path_slug}"
    return f"{source_id}-{_slug(name)}"


def _markdown_links(content: str) -> list[tuple[str, str]]:
    return re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)


def _first_markdown_link(content: str) -> tuple[str, str]:
    links = _markdown_links(content)
    return links[0] if links else ("", "")


def _first_html_link(content: str) -> tuple[str, str]:
    match = re.search(
        r"<a[^>]+href=[\"'](?P<href>[^\"']+)[\"'][^>]*>(?P<label>.*?)</a>",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return _strip_tags(content), ""
    return _strip_tags(match.group("label")), match.group("href")


def _strip_markdown_links(content: str) -> str:
    return re.sub(r"\[[^\]]+\]\([^)]+\)", "", content)


def _strip_tags(content: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", content)
    return " ".join(without_tags.replace("&nbsp;", " ").split())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the current-event live scoring snapshot.")
    parser.add_argument("--output", default=str(SNAPSHOT_FILE), help="Path to write the snapshot JSON.")
    parser.add_argument("--calendar-url", default=STARTBOX_CALENDAR_URL, help="StartBox calendar URL to fetch.")
    parser.add_argument("--as-of", help="Current date in YYYY-MM-DD format. Defaults to today.")
    parser.add_argument("--lookback-days", type=int, default=1, help="Completed-event lookback window.")
    parser.add_argument("--lookahead-days", type=int, default=7, help="Upcoming-event lookahead window.")
    parser.add_argument("--timeout-seconds", type=int, default=20, help="HTTP timeout per source request.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    snapshot = refresh_startbox_live_snapshot(
        args.output,
        calendar_url=args.calendar_url,
        as_of=as_of,
        lookback_days=args.lookback_days,
        lookahead_days=args.lookahead_days,
        timeout_seconds=args.timeout_seconds,
    )
    print(f"Wrote {len(snapshot['events'])} current events to {args.output}")


if __name__ == "__main__":
    main()
