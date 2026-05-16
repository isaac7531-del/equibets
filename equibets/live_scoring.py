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
    scores_url: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "name": self.name,
            "phase_status": self.phase_status,
            "entry_status_url": self.entry_status_url,
            "times_url": self.times_url,
            "scores_url": self.scores_url,
        }


@dataclass(frozen=True)
class LiveScoreEntry:
    """One scored live leaderboard row from a current event."""

    id: str
    rider_name: str
    horse_name: str
    division: str
    status: str
    score: dict[str, float | None] | None

    def to_mapping(self) -> dict[str, object]:
        return {
            "id": self.id,
            "riderName": self.rider_name,
            "horseName": self.horse_name,
            "division": self.division,
            "status": self.status,
            "score": self.score,
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
    entries: tuple[LiveScoreEntry, ...] = ()

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
            "entries": [entry.to_mapping() for entry in self.entries],
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
        rows = _html_calendar_rows(content)

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

    normalized_base_url = _directory_base_url(base_url)
    divisions: list[LiveDivision] = []
    for name, phase_cell in _markdown_division_rows(content):
        if name.lower() in {"division", "phase", "rider"} or not name.strip("- "):
            continue

        links = {
            label.lower(): urljoin(normalized_base_url, url)
            for label, url in _markdown_links(phase_cell)
        }
        phase_status = _strip_markdown_links(phase_cell).strip(" -")
        divisions.append(
            LiveDivision(
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
            LiveDivision(
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
) -> tuple[LiveScoreEntry, ...]:
    """Parse current leader rows from a StartBox event division listing."""

    normalized_base_url = _directory_base_url(base_url)
    entries: list[LiveScoreEntry] = []
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
            LiveScoreEntry(
                id=_entry_id(division, rider_name, horse_name),
                rider_name=rider_name,
                horse_name=horse_name,
                division=division,
                status=_score_status_from_links(links),
                score={
                    "dressagePenalties": None,
                    "showJumpingPenalties": None,
                    "crossCountryJumpPenalties": None,
                    "crossCountryTimePenalties": None,
                    "totalPenalties": total_penalties,
                },
            )
        )

    return tuple(entries)


def parse_startbox_scores_page(content: str, *, division: str, status: str = "scores") -> tuple[LiveScoreEntry, ...]:
    """Parse all scored rows from a StartBox division score page."""

    entries: list[LiveScoreEntry] = []
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
        row_status = _row_status(row, status)
        score: dict[str, float | None] | None = None
        if dressage_penalties is not None or total_penalties is not None:
            score = {
                "dressagePenalties": dressage_penalties,
                "showJumpingPenalties": _difference_or_none(total_penalties, dressage_penalties),
                "crossCountryJumpPenalties": None,
                "crossCountryTimePenalties": None,
                "totalPenalties": total_penalties,
            }

        entries.append(
            LiveScoreEntry(
                id=_entry_id(division, rider_name, horse_name, start_number),
                rider_name=rider_name,
                horse_name=horse_name,
                division=division,
                status=row_status,
                score=score,
            )
        )

    return tuple(entries)


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

        divisions = parse_startbox_event_page(page_content, base_url=event.result_url)
        leader_entries = parse_startbox_event_leaders(page_content, base_url=event.result_url)
        leader_statuses = {entry.division: entry.status for entry in leader_entries}
        score_entries: list[LiveScoreEntry] = []
        scored_divisions: set[str] = set()
        for division in divisions:
            if not division.scores_url:
                continue

            try:
                scores_content = _fetch_url(division.scores_url, timeout_seconds=timeout_seconds)
            except Exception as exc:  # pragma: no cover - exercised by real source behavior
                source_errors.append(
                    {
                        "event_id": event.id,
                        "url": division.scores_url,
                        "message": str(exc),
                    }
                )
                continue

            entries = parse_startbox_scores_page(
                scores_content,
                division=division.name,
                status=leader_statuses.get(division.name, _score_status_from_url(division.scores_url)),
            )
            if entries:
                scored_divisions.add(division.name)
                score_entries.extend(entries)

        score_entries.extend(entry for entry in leader_entries if entry.division not in scored_divisions)
        enriched_events.append(
            replace(
                event,
                divisions=divisions,
                entries=tuple(_deduplicate_entries(score_entries)),
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


def _deduplicate_entries(entries: list[LiveScoreEntry]) -> list[LiveScoreEntry]:
    deduplicated: dict[str, LiveScoreEntry] = {}
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
