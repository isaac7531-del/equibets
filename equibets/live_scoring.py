"""Current-event live scoring feed helpers."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen


STARTBOX_SOURCE_ID = "startbox_scoring"
STARTBOX_SOURCE_NAME = "StartBox/EventingScores"
STARTBOX_SOURCE_PRIORITY = 45
STARTBOX_CALENDAR_URL = "https://eventing.startboxscoring.com/archives.php?Year={year}"
DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "current_event_feed.json"

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
_ROW_PATTERN = re.compile(
    r"\|\s*(?P<date>[^|]+?)\s*\|\s*"
    r"\[(?P<label>[^\]]+)\]\((?P<url>[^)]+)\)\s*\|\s*"
    r"(?P<description>[^|]+?)\s*\|"
)
_LOCATION_PATTERN = re.compile(
    r"^(?P<event>.+)\s+(?P<city>[^,]+),\s*(?P<region>[A-Z]{2})\s+(?P<country>US|Canada)$"
)


@dataclass(frozen=True)
class CurrentEvent:
    """One public current-event scoring link."""

    id: str
    source_id: str
    source_name: str
    source_priority: int
    event_name: str
    start_date: date
    end_date: date
    location: str
    country: str
    status: str
    status_label: str
    scoring_url: str
    last_observed_at: datetime
    notes: str
    divisions: tuple[dict[str, str], ...] = field(default_factory=tuple)

    def to_mapping(self) -> dict[str, object]:
        """Serialize the event for the browser feed."""

        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_priority": self.source_priority,
            "event_name": self.event_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "location": self.location,
            "country": self.country,
            "status": self.status,
            "status_label": self.status_label,
            "scoring_url": self.scoring_url,
            "last_observed_at": self.last_observed_at.isoformat().replace("+00:00", "Z"),
            "notes": self.notes,
            "divisions": list(self.divisions),
        }


def parse_startbox_calendar(
    calendar_text: str,
    *,
    observed_at: datetime,
    days_back: int = 7,
    days_forward: int = 14,
) -> list[CurrentEvent]:
    """Extract current, recent, and upcoming scoring links from a StartBox calendar."""

    observed_date = observed_at.date()
    window_start = observed_date - timedelta(days=days_back)
    window_end = observed_date + timedelta(days=days_forward)
    events: list[CurrentEvent] = []

    for match in _ROW_PATTERN.finditer(calendar_text):
        start_date, end_date = _parse_date_range(match.group("date"))
        if end_date < window_start or start_date > window_end:
            continue

        label = match.group("label").strip()
        description = _clean_text(match.group("description"))
        event_name, location, country = _split_description(description)
        status = _status_from_label(label, start_date, end_date, observed_date)
        event = CurrentEvent(
            id=f"startbox-{_slug(event_name)}-{start_date.isoformat()}",
            source_id=STARTBOX_SOURCE_ID,
            source_name=STARTBOX_SOURCE_NAME,
            source_priority=STARTBOX_SOURCE_PRIORITY,
            event_name=event_name,
            start_date=start_date,
            end_date=end_date,
            location=location,
            country=country,
            status=status,
            status_label=label,
            scoring_url=match.group("url").strip(),
            last_observed_at=observed_at,
            notes=_notes_for_status(status),
        )
        events.append(event)

    return sorted(events, key=lambda event: (event.start_date, event.event_name))


def build_feed(
    events: list[CurrentEvent],
    *,
    generated_at: datetime,
    source_url: str,
) -> dict[str, object]:
    """Build the JSON payload consumed by the website."""

    if events:
        coverage_from = min(event.start_date for event in events).isoformat()
        coverage_through = max(event.end_date for event in events).isoformat()
    else:
        coverage_from = generated_at.date().isoformat()
        coverage_through = generated_at.date().isoformat()

    return {
        "version": 1,
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "coverage_window": {
            "from": coverage_from,
            "through": coverage_through,
        },
        "sources": [
            {
                "id": STARTBOX_SOURCE_ID,
                "name": "StartBox/EventingScores calendar",
                "url": source_url,
                "observed": "Current calendar rows parsed from public StartBox eventing scoring listings.",
            }
        ],
        "events": [event.to_mapping() for event in events],
    }


def refresh_startbox_feed(
    *,
    output_path: Path | str = DATA_FILE,
    observed_at: datetime | None = None,
    year: int | None = None,
) -> dict[str, object]:
    """Fetch StartBox eventing calendar data and write the current-event feed."""

    generated_at = observed_at or datetime.now(UTC)
    calendar_year = year or generated_at.year
    source_url = STARTBOX_CALENDAR_URL.format(year=calendar_year)
    calendar_text = _fetch_text(source_url)
    events = parse_startbox_calendar(calendar_text, observed_at=generated_at)
    feed = build_feed(events, generated_at=generated_at, source_url=source_url)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(feed, indent=2) + "\n", encoding="utf-8")
    return feed


def _fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "User-Agent": "Equibets live scoring feed (+https://github.com/isaac7531-del/equibets)",
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_date_range(value: str) -> tuple[date, date]:
    normalized = _clean_text(value.replace(".", " "))
    match = re.match(
        r"^(?P<month>[A-Za-z]+)\s+(?P<start>\d{1,2})(?:-(?P<end>\d{1,2}))?,\s*(?P<year>\d{4})$",
        normalized,
    )
    if match is None:
        raise ValueError(f"Unsupported StartBox date range: {value}")

    month = _MONTHS[match.group("month").lower()[:3]]
    year = int(match.group("year"))
    start_day = int(match.group("start"))
    end_day = int(match.group("end") or start_day)
    return date(year, month, start_day), date(year, month, end_day)


def _split_description(description: str) -> tuple[str, str, str]:
    match = _LOCATION_PATTERN.match(description)
    if match is None:
        return description, "Unknown", "Unknown"

    country = "USA" if match.group("country") == "US" else "Canada"
    return (
        match.group("event").strip(),
        f"{match.group('city').strip()}, {match.group('region')}",
        country,
    )


def _status_from_label(label: str, start_date: date, end_date: date, observed_date: date) -> str:
    normalized = label.lower()
    if normalized == "results":
        if start_date <= observed_date <= end_date:
            return "live_results"
        return "recent_results"
    if normalized == "times":
        return "ride_times"
    if normalized == "entries":
        return "entries"
    return "listed"


def _notes_for_status(status: str) -> str:
    return {
        "live_results": "Results are marked available for an event that is currently running.",
        "recent_results": "Recent results remain inside the current-event scoring window.",
        "ride_times": "Ride times are posted and should be checked for results as the event starts.",
        "entries": "Entries are posted for an upcoming event in the current scoring window.",
    }.get(status, "Calendar listing is available in the current scoring window.")


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the Equibets current-event live scoring feed.")
    parser.add_argument("--output", default=str(DATA_FILE), help="Path to write the JSON feed.")
    parser.add_argument("--year", type=int, default=None, help="Calendar year to fetch.")
    args = parser.parse_args()

    feed = refresh_startbox_feed(output_path=args.output, year=args.year)
    print(f"Wrote {len(feed['events'])} current-event scoring links to {args.output}")


if __name__ == "__main__":
    _main()
