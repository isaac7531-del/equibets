"""Collect current eventing live-score snapshots from public scoreboards."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "current_event_live_scores.json"
DEFAULT_ARCHIVE_URL = "http://eventing.startboxscoring.com/archives.php?Year={year}"
SOURCE_ID = "startbox_eventing"

_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)")
_DECIMAL_SCORE_RE = re.compile(r"(?P<score>\d+\.\d+%?)\s*$")
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True)
class ArchiveEvent:
    """One event row discovered in the public StartBox eventing archive."""

    name: str
    date_label: str
    start_date: date
    end_date: date
    status: str
    source_url: str | None
    link_label: str | None


@dataclass(frozen=True)
class DivisionLeader:
    """Current leader for one division within an event scoreboard."""

    division: str
    phase: str
    leader_name: str
    score_text: str
    score: float | None
    results_url: str | None = None
    rider_name: str | None = None
    horse_name: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "division": self.division,
            "phase": self.phase,
            "leader_name": self.leader_name,
            "rider_name": self.rider_name,
            "horse_name": self.horse_name,
            "score_text": self.score_text,
            "score": self.score,
            "results_url": self.results_url,
        }


@dataclass(frozen=True)
class EventLiveScore:
    """Normalized live-score state for a single event."""

    event_name: str
    date_label: str
    start_date: date
    end_date: date
    location: str
    status: str
    source_id: str
    source_url: str | None
    leaders: tuple[DivisionLeader, ...]
    fetch_error: str | None = None

    def to_mapping(self) -> dict[str, object]:
        return {
            "event_name": self.event_name,
            "date_label": self.date_label,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "location": self.location,
            "status": self.status,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "leaders": [leader.to_mapping() for leader in self.leaders],
            "fetch_error": self.fetch_error,
        }


def parse_startbox_archive(markdown: str) -> list[ArchiveEvent]:
    """Parse StartBox archive markdown into dated event rows."""

    events: list[ArchiveEvent] = []
    section: str | None = None

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if "### Open/Currently Running" in line:
            section = "current"
            continue
        if "### Completed Events" in line:
            section = "completed"
            continue
        if "### Future Events" in line:
            section = "upcoming"
            continue
        if section is None or not line.startswith("|"):
            continue

        cells = _split_markdown_row(line)
        if len(cells) < 3 or cells[0].startswith("---") or cells[0].startswith("###"):
            continue

        try:
            start_date, end_date = parse_event_date_range(cells[0])
        except ValueError:
            continue

        link_label, source_url = _first_markdown_link(cells[1])
        events.append(
            ArchiveEvent(
                name=_clean_archive_event_name(cells[2]),
                date_label=_clean_date_label(cells[0]),
                start_date=start_date,
                end_date=end_date,
                status=section,
                source_url=source_url,
                link_label=link_label,
            )
        )

    return events


def parse_startbox_event_page(
    markdown: str,
    archive_event: ArchiveEvent,
    *,
    source_url: str | None = None,
    leader_limit: int | None = None,
) -> EventLiveScore:
    """Parse a StartBox event page into current division leaders."""

    event_name = _event_name(markdown, archive_event.name)
    date_label, location = _event_date_location(markdown, archive_event)
    leaders = tuple(_parse_leaders(markdown))
    if leader_limit is not None:
        leaders = leaders[:leader_limit]

    return EventLiveScore(
        event_name=event_name,
        date_label=date_label,
        start_date=archive_event.start_date,
        end_date=archive_event.end_date,
        location=location,
        status=archive_event.status,
        source_id=SOURCE_ID,
        source_url=source_url or archive_event.source_url,
        leaders=leaders,
    )


def collect_live_scores(
    *,
    as_of: date | None = None,
    collected_at: datetime | None = None,
    archive_url: str | None = None,
    event_limit: int = 8,
    leader_limit: int = 8,
) -> dict[str, object]:
    """Fetch the current archive and event pages, returning JSON-ready data."""

    as_of = as_of or date.today()
    collected_at = collected_at or datetime.now(timezone.utc)
    archive_url = archive_url or DEFAULT_ARCHIVE_URL.format(year=as_of.year)
    archive_markdown, fetched_archive_url = fetch_public_markdown(archive_url)
    archive_events = parse_startbox_archive(archive_markdown)

    live_events: list[EventLiveScore] = []
    for archive_event in _select_events(archive_events, as_of, event_limit):
        if not archive_event.source_url:
            live_events.append(_event_without_scores(archive_event))
            continue

        try:
            event_markdown, fetched_event_url = fetch_public_markdown(archive_event.source_url)
            live_events.append(
                parse_startbox_event_page(
                    event_markdown,
                    archive_event,
                    source_url=fetched_event_url,
                    leader_limit=leader_limit,
                )
            )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            live_events.append(_event_without_scores(archive_event, fetch_error=str(exc)))

    return {
        "version": 1,
        "collected_at": collected_at.isoformat().replace("+00:00", "Z"),
        "as_of_date": as_of.isoformat(),
        "source_id": SOURCE_ID,
        "source_name": "StartBox Eventing live scores",
        "archive_url": archive_url,
        "fetched_archive_url": fetched_archive_url,
        "events": [event.to_mapping() for event in live_events],
    }


def fetch_public_markdown(url: str, *, timeout: int = 25) -> tuple[str, str]:
    """Fetch a public page, using a reader fallback for sites that block bots."""

    errors: list[str] = []
    for target_url in _url_candidates(url):
        for candidate_url in (target_url, *_reader_urls(target_url)):
            try:
                text = _fetch_text(candidate_url, timeout=timeout)
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                errors.append(f"{candidate_url}: {exc}")
                continue
            if _is_blocked_response(text):
                errors.append(f"{candidate_url}: blocked response")
                continue
            return text, target_url

    raise URLError("; ".join(errors) or f"unable to fetch {url}")


def parse_event_date_range(label: str) -> tuple[date, date]:
    """Parse archive date labels such as ``May.. 16-17, 2026``."""

    clean_label = _clean_date_label(label)
    match = re.search(
        r"(?P<month>[A-Za-z]+)\s+(?P<start>\d{1,2})(?:-(?P<end>\d{1,2}))?,\s*(?P<year>\d{4})",
        clean_label,
    )
    if not match:
        raise ValueError(f"Unsupported event date label: {label}")

    month = _MONTHS[match.group("month").lower()]
    year = int(match.group("year"))
    start_day = int(match.group("start"))
    end_day = int(match.group("end") or start_day)
    return date(year, month, start_day), date(year, month, end_day)


def write_snapshot(snapshot: dict[str, object], path: Path | str = DATA_FILE) -> None:
    """Write a live-score snapshot using stable formatting."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(snapshot, output_file, indent=2, sort_keys=True)
        output_file.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect current eventing live-score data.")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    parser.add_argument("--collected-at", type=_parse_datetime, default=None)
    parser.add_argument("--archive-url", default=None)
    parser.add_argument("--event-limit", type=int, default=8)
    parser.add_argument("--leader-limit", type=int, default=8)
    parser.add_argument("--output", type=Path, default=DATA_FILE)
    args = parser.parse_args(argv)

    snapshot = collect_live_scores(
        as_of=args.as_of,
        collected_at=args.collected_at,
        archive_url=args.archive_url,
        event_limit=args.event_limit,
        leader_limit=args.leader_limit,
    )
    write_snapshot(snapshot, args.output)
    return 0


def _parse_datetime(value: str) -> datetime:
    normalized_value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized_value)


def _select_events(
    events: list[ArchiveEvent],
    as_of: date,
    limit: int,
) -> list[ArchiveEvent]:
    current_results = [
        event
        for event in events
        if event.status == "current" and event.link_label == "Results"
    ]
    current_entries = [
        event
        for event in events
        if event.status == "current" and event.link_label != "Results"
    ]
    completed_results = sorted(
        (
            event
            for event in events
            if event.status == "completed"
            and event.link_label == "Results"
            and event.start_date <= as_of
        ),
        key=lambda event: (event.start_date, event.name),
        reverse=True,
    )
    upcoming_entries = sorted(
        (event for event in events if event.status == "upcoming" and event.start_date >= as_of),
        key=lambda event: (event.start_date, event.name),
    )

    selected = current_results + completed_results + current_entries + upcoming_entries
    unique_events: list[ArchiveEvent] = []
    seen: set[tuple[str, date]] = set()
    for event in selected:
        key = (event.name, event.start_date)
        if key in seen:
            continue
        seen.add(key)
        unique_events.append(event)
        if len(unique_events) == limit:
            break
    return unique_events


def _event_without_scores(
    archive_event: ArchiveEvent,
    *,
    fetch_error: str | None = None,
) -> EventLiveScore:
    return EventLiveScore(
        event_name=archive_event.name,
        date_label=archive_event.date_label,
        start_date=archive_event.start_date,
        end_date=archive_event.end_date,
        location="",
        status=archive_event.status,
        source_id=SOURCE_ID,
        source_url=archive_event.source_url,
        leaders=(),
        fetch_error=fetch_error,
    )


def _parse_leaders(markdown: str) -> list[DivisionLeader]:
    table_leaders = _parse_table_leaders(markdown)
    if table_leaders:
        return table_leaders

    leaders: list[DivisionLeader] = []
    pending: tuple[str, str, str | None] | None = None

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line or line in {"Division Phase Current Leader", "Rider Horse Score"}:
            continue
        if "Thoroughbred Incentive Program" in line:
            break

        if "](" in line:
            division = line.split("[", 1)[0].strip()
            if not division or division.lower() in {"title:", "url source:"}:
                continue

            links = _markdown_links(line)
            phase = _phase_from_links([label for label, _url in links])
            results_url = _results_url(links)
            link_matches = list(_LINK_RE.finditer(line))
            remainder = line[link_matches[-1].end() :].strip() if link_matches else ""
            pending = (division, phase, results_url)
            if _DECIMAL_SCORE_RE.search(remainder):
                leaders.append(_leader_from_text(division, phase, remainder, results_url))
                pending = None
            continue

        if pending and _DECIMAL_SCORE_RE.search(line):
            division, phase, results_url = pending
            leaders.append(_leader_from_text(division, phase, _strip_schedule_prefix(line), results_url))
            pending = None

    return _dedupe_leaders(leaders)


def _parse_table_leaders(markdown: str) -> list[DivisionLeader]:
    leaders: list[DivisionLeader] = []
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue
        cells = _split_markdown_row(line)
        if len(cells) < 5 or cells[0] in {"Division", "Rider", "---"}:
            continue
        score_text = cells[4].strip()
        if not _DECIMAL_SCORE_RE.search(score_text):
            continue

        phase_label, results_url = _first_markdown_link(cells[1])
        rider_name = cells[2].strip()
        horse_name = cells[3].strip()
        leaders.append(
            DivisionLeader(
                division=_strip_markdown(cells[0]),
                phase=phase_label or _strip_markdown(cells[1]),
                leader_name=f"{rider_name} / {horse_name}",
                rider_name=rider_name,
                horse_name=horse_name,
                score_text=score_text,
                score=_score_number(score_text),
                results_url=results_url,
            )
        )

    return _dedupe_leaders(leaders)


def _leader_from_text(
    division: str,
    phase: str,
    leader_text: str,
    results_url: str | None,
) -> DivisionLeader:
    score_match = _DECIMAL_SCORE_RE.search(leader_text)
    if not score_match:
        raise ValueError(f"Leader line does not include a decimal score: {leader_text}")

    score_text = score_match.group("score")
    leader_name = leader_text[: score_match.start()].strip(" .")
    leader_name = re.sub(r"^Ring\s+\d+\s+", "", leader_name.lstrip(") ."))
    return DivisionLeader(
        division=_strip_markdown(division),
        phase=phase,
        leader_name=leader_name,
        score_text=score_text,
        score=_score_number(score_text),
        results_url=results_url,
    )


def _dedupe_leaders(leaders: list[DivisionLeader]) -> list[DivisionLeader]:
    unique: list[DivisionLeader] = []
    seen: set[tuple[str, str, str]] = set()
    for leader in leaders:
        key = (leader.division, leader.leader_name, leader.score_text)
        if key in seen:
            continue
        seen.add(key)
        unique.append(leader)
    return unique


def _event_name(markdown: str, fallback: str) -> str:
    title = fallback
    for line in markdown.splitlines():
        if line.startswith("Title:"):
            title = line.removeprefix("Title:").strip()
            title = re.sub(r"^Results for\s+", "", title)
            break

    for line in markdown.splitlines():
        if not line.startswith("## "):
            continue
        heading = line.removeprefix("## ").strip()
        if _is_date_location_heading(heading):
            continue
        if heading and heading != "Online Scoring System":
            return heading
    return title


def _event_date_location(markdown: str, archive_event: ArchiveEvent) -> tuple[str, str]:
    for line in markdown.splitlines():
        if not line.startswith("## "):
            continue
        heading = line.removeprefix("## ").strip()
        if not _is_date_location_heading(heading):
            continue
        date_label, _separator, location = heading.partition(" - ")
        return date_label, location
    return archive_event.date_label, ""


def _is_date_location_heading(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]{3,}\s+\d{1,2}", value))


def _strip_schedule_prefix(line: str) -> str:
    return re.sub(
        r"^(?:Dressage|Stadium|Cross Country|Jumper|XC):.*?(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.",
        "",
        line,
    ).strip()


def _phase_from_links(labels: list[str]) -> str:
    score_labels = [label for label in labels if "Score" in label]
    if score_labels:
        return score_labels[-1]
    return labels[-1] if labels else "Scores"


def _results_url(links: list[tuple[str, str]]) -> str | None:
    for label, url in reversed(links):
        if "Score" in label:
            return url
    return links[-1][1] if links else None


def _markdown_links(value: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2)) for match in _LINK_RE.finditer(value)]


def _first_markdown_link(value: str) -> tuple[str | None, str | None]:
    links = _markdown_links(value)
    return links[0] if links else (None, None)


def _split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _clean_archive_event_name(value: str) -> str:
    without_images = re.split(r"!?\[!\[Image|\[!\[Image|!\[Image", value, maxsplit=1)[0]
    return _strip_markdown(without_images).strip()


def _strip_markdown(value: str) -> str:
    value = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def _clean_date_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.replace(".", " ")).strip()


def _score_number(score_text: str) -> float | None:
    if score_text.endswith("%"):
        return None
    return float(score_text)


def _fetch_text(url: str, *, timeout: int) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 EquibetsLiveScores/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _reader_urls(url: str) -> tuple[str, str]:
    return (
        f"https://r.jina.ai/http://{url}",
        f"https://r.jina.ai/http://r.jina.ai/http://{url}",
    )


def _url_candidates(url: str) -> list[str]:
    candidates = [url]
    parsed_url = urlparse(url)
    if parsed_url.netloc == "eventingscores.com":
        candidates.append(urlunparse(parsed_url._replace(netloc="eventing.startboxscoring.com")))
    return candidates


def _is_blocked_response(text: str) -> bool:
    return "403 Forbidden" in text or "Target URL returned error 403" in text


if __name__ == "__main__":
    raise SystemExit(main())
