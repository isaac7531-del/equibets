"""Collect finished eventing classifications from public Equiresults pages.

A class is ingested only when the page is no longer provisional or live and
every starter is either a status row or a numeric dressage, show-jumping, and
cross-country total. Refusal notes such as ``40 r(5b)`` stay with the jump
penalty. Elapsed cross-country times stay out of the penalty total.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from equibets.live_scores import build_live_score_payload, load_results_if_present, write_live_score_payload
from equibets.rechenstelle import merge_into_store
from equibets.results import EventingResult


SOURCE_ID = "equiresults"
SOURCE_PRIORITY = 8
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)
PRATONI_CCI1_INTRO_URL = "https://www.equiresults.com/competition/15751/404301/results"
PRATONI_CCIP1S_URL = "https://www.equiresults.com/competition/15751/404302/results"
PRATONI_CCI2S_URL = "https://www.equiresults.com/competition/15751/404300/results"
PRATONI_CCI4S_URL = "https://www.equiresults.com/competition/15751/404298/results"
PRATONI_CCI3S_URL = "https://www.equiresults.com/competition/15751/404299/results"
PRATONI_CCIJ2S_URL = "https://www.equiresults.com/competition/15751/404304/results"
PRATONI_CCI4L_URL = "https://www.equiresults.com/competition/15751/404305/results"
# Rit. is the Italian retirement token used on Equiresults penalty cells.
STATUS_RE = re.compile(
    r"Elim|W\.?\s*D\.?|\bWD\b|\bRET\b|\bRit\.?\b|Automatic",
    re.IGNORECASE,
)
LEADING_NUMBER_RE = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)")


@dataclass(frozen=True)
class EquiresultsClass:
    """One public Equiresults classification page."""

    url: str
    event_name: str
    level: str
    event_date: date
    country: str


def pratoni_cci1_intro_2026_class() -> EquiresultsClass:
    """Return the Pratoni del Vivaro CCI1*-Intro classification."""

    return EquiresultsClass(
        url=PRATONI_CCI1_INTRO_URL,
        event_name="Pratoni del Vivaro · CCI1*-Intro",
        level="CCI1*-Intro",
        event_date=date(2026, 10, 22),
        country="ITA",
    )


def pratoni_ccip1s_2026_class() -> EquiresultsClass:
    """Return the Pratoni del Vivaro CCIP1-S classification."""

    return EquiresultsClass(
        url=PRATONI_CCIP1S_URL,
        event_name="Pratoni del Vivaro · CCIP1-S",
        level="CCIP1-S",
        event_date=date(2026, 10, 23),
        country="ITA",
    )


def pratoni_cci2s_2026_class() -> EquiresultsClass:
    """Return the Pratoni del Vivaro CCI2*-S classification."""

    return EquiresultsClass(
        url=PRATONI_CCI2S_URL,
        event_name="Pratoni del Vivaro · CCI2*-S",
        level="CCI2*-S",
        event_date=date(2026, 10, 22),
        country="ITA",
    )


def pratoni_cci4s_2026_class() -> EquiresultsClass:
    """Return the Pratoni del Vivaro CCI4*-S classification."""

    return EquiresultsClass(
        url=PRATONI_CCI4S_URL,
        event_name="Pratoni del Vivaro · CCI4*-S",
        level="CCI4*-S",
        event_date=date(2026, 10, 22),
        country="ITA",
    )


def pratoni_cci3s_2026_class() -> EquiresultsClass:
    """Return the Pratoni del Vivaro CCI3*-S classification."""

    return EquiresultsClass(
        url=PRATONI_CCI3S_URL,
        event_name="Pratoni del Vivaro · CCI3*-S",
        level="CCI3*-S",
        event_date=date(2026, 10, 23),
        country="ITA",
    )


def pratoni_ccij2s_2026_class() -> EquiresultsClass:
    """Return the Pratoni del Vivaro CCIJ2*-S classification."""

    return EquiresultsClass(
        url=PRATONI_CCIJ2S_URL,
        event_name="Pratoni del Vivaro · CCIJ2*-S",
        level="CCIJ2*-S",
        event_date=date(2026, 10, 23),
        country="ITA",
    )


def pratoni_cci4l_2026_class() -> EquiresultsClass:
    """Return the Pratoni del Vivaro CCI4*-L classification."""

    return EquiresultsClass(
        url=PRATONI_CCI4L_URL,
        event_name="Pratoni del Vivaro · CCI4*-L",
        level="CCI4*-L",
        event_date=date(2026, 10, 23),
        country="ITA",
    )


def fetch_results_html(url: str, *, timeout: float = 45.0) -> str:
    """Fetch one Equiresults classification page as text."""

    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "text/html"})
    try:
        with urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc


def parse_results_page(
    html: str,
    *,
    competition: EquiresultsClass,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse a finished classification. Unfinished pages return no rows."""

    if not _is_finished_page(html):
        return []
    parser = _ResultsParser()
    parser.feed(html)
    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for row in parser.rows:
        parsed = _parse_row(row, competition=competition, collected_at=collected)
        if parsed is None:
            return []
        if parsed is not _STATUS:
            results.append(parsed)
    return results


def collect_class(
    competition: EquiresultsClass,
    *,
    collected_at: datetime | None = None,
    confirm_after_seconds: float = 20.0,
) -> list[EventingResult]:
    """Fetch a class twice and keep rows only when the phase tuples match."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    first = parse_results_page(fetch_results_html(competition.url), competition=competition, collected_at=collected)
    if confirm_after_seconds > 0:
        time.sleep(confirm_after_seconds)
    second = parse_results_page(fetch_results_html(competition.url), competition=competition, collected_at=collected)
    if not first or _phase_tuples(first) != _phase_tuples(second):
        raise RuntimeError(f"Equiresults classification {competition.url} did not match on two fetches")
    return second


class _ResultsParser(HTMLParser):
    """Extract rider, horse, nation, and phase cells from an Equiresults table."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, object]] = []
        self._in_row = False
        self._in_cell = False
        self._cell_class = ""
        self._cell_text: list[str] = []
        self._cells: list[tuple[str, str]] = []
        self._capture: str | None = None
        self._rider = ""
        self._horse = ""
        self._in_nation = False
        self._nation = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "tr" and attributes.get("id", "").startswith("result_"):
            self._in_row = True
            self._cells = []
            self._rider = ""
            self._horse = ""
            self._nation = ""
            return
        if not self._in_row:
            return
        if tag == "td":
            self._in_cell = True
            self._cell_class = attributes.get("class", "")
            self._cell_text = []
            return
        href = attributes.get("href", "")
        if tag == "a" and href.startswith("/rider/"):
            self._capture = "rider"
            return
        if tag == "a" and href.startswith("/horse/"):
            self._capture = "horse"
            return
        if tag == "span" and "flagContainer-right" in attributes.get("class", "").split():
            self._in_nation = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture:
            self._capture = None
            return
        if tag == "span" and self._in_nation:
            self._in_nation = False
            return
        if tag == "td" and self._in_cell:
            self._cells.append((self._cell_class, _clean_text("".join(self._cell_text))))
            self._in_cell = False
            return
        if tag == "tr" and self._in_row:
            self.rows.append(
                {
                    "rider": _clean_text(self._rider),
                    "horse": _clean_text(self._horse),
                    "nation": _clean_text(self._nation),
                    "cells": self._cells,
                }
            )
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._capture == "rider":
            self._rider += data
            return
        if self._capture == "horse":
            self._horse += data
            return
        if self._in_nation and not self._nation.strip() and data.strip():
            self._nation += data
            return
        if self._in_cell:
            self._cell_text.append(data)


_STATUS = object()


def _parse_row(
    row: dict[str, object],
    *,
    competition: EquiresultsClass,
    collected_at: datetime,
) -> EventingResult | object | None:
    rider_name = str(row.get("rider") or "")
    horse_name = str(row.get("horse") or "")
    cells = row.get("cells")
    if not rider_name or not horse_name or not isinstance(cells, list):
        return None
    phase_cells = [(str(css), str(text)) for css, text in cells]
    if _row_has_status(phase_cells):
        return _STATUS

    dressage_cells = _plain_cells(phase_cells)
    show_jumping_cells = _marked_cells(phase_cells, "secondPhase")
    cross_country_cells = _marked_cells(phase_cells, "thirdPhase")
    if len(dressage_cells) < 3 or len(show_jumping_cells) < 3 or len(cross_country_cells) < 3:
        return None
    dressage = _required_number(dressage_cells[1])
    show_jumping = _required_number(show_jumping_cells[2])
    cross_country_jump = _leading_number(cross_country_cells[0])
    cross_country_total = _required_number(cross_country_cells[2])
    final = _required_number(dressage_cells[-1])
    if None in {dressage, show_jumping, cross_country_jump, cross_country_total, final}:
        return None

    cross_country_time = round(cross_country_total - cross_country_jump, 1)
    dressage = round(dressage, 1)
    show_jumping = round(show_jumping, 1)
    cross_country_jump = round(cross_country_jump, 1)
    calculated = round(dressage + show_jumping + cross_country_jump + cross_country_time, 1)
    if cross_country_time < 0 or abs(calculated - round(final, 1)) > 0.05:
        return None

    nation = str(row.get("nation") or "")
    rider_label = f"{rider_name} ({nation})" if nation else rider_name
    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(competition.url, competition.level, rider_name, horse_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_label,
        horse_name=horse_name,
        event_name=competition.event_name,
        event_date=competition.event_date,
        level=competition.level,
        country=competition.country,
        dressage_score=dressage,
        show_jumping_penalties=show_jumping,
        cross_country_jump_penalties=cross_country_jump,
        cross_country_time_penalties=cross_country_time,
        collected_at=collected_at,
        is_user_entered=False,
    )


def _is_finished_page(html: str) -> bool:
    if "Classifica Provvisoria" in html or "Classifica live" in html:
        return False
    return 'id="results_table_' in html or 'id="result_' in html


def _row_has_status(cells: list[tuple[str, str]]) -> bool:
    """Treat elimination and withdrawal penalty cells as non-scoring rows."""

    for marker in ("secondPhase", "thirdPhase"):
        penalty = next((text for css_class, text in cells if marker in css_class.split() and "splitBold" in css_class.split()), "")
        if penalty and STATUS_RE.search(penalty):
            return True
    return False


def _plain_cells(cells: list[tuple[str, str]]) -> list[str]:
    return [text for css_class, text in cells if "secondPhase" not in css_class and "thirdPhase" not in css_class and "splitBold" in css_class.split()]


def _marked_cells(cells: list[tuple[str, str]], marker: str) -> list[str]:
    return [text for css_class, text in cells if marker in css_class.split()]


def _required_number(value: str) -> float | None:
    match = LEADING_NUMBER_RE.match(value.replace(",", "."))
    if match is None:
        return None
    return float(match.group(1))


def _leading_number(value: str) -> float | None:
    return _required_number(value)


def _phase_tuples(results: Sequence[EventingResult]) -> list[tuple[object, ...]]:
    return [
        (
            result.rider_name,
            result.horse_name,
            result.dressage_score,
            result.show_jumping_penalties,
            result.cross_country_jump_penalties,
            result.cross_country_time_penalties,
        )
        for result in results
    ]


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"equiresults:{digest}"


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect a finished Equiresults eventing classification")
    parser.add_argument("--pratoni-cci1-intro-2026", action="store_true", help="Pull Pratoni del Vivaro CCI1*-Intro")
    parser.add_argument("--pratoni-ccip1s-2026", action="store_true", help="Pull Pratoni del Vivaro CCIP1-S")
    parser.add_argument("--pratoni-cci2s-2026", action="store_true", help="Pull Pratoni del Vivaro CCI2*-S")
    parser.add_argument("--pratoni-cci4s-2026", action="store_true", help="Pull Pratoni del Vivaro CCI4*-S")
    parser.add_argument("--pratoni-cci3s-2026", action="store_true", help="Pull Pratoni del Vivaro CCI3*-S")
    parser.add_argument("--pratoni-ccij2s-2026", action="store_true", help="Pull Pratoni del Vivaro CCIJ2*-S")
    parser.add_argument("--pratoni-cci4l-2026", action="store_true", help="Pull Pratoni del Vivaro CCI4*-L")
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--start-date", type=_date_arg, required=True, help="Live snapshot window start, YYYY-MM-DD")
    parser.add_argument("--end-date", type=_date_arg, required=True, help="Live snapshot window end, YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    selected = [
        pratoni_cci1_intro_2026_class() if args.pratoni_cci1_intro_2026 else None,
        pratoni_ccip1s_2026_class() if args.pratoni_ccip1s_2026 else None,
        pratoni_cci2s_2026_class() if args.pratoni_cci2s_2026 else None,
        pratoni_cci4s_2026_class() if args.pratoni_cci4s_2026 else None,
        pratoni_cci3s_2026_class() if args.pratoni_cci3s_2026 else None,
        pratoni_ccij2s_2026_class() if args.pratoni_ccij2s_2026 else None,
        pratoni_cci4l_2026_class() if args.pratoni_cci4l_2026 else None,
    ]
    selected = [competition for competition in selected if competition is not None]
    if len(selected) != 1:
        raise SystemExit(
            "Specify one of --pratoni-cci1-intro-2026, --pratoni-ccip1s-2026, "
            "--pratoni-cci2s-2026, --pratoni-cci4s-2026, --pratoni-cci3s-2026, "
            "--pratoni-ccij2s-2026, or --pratoni-cci4l-2026"
        )
    competition = selected[0]
    results = collect_class(competition)
    print(f"Equiresults collect complete: results_collected={len(results)}")
    if args.dry_run:
        return 0

    merge_into_store(args.output, results)
    payload = build_live_score_payload(
        load_results_if_present(args.output),
        start_date=args.start_date,
        end_date=args.end_date,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0),
    )
    write_live_score_payload(payload, args.live_output)
    print(
        "Live scoring snapshot written: "
        f"events={payload['event_count']}, results={payload['result_count']}, "
        f"window={args.start_date.isoformat()}..{args.end_date.isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
