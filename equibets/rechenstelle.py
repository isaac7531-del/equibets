"""Collect live eventing scores from Rechenstelle leaderboards."""

from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from equibets.fei_bot import FeiResultStore, result_to_mapping
from equibets.live_scores import (
    build_live_score_payload,
    current_event_window,
    write_live_score_payload,
)
from equibets.results import EventingResult, consolidate_results


SOURCE_ID = "rechenstelle"
SOURCE_PRIORITY = 5
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Public Millstreet July 2026 boards (FEI U25 Worlds + supporting classes).
MILLSTREET_JULY_2026 = (
    {
        "url": "https://live.rechenstelle.de/2026/millstreet_07/leaderboard52.html",
        "event_name": "Millstreet · CH-M-U25-C",
        "level": "CH-M-U25-C",
        "event_date": date(2026, 7, 21),
        "country": "IRL",
    },
    {
        "url": "https://live.rechenstelle.de/2026/millstreet_07/leaderboard01.html",
        "event_name": "Millstreet · CCI4*-L",
        "level": "CCI4*-L",
        "event_date": date(2026, 7, 21),
        "country": "IRL",
    },
    {
        "url": "https://live.rechenstelle.de/2026/millstreet_07/leaderboard02.html",
        "event_name": "Millstreet · CCI3*-L",
        "level": "CCI3*-L",
        "event_date": date(2026, 7, 21),
        "country": "IRL",
    },
    {
        "url": "https://live.rechenstelle.de/2026/millstreet_07/leaderboard03.html",
        "event_name": "Millstreet · CCI2*-L",
        "level": "CCI2*-L",
        "event_date": date(2026, 7, 21),
        "country": "IRL",
    },
    {
        "url": "https://live.rechenstelle.de/2026/millstreet_07/leaderboard04.html",
        "event_name": "Millstreet · CCI4*-S",
        "level": "CCI4*-S",
        "event_date": date(2026, 7, 21),
        "country": "IRL",
    },
    {
        "url": "https://live.rechenstelle.de/2026/millstreet_07/leaderboard05.html",
        "event_name": "Millstreet · CCI3*-S",
        "level": "CCI3*-S",
        "event_date": date(2026, 7, 21),
        "country": "IRL",
    },
)

# FEI Eventing World Championship Aachen (CH-M-C), Aug 11–16 2026.
# Dressage start list / live board; rows without dressage scores are skipped.
AACHEN_CHMC_2026 = (
    {
        "url": "https://live.rechenstelle.de/2026/aachen/leaderboard01.html",
        "event_name": "Aachen · CH-M-C",
        "level": "CH-M-C",
        "event_date": date(2026, 8, 11),
        "country": "GER",
    },
)

# Hambach (GER) CCI3*-S / CCI2*-S / CCI1*-Intro, Aug 21–23 2026.
# Dressage opened on the public boards on Aug 20; rows without dressage are skipped.
HAMBACH_AUG_2026 = (
    {
        "url": "https://live.rechenstelle.de/2026/hambach/leaderboard01.html",
        "event_name": "Hambach · CCI3*-S",
        "level": "CCI3*-S",
        "event_date": date(2026, 8, 21),
        "country": "GER",
    },
    {
        "url": "https://live.rechenstelle.de/2026/hambach/leaderboard02.html",
        "event_name": "Hambach · CCI2*-S",
        "level": "CCI2*-S",
        "event_date": date(2026, 8, 21),
        "country": "GER",
    },
    {
        "url": "https://live.rechenstelle.de/2026/hambach/leaderboard03.html",
        "event_name": "Hambach · CCI1*-Intro",
        "level": "CCI1*-Intro",
        "event_date": date(2026, 8, 21),
        "country": "GER",
    },
)

# Segersjö (SWE) CCI3*-S / CH-EU-J-CCI2*-L / CH-EU-Y-CCI3*-L, Aug 26–30 2026.
# Public start-list boards appeared Aug 25; rows without dressage are skipped.
SEGERSJO_AUG_2026 = (
    {
        "url": "https://live.rechenstelle.de/2026/segersjo/leaderboard01.html",
        "event_name": "Segersjö · CCI3*-S",
        "level": "CCI3*-S",
        "event_date": date(2026, 8, 26),
        "country": "SWE",
    },
    {
        "url": "https://live.rechenstelle.de/2026/segersjo/leaderboard11.html",
        "event_name": "Segersjö · CH-EU-J-CCI2*-L",
        "level": "CH-EU-J-CCI2*-L",
        "event_date": date(2026, 8, 26),
        "country": "SWE",
    },
    {
        "url": "https://live.rechenstelle.de/2026/segersjo/leaderboard61.html",
        "event_name": "Segersjö · CH-EU-Y-CCI3*-L",
        "level": "CH-EU-Y-CCI3*-L",
        "event_date": date(2026, 8, 26),
        "country": "SWE",
    },
)


@dataclass(frozen=True)
class RechenstelleBoard:
    """One Rechenstelle leaderboard page to ingest."""

    url: str
    event_name: str
    level: str
    event_date: date
    country: str


# Rechenstelle marks retirements/withdrawals with compact tokens such as WD,
# WDbDRE, WDbSJ, NAbSJ (not accepted before show jumping), EL, ELcDRE, RT,
# and RTcDRE. Accept any WD/EL/RT/NAb suffix so phase-specific forms are
# skipped when they leave the scored field.
STATUS_TOKEN_RE = re.compile(
    r"\b(?:WD\w*|NAb\w*|EL\w*|RET|RT\w*|DNS|DSQ)\b",
    re.IGNORECASE,
)


class _LeaderboardParser(HTMLParser):
    """Extract parent standing rows from a Rechenstelle leaderboard table."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[dict[str, str | None]]] = []
        self.header_cells: list[str] = []
        self.title = ""
        self.last_update = ""
        self._capture_title = False
        self._in_thead = False
        self._in_header_row = False
        self._header_cell: str | None = None
        self._in_parent = False
        self._row: list[dict[str, str | None]] | None = None
        self._cell: dict[str, str | None] | None = None
        self._last_update_pending = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        if tag == "title":
            self._capture_title = True
            return
        if tag == "p" and "lastupdate" in attributes.get("class", "").split():
            self._last_update_pending = True
            return
        if tag == "thead":
            self._in_thead = True
            return
        if self._in_thead and tag == "tr" and not self.header_cells:
            self._in_header_row = True
            return
        if self._in_header_row and tag in {"th", "td"}:
            self._header_cell = ""
            return
        if tag == "tr" and attributes.get("class", "").startswith("parent"):
            self._in_parent = True
            self._row = []
            return
        if not self._in_parent:
            return
        if tag == "td":
            self._cell = {"text": "", "flag": None}
            return
        if self._cell is not None and tag == "img" and "flags/" in attributes.get("src", ""):
            flag_name = attributes["src"].rsplit("/", 1)[-1]
            self._cell["flag"] = flag_name.split(".", 1)[0]

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False
            return
        if tag == "thead":
            self._in_thead = False
            self._in_header_row = False
            return
        if tag == "tr" and self._in_header_row:
            self._in_header_row = False
            return
        if tag in {"th", "td"} and self._header_cell is not None:
            label = _clean_text(self._header_cell)
            if label:
                self.header_cells.append(label)
            self._header_cell = None
            return
        if tag == "td" and self._cell is not None and self._row is not None:
            self._row.append(self._cell)
            self._cell = None
            return
        if tag == "tr" and self._in_parent and self._row is not None:
            self.rows.append(self._row)
            self._row = None
            self._in_parent = False

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self.title += data
            return
        if self._last_update_pending:
            match = re.search(r"Last Update:\s*(.+)", data)
            if match:
                self.last_update = match.group(1).strip()
                self._last_update_pending = False
            return
        if self._header_cell is not None:
            self._header_cell += data
            return
        if self._cell is not None:
            self._cell["text"] = (self._cell["text"] or "") + data


def fetch_leaderboard_html(url: str, *, timeout: float = 30.0) -> str:
    """Fetch a Rechenstelle leaderboard page as text."""

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
    board: RechenstelleBoard,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse Rechenstelle leaderboard HTML into EventingResult rows."""

    parser = _LeaderboardParser()
    parser.feed(html)
    collected = collected_at or datetime.now(timezone.utc)
    phase_order = _detect_phase_order(parser.header_cells)
    results: list[EventingResult] = []

    for row in parser.rows:
        if len(row) < 8:
            continue
        if _row_has_status(row):
            continue
        rider_name = _clean_text(row[2].get("text"))
        horse_name = _clean_text(row[4].get("text"))
        dressage = _parse_number(row[7].get("text"))
        if not rider_name or not horse_name or dressage is None:
            continue

        show_jumping, xc_jump, xc_time = _phase_penalties(row, phase_order=phase_order)
        nation = row[3].get("flag")
        rider_label = f"{rider_name} ({nation})" if nation else rider_name
        start_no = _clean_text(row[1].get("text"))
        record_id = _record_id(board.url, board.level, start_no, rider_name, horse_name)

        results.append(
            EventingResult(
                source_id=SOURCE_ID,
                source_record_id=record_id,
                source_priority=SOURCE_PRIORITY,
                rider_name=rider_label,
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


def _detect_phase_order(header_cells: Sequence[str]) -> str:
    """Return sj_then_xc or xc_then_sj from the primary header row."""

    normalized = [html_lib.unescape(cell).casefold() for cell in header_cells]
    try:
        jumping_at = next(index for index, cell in enumerate(normalized) if cell == "jumping")
        cross_country_at = next(
            index for index, cell in enumerate(normalized) if cell == "cross-country"
        )
    except StopIteration:
        return "xc_then_sj"
    if jumping_at < cross_country_at:
        return "sj_then_xc"
    return "xc_then_sj"


def _phase_penalties(
    row: Sequence[dict[str, str | None]],
    *,
    phase_order: str,
) -> tuple[float, float, float]:
    """Map Jumping/XC columns for short (SJ→XC) and long (XC→SJ) boards."""

    if phase_order == "sj_then_xc":
        show_jumping = _parse_number(row[9].get("text")) if len(row) > 9 else None
        # Jumping "Time" is elapsed clock time, not penalty points.
        xc_jump = _parse_number(row[13].get("text")) if len(row) > 13 else None
        xc_time = _parse_xc_time_penalties(row[14].get("text")) if len(row) > 14 else None
    else:
        xc_jump = _parse_number(row[9].get("text")) if len(row) > 9 else None
        xc_time = _parse_xc_time_penalties(row[10].get("text")) if len(row) > 10 else None
        show_jumping = _parse_number(row[13].get("text")) if len(row) > 13 else None
    return show_jumping or 0.0, xc_jump or 0.0, xc_time or 0.0


def _row_has_status(row: Sequence[dict[str, str | None]]) -> bool:
    # Rider (2) and horse (4) names can start with EL/RT (Eliope, Elliot) and
    # must not be treated as elimination/retirement tokens.
    return any(
        STATUS_TOKEN_RE.search(_clean_text(cell.get("text")))
        for index, cell in enumerate(row)
        if index not in {2, 4}
    )


def _parse_xc_time_penalties(value: str | None) -> float | None:
    """Parse XC time penalties, ignoring mm:ss clock times."""

    text = _clean_text(value)
    if not text:
        return None
    if re.fullmatch(r"\d{1,2}:\d{2}(?:\.\d+)?", text):
        return 0.0
    return _parse_number(text)


def collect_boards(
    boards: Sequence[RechenstelleBoard],
    *,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Fetch and parse each configured Rechenstelle board."""

    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for board in boards:
        html = fetch_leaderboard_html(board.url)
        results.extend(parse_leaderboard_results(html, board=board, collected_at=collected))
    return results


def millstreet_july_2026_boards() -> list[RechenstelleBoard]:
    """Return the Millstreet July 2026 public leaderboard set."""

    return [RechenstelleBoard(**item) for item in MILLSTREET_JULY_2026]


def aachen_chmc_2026_boards() -> list[RechenstelleBoard]:
    """Return the Aachen 2026 FEI Eventing World Championship board set."""

    return [RechenstelleBoard(**item) for item in AACHEN_CHMC_2026]


def hambach_aug_2026_boards() -> list[RechenstelleBoard]:
    """Return the Hambach August 2026 public leaderboard set."""

    return [RechenstelleBoard(**item) for item in HAMBACH_AUG_2026]


def segersjo_aug_2026_boards() -> list[RechenstelleBoard]:
    """Return the Segersjö August 2026 public leaderboard set."""

    return [RechenstelleBoard(**item) for item in SEGERSJO_AUG_2026]


def merge_into_store(store_path: Path, new_results: Iterable[EventingResult]) -> list[EventingResult]:
    """Merge Rechenstelle rows into the shared results store.

    Previous Rechenstelle rows for the same event/level/date are replaced so
    retired/eliminated combinations disappear when they leave the live board.
    """

    store = FeiResultStore(store_path)
    incoming = list(new_results)
    refresh_keys = {
        (_slug(result.event_name), result.event_date, _slug(result.level), result.source_id)
        for result in incoming
    }
    retained = [
        result
        for result in store.load()
        if (
            _slug(result.event_name),
            result.event_date,
            _slug(result.level),
            result.source_id,
        )
        not in refresh_keys
    ]
    merged = consolidate_results([*retained, *incoming])
    store.path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "source_id": "mixed",
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "results": [result_to_mapping(result) for result in merged],
    }
    with store.path.open("w", encoding="utf-8") as results_file:
        json.dump(payload, results_file, indent=2, sort_keys=True)
        results_file.write("\n")
    return merged


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _clean_text(value: str | None) -> str:
    text = html_lib.unescape(value or "")
    text = text.replace("\xa0", " ")
    return " ".join(text.split())


def _parse_number(value: str | None) -> float | None:
    text = _clean_text(value)
    if not text:
        return None
    # Skip status markers such as WD / EL / RET / WDbDRE.
    if re.search(r"[A-Za-z]", text):
        return None
    normalized = text.replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"rechenstelle:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Rechenstelle live eventing scores")
    parser.add_argument(
        "--millstreet-july-2026",
        action="store_true",
        help="Pull the Millstreet July 2026 public leaderboards",
    )
    parser.add_argument(
        "--aachen-ch-m-c-2026",
        action="store_true",
        help="Pull the Aachen 2026 FEI Eventing World Championship leaderboard",
    )
    parser.add_argument(
        "--hambach-2026",
        action="store_true",
        help="Pull the Hambach August 2026 public leaderboards",
    )
    parser.add_argument(
        "--segersjo-2026",
        action="store_true",
        help="Pull the Segersjö August 2026 public leaderboards",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    boards: list[RechenstelleBoard] = []
    if args.millstreet_july_2026:
        boards.extend(millstreet_july_2026_boards())
    if args.aachen_ch_m_c_2026:
        boards.extend(aachen_chmc_2026_boards())
    if args.hambach_2026:
        boards.extend(hambach_aug_2026_boards())
    if args.segersjo_2026:
        boards.extend(segersjo_aug_2026_boards())
    if not boards:
        raise SystemExit(
            "Specify --millstreet-july-2026, --aachen-ch-m-c-2026, --hambach-2026, and/or --segersjo-2026"
        )

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_boards(boards, collected_at=collected_at)
    print(
        "Rechenstelle collect complete: "
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
