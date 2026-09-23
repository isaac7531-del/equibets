"""Collect published CCI results from public USEA results pages."""

from __future__ import annotations

import argparse
import hashlib
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


SOURCE_ID = "usea"
SOURCE_PRIORITY = 50
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
RESULTS_URL = "https://useventing.com/events-competitions/resources/results/item?event={event_id}"
LEVEL_RE = re.compile(r"CCI\s*(\d)\s*\*?\s*-\s*([SL])", re.IGNORECASE)
NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

# Plantation Field International, 17–20 Sep 2026 (USEA 19088).
# The calendar page is event info only. Numeric finals are the public results
# board. Ingest CCI* rows with a numeric total; skip W/E/R/RF/MR status rows
# and national HT classes.
PLANTATION_SEP_2026 = {
    "event_id": "19088",
    "event_title": "Plantation Field",
    "event_date": date(2026, 9, 17),
    "country": "USA",
}


@dataclass(frozen=True)
class UseaEvent:
    """One USEA results page to ingest."""

    event_id: str
    event_title: str
    event_date: date
    country: str

    @property
    def url(self) -> str:
        return RESULTS_URL.format(event_id=self.event_id)


class _ResultsPageParser(HTMLParser):
    """Extract CCI section headings and competitor rows from a USEA results page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.sections: list[dict[str, object]] = []
        self._skip_depth = 0
        self._stack: list[str] = []
        self._heading_open = False
        self._heading_text = ""
        self._current_heading = ""
        self._row: dict[str, object] | None = None
        self._row_depth = 0
        self._in_first_col = False
        self._link_text: str | None = None
        self._cell_text: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self._skip_depth += 1
        if self._skip_depth:
            return

        attributes = {key: value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        self._stack.append(tag)
        if tag == "h6" and "results_heading" in classes:
            self._heading_open = True
            self._heading_text = ""
            return
        if tag == "div" and "other_row" in classes:
            self._row = {"links": [], "cells": []}
            self._row_depth = len(self._stack)
            return
        if self._row is None:
            return
        if tag == "div" and "first_col" in classes:
            self._in_first_col = True
            return
        if tag == "div" and ({"other_col", "last_col"} & classes):
            self._cell_text = ""
            return
        if tag == "a" and self._in_first_col:
            self._link_text = ""

    def handle_endtag(self, tag: str) -> None:
        if self._skip_depth:
            if tag in {"script", "style"}:
                self._skip_depth -= 1
            return
        if tag == "h6" and self._heading_open:
            self._current_heading = _clean_text(self._heading_text)
            self._heading_open = False
        if tag == "a" and self._link_text is not None and self._row is not None:
            links = self._row["links"]
            assert isinstance(links, list)
            links.append(_clean_text(self._link_text))
            self._link_text = None
        if tag == "div" and self._cell_text is not None and self._row is not None:
            cells = self._row["cells"]
            assert isinstance(cells, list)
            cells.append(_clean_text(self._cell_text))
            self._cell_text = None
        if tag == "div" and self._in_first_col:
            self._in_first_col = False
        if (
            tag == "div"
            and self._row is not None
            and len(self._stack) == self._row_depth
        ):
            self.sections.append(
                {
                    "heading": self._current_heading,
                    "links": list(self._row["links"]),  # type: ignore[arg-type]
                    "cells": list(self._row["cells"]),  # type: ignore[arg-type]
                }
            )
            self._row = None
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._heading_open:
            self._heading_text += data
        if self._link_text is not None:
            self._link_text += data
        elif self._cell_text is not None:
            self._cell_text += data


def results_url(event_id: str) -> str:
    """Return the public USEA results URL for an event id."""

    return RESULTS_URL.format(event_id=event_id)


def fetch_results_html(url: str, *, timeout: float = 30.0) -> str:
    """Fetch a USEA results page as text."""

    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html"})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc


def parse_results_html(
    html: str,
    *,
    event: UseaEvent,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse a USEA results page into CCI rows with a numeric finishing total."""

    parser = _ResultsPageParser()
    parser.feed(html)
    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for section in parser.sections:
        level = _level_from_heading(str(section["heading"]))
        if level is None:
            continue
        parsed = _parse_row(section, event=event, level=level, collected_at=collected)
        if parsed is not None:
            results.append(parsed)
    return results


def plantation_sep_2026_event() -> UseaEvent:
    """Return the Plantation Field September 2026 USEA results event."""

    return UseaEvent(**PLANTATION_SEP_2026)


def collect_events(
    events: Sequence[UseaEvent],
    *,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Fetch and parse each configured USEA results page."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    results: list[EventingResult] = []
    for event in events:
        html = fetch_results_html(event.url)
        results.extend(parse_results_html(html, event=event, collected_at=collected))
    return results


def _parse_row(
    section: dict[str, object],
    *,
    event: UseaEvent,
    level: str,
    collected_at: datetime,
) -> EventingResult | None:
    links = section["links"]
    cells = section["cells"]
    if not isinstance(links, list) or not isinstance(cells, list) or len(links) < 2:
        return None
    horse_name = _clean_text(str(links[0]))
    rider_name = _display_rider(_clean_text(str(links[1])))
    if not horse_name or not rider_name or len(cells) < 6:
        return None

    dressage = _parse_number(str(cells[0]))
    xc_jump = _parse_number(str(cells[1]))
    xc_time = _parse_number(str(cells[2]))
    sj_jump = _parse_number(str(cells[3]))
    sj_time = _parse_number(str(cells[4]))
    total = _parse_number(str(cells[5]))
    if None in {dressage, xc_jump, xc_time, sj_jump, sj_time, total}:
        return None
    assert dressage is not None
    assert xc_jump is not None
    assert xc_time is not None
    assert sj_jump is not None
    assert sj_time is not None

    show_jumping = round(sj_jump + sj_time, 1)
    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(event.event_id, level, rider_name, horse_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_name,
        horse_name=horse_name,
        event_name=f"{event.event_title} · {level}",
        event_date=event.event_date,
        level=level,
        country=event.country,
        dressage_score=dressage,
        show_jumping_penalties=show_jumping,
        cross_country_jump_penalties=xc_jump,
        cross_country_time_penalties=xc_time,
        collected_at=collected_at,
        is_user_entered=False,
    )


def _level_from_heading(heading: str) -> str | None:
    match = LEVEL_RE.search(heading)
    if not match:
        return None
    return f"CCI{match.group(1)}*-{match.group(2).upper()}"


def _parse_number(value: str) -> float | None:
    text = _clean_text(value).replace(",", ".")
    if not NUMBER_RE.match(text):
        return None
    return round(float(text), 1)


def _display_rider(name: str) -> str:
    """Title-case all-caps USEA rider names while keeping initials."""

    parts = []
    for part in name.split():
        if len(part) <= 2 and part.endswith("."):
            parts.append(part.upper())
            continue
        parts.append(part[:1].upper() + part[1:].lower())
    return " ".join(parts)


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"usea:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect public USEA CCI results")
    parser.add_argument(
        "--plantation-2026",
        action="store_true",
        help="Pull Plantation Field September 2026 CCI results",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    events: list[UseaEvent] = []
    if args.plantation_2026:
        events.append(plantation_sep_2026_event())
    if not events:
        raise SystemExit("Specify --plantation-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_events(events, collected_at=collected_at)
    print(f"USEA collect complete: events={len(events)}, results_collected={len(results)}")
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
