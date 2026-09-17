"""Collect live eventing scores from EventingScores result boards."""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from equibets.live_scores import (
    build_live_score_payload,
    current_event_window,
    write_live_score_payload,
)
from equibets.rechenstelle import merge_into_store
from equibets.results import EventingResult


SOURCE_ID = "eventingscores"
SOURCE_PRIORITY = 8
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
START_DAY_RE = re.compile(
    r"\b(?:mon|tue|wed|thu|fri|sat|sun)\b",
    re.IGNORECASE,
)
PLACE_RE = re.compile(r"^\d+(?:st|nd|rd|th)$", re.IGNORECASE)
PERCENT_RE = re.compile(r"%")
LEADING_NUMBER_RE = re.compile(r"^(-?\d+(?:\.\d+)?)")

# Agria Blenheim Palace International, 17–20 Sep 2026.
# Public EventingScores boards: CCI4*-L (69243) and 8/9YO CCI4*-S (69244).
# Rows without a numeric dressage score (start-time tokens, empty judge-%
# columns, horse-inspection flags) are skipped.
BLENHEIM_SEP_2026 = (
    {
        "url": "https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69244.html?eventid=2990",
        "event_name": "Blenheim · CCI4*-S 8/9YO",
        "level": "CCI4*-S",
        "event_date": date(2026, 9, 17),
        "country": "GBR",
    },
    {
        "url": "https://www.eventingscores.co.uk/uploads/events/2990/results_2990_69243.html?eventid=2990",
        "event_name": "Blenheim · CCI4*-L",
        "level": "CCI4*-L",
        "event_date": date(2026, 9, 17),
        "country": "GBR",
    },
)


@dataclass(frozen=True)
class EventingScoresBoard:
    """One EventingScores results table to ingest."""

    url: str
    event_name: str
    level: str
    event_date: date
    country: str


class _ResultsTableParser(HTMLParser):
    """Extract header labels and data rows from an EventingScores table."""

    def __init__(self) -> None:
        super().__init__()
        self.header_cells: list[str] = []
        self.rows: list[list[dict[str, str]]] = []
        self._in_thead = False
        self._in_header_row = False
        self._header_cell: str | None = None
        self._in_row = False
        self._row: list[dict[str, str]] | None = None
        self._cell: dict[str, str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "thead":
            self._in_thead = True
            return
        if self._in_thead and tag == "tr" and not self.header_cells:
            self._in_header_row = True
            return
        if self._in_header_row and tag in {"th", "td"}:
            self._header_cell = ""
            return
        if tag == "tr" and not self._in_thead:
            self._in_row = True
            self._row = []
            return
        if not self._in_row:
            return
        if tag == "td":
            self._cell = {
                "text": "",
                "horse": attributes.get("data-horse", ""),
                "rider": attributes.get("data-rider", ""),
                "number": attributes.get("data-number", ""),
            }
            return
        if self._cell is not None and tag == "img" and not self._cell.get("flag"):
            flag = attributes.get("alt") or ""
            if flag:
                self._cell["flag"] = flag

    def handle_endtag(self, tag: str) -> None:
        if tag == "thead":
            self._in_thead = False
            self._in_header_row = False
            return
        if tag == "tr" and self._in_header_row:
            self._in_header_row = False
            return
        if tag in {"th", "td"} and self._header_cell is not None:
            label = _clean_text(self._header_cell)
            self.header_cells.append(label)
            self._header_cell = None
            return
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append(self._cell)
            self._cell = None
            return
        if tag == "tr" and self._in_row and self._row is not None:
            if any(_clean_text(cell.get("text")) or cell.get("horse") or cell.get("rider") for cell in self._row):
                self.rows.append(self._row)
            self._row = None
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._header_cell is not None:
            self._header_cell += data
            return
        if self._cell is not None:
            self._cell["text"] = (self._cell.get("text") or "") + data


def fetch_results_html(url: str, *, timeout: float = 30.0) -> str:
    """Fetch an EventingScores results page as text."""

    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc


def parse_leaderboard_results(
    html: str,
    *,
    board: EventingScoresBoard,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse EventingScores HTML into EventingResult rows with numeric dressage."""

    parser = _ResultsTableParser()
    parser.feed(html)
    collected = collected_at or datetime.now(timezone.utc)
    columns = _column_index(parser.header_cells)
    results: list[EventingResult] = []

    for row in parser.rows:
        rider_name = _cell_attr(row, "rider") or _cell_text(row, columns.get("rider"))
        horse_name = _cell_attr(row, "horse") or _cell_text(row, columns.get("horse"))
        start_no = _cell_attr(row, "number") or _cell_text(row, columns.get("no"))
        dressage = _parse_penalty(_cell_text(row, columns.get("dressage")))
        if not rider_name or not horse_name or dressage is None:
            continue

        show_jumping = _parse_penalty(_cell_text(row, columns.get("sj"))) or 0.0
        xc_jump = _parse_penalty(_cell_text(row, columns.get("xcj"))) or 0.0
        xc_time = _parse_penalty(_cell_text(row, columns.get("xct"))) or 0.0
        record_id = _record_id(board.url, board.level, start_no, rider_name, horse_name)

        results.append(
            EventingResult(
                source_id=SOURCE_ID,
                source_record_id=record_id,
                source_priority=SOURCE_PRIORITY,
                rider_name=rider_name,
                horse_name=horse_name,
                event_name=board.event_name,
                event_date=board.event_date,
                level=board.level,
                country=board.country,
                dressage_score=dressage,
                show_jumping_penalties=show_jumping,
                cross_country_jump_penalties=xc_jump,
                cross_country_time_penalties=xc_time,
                collected_at=collected,
                is_user_entered=False,
            )
        )
    return results


def blenheim_sep_2026_boards() -> list[EventingScoresBoard]:
    """Return the Blenheim September 2026 EventingScores boards."""

    return [EventingScoresBoard(**item) for item in BLENHEIM_SEP_2026]


def collect_boards(
    boards: Sequence[EventingScoresBoard],
    *,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Fetch and parse each EventingScores board."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    results: list[EventingResult] = []
    for board in boards:
        html = fetch_results_html(board.url)
        results.extend(parse_leaderboard_results(html, board=board, collected_at=collected))
    return results


def _column_index(header_cells: Sequence[str]) -> dict[str, int]:
    normalized = [_clean_text(cell).casefold() for cell in header_cells]
    mapping: dict[str, int] = {}
    aliases = {
        "no": ("no", "no."),
        "rider": ("rider",),
        "horse": ("horse",),
        "dressage": ("dressage",),
        "sj": ("sj",),
        "xct": ("xct",),
        "xcj": ("xcj",),
    }
    for key, names in aliases.items():
        for index, label in enumerate(normalized):
            if label in names:
                mapping[key] = index
                break
    return mapping


def _cell_text(row: Sequence[dict[str, str]], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return _clean_text(row[index].get("text"))


def _cell_attr(row: Sequence[dict[str, str]], key: str) -> str:
    for cell in row:
        value = _clean_text(cell.get(key))
        if value:
            return value
    return ""


def _parse_penalty(value: str | None) -> float | None:
    """Parse a score/penalty cell, ignoring start times, places, and judge %."""

    text = _clean_text(value)
    if not text or PERCENT_RE.search(text) or START_DAY_RE.search(text) or PLACE_RE.match(text):
        return None
    match = LEADING_NUMBER_RE.match(text.replace(",", "."))
    if not match:
        return None
    return float(match.group(1))


def _clean_text(value: str | None) -> str:
    text = html_lib.unescape(value or "")
    text = text.replace("\xa0", " ")
    return " ".join(text.split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"eventingscores:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect EventingScores live eventing scores")
    parser.add_argument(
        "--blenheim-2026",
        action="store_true",
        help="Pull the Blenheim September 2026 EventingScores boards",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    boards: list[EventingScoresBoard] = []
    if args.blenheim_2026:
        boards.extend(blenheim_sep_2026_boards())
    if not boards:
        raise SystemExit("Specify --blenheim-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_boards(boards, collected_at=collected_at)
    print(
        "EventingScores collect complete: "
        f"boards={len(boards)}, results_collected={len(results)}"
    )
    if args.dry_run:
        return 0

    merged = merge_into_store(args.output, results)
    start_date, end_date = current_event_window()
    live_payload = build_live_score_payload(merged, start_date=start_date, end_date=end_date)
    write_live_score_payload(live_payload, args.live_output)
    print(
        "Live scoring snapshot written: "
        f"events={live_payload['event_count']}, "
        f"results={live_payload['result_count']}, "
        f"output={args.live_output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
