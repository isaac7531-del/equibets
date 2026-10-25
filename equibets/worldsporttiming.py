"""Collect live eventing scores from public World Sport Timing result pages.

Final classification pages publish dressage, cross-country, and show jumping
on one row. A row is ingested only when every phase cell is numeric and the
displayed total matches those penalties. Status rows such as WD-DR and WD-XC
stay out of the store.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from equibets.live_scores import build_live_score_payload, write_live_score_payload
from equibets.rechenstelle import merge_into_store
from equibets.results import EventingResult


SOURCE_ID = "worldsporttiming"
SOURCE_PRIORITY = 6
PAIR_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)\s*$")
NUMBER_RE = re.compile(r"^(-?\d+(?:\.\d+)?)")
STATUS_RE = re.compile(r"[A-Za-z]")

# US Equestrian Open Eventing Final, Morven Park, 8–11 Oct 2026.
# CCI4*-L and CCI4*-S finals are the public show-jumping classification pages.
# Dressage opened on 8 Oct, so the stored show date stays on that start day.
MORVEN_PARK_OCT_2026 = (
    {
        "url": "https://results.worldsporttiming.com/2026/us-equestrian-open-eventing-final/competition/4L-SJ/result",
        "event_name": "Morven Park · CCI4*-L",
        "level": "CCI4*-L",
        "event_date": date(2026, 10, 8),
        "country": "USA",
    },
    {
        "url": "https://results.worldsporttiming.com/2026/us-equestrian-open-eventing-final/competition/4S-SJ/result",
        "event_name": "Morven Park · CCI4*-S",
        "level": "CCI4*-S",
        "event_date": date(2026, 10, 8),
        "country": "USA",
    },
)

# Mondial du Lion, Le Lion d'Angers, 15–18 Oct 2026.
# The stored show date is the first day of the meeting. Both finished
# show-jumping classifications are included. A class stays out while its
# overview control is Live or any starter still lacks a show-jumping cell.
MONDIAL_DU_LION_OCT_2026 = (
    {
        "url": "https://results.worldsporttiming.com/2026/mondial-du-lion/competition/6YO-SJ/result",
        "event_name": "Mondial du Lion · 6-year-old",
        "level": "6-year-old",
        "event_date": date(2026, 10, 15),
        "country": "FRA",
    },
    {
        "url": "https://results.worldsporttiming.com/2026/mondial-du-lion/competition/7YO-SJ/result",
        "event_name": "Mondial du Lion · 7-year-old",
        "level": "7-year-old",
        "event_date": date(2026, 10, 15),
        "country": "FRA",
    },
)

# Les 5 Etoiles de Pau, 22–25 Oct 2026.
# Dressage opened on 22 Oct, so the stored show date stays on that start day.
# The CCI5*-L show-jumping classification is the finish. Ingest it only after
# the overview Live control is gone and every starter still in the class has
# numeric cross-country and show-jumping penalties that reconcile to the total.
PAU_OCT_2026 = (
    {
        "url": "https://results.worldsporttiming.com/2026/les-5-etoiles-de-pau/competition/SJ/result",
        "event_name": "Les 5 Etoiles de Pau · CCI5*-L",
        "level": "CCI5*-L",
        "event_date": date(2026, 10, 22),
        "country": "FRA",
    },
)


@dataclass(frozen=True)
class WorldSportTimingBoard:
    """One public World Sport Timing final classification page."""

    url: str
    event_name: str
    level: str
    event_date: date
    country: str


class _ResultParser(HTMLParser):
    """Extract rider, horse, nation, and phase cells from a WST results table."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, object]] = []
        self._in_row = False
        self._row: dict[str, object] | None = None
        self._in_td = False
        self._td_parts: list[str] = []
        self._skip_infos = 0
        self._capture_rider = False
        self._capture_horse = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value or "" for key, value in attrs}
        classes = set(attributes.get("class", "").split())
        if tag == "tr" and any(name.startswith("line_") for name in classes):
            self._in_row = True
            self._row = {"rider": "", "horse": "", "nation": "", "cells": []}
            return
        if not self._in_row or self._row is None:
            return
        if tag == "td":
            self._in_td = True
            self._td_parts = []
            return
        if tag == "br" and self._in_td:
            self._td_parts.append("\n")
            return
        if tag == "div" and "rider" in classes:
            self._capture_rider = True
            return
        if tag == "span" and "horse" in classes and "infos" not in classes:
            self._capture_horse = True
            return
        if tag == "span" and "infos" in classes:
            self._skip_infos += 1
            return
        if tag == "img" and "/flags/" in attributes.get("src", ""):
            nation = attributes["src"].rsplit("/", 1)[-1].split(".", 1)[0]
            if nation and not self._row["nation"]:
                self._row["nation"] = nation

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._skip_infos:
            self._skip_infos -= 1
            return
        if tag == "div" and self._capture_rider:
            self._capture_rider = False
            return
        if tag == "span" and self._capture_horse:
            self._capture_horse = False
            return
        if tag == "td" and self._in_td and self._row is not None:
            cells = self._row["cells"]
            if isinstance(cells, list):
                cells.append("".join(self._td_parts).replace("\xa0", " ").strip())
            self._in_td = False
            self._td_parts = []
            return
        if tag == "tr" and self._in_row and self._row is not None:
            self.rows.append(self._row)
            self._in_row = False
            self._row = None

    def handle_data(self, data: str) -> None:
        if not self._in_row or self._row is None or self._skip_infos:
            return
        cleaned = " ".join(data.split())
        if self._capture_rider and cleaned and not self._row["rider"]:
            self._row["rider"] = cleaned
        if self._capture_horse and cleaned and not self._row["horse"]:
            self._row["horse"] = cleaned
        if self._in_td:
            self._td_parts.append(data)


def fetch_result_html(url: str, *, timeout: float = 45.0) -> str:
    """Fetch a World Sport Timing result page as text.

    Direct urllib receives a Cloudflare challenge. One fresh browser-impersonation
    session per URL returns the raw result document.
    """

    from curl_cffi import requests

    session = requests.Session(impersonate="chrome136")
    try:
        response = session.get(url, timeout=timeout)
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc}") from exc
    finally:
        session.close()
    if response.status_code != 200:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")
    charset = response.encoding or "utf-8"
    return response.content.decode(charset, errors="replace")


def parse_result_page(
    html: str,
    *,
    board: WorldSportTimingBoard,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse a final classification page into reconciled EventingResult rows."""

    parser = _ResultParser()
    parser.feed(html)
    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for row in parser.rows:
        parsed = _parse_row(row, board=board, collected_at=collected)
        if parsed is not None:
            results.append(parsed)
    if len(html) > 1000 and parser.rows and not results:
        raise RuntimeError(f"World Sport Timing page {board.url} parsed no scored rows")
    return results


def morven_park_oct_2026_boards() -> list[WorldSportTimingBoard]:
    """Return the Morven Park October 2026 CCI final pages."""

    return [WorldSportTimingBoard(**item) for item in MORVEN_PARK_OCT_2026]


def mondial_du_lion_oct_2026_boards() -> list[WorldSportTimingBoard]:
    """Return the finished Mondial du Lion October 2026 show-jumping finals."""

    return [WorldSportTimingBoard(**item) for item in MONDIAL_DU_LION_OCT_2026]


def pau_oct_2026_boards() -> list[WorldSportTimingBoard]:
    """Return the finished Pau October 2026 CCI5*-L show-jumping final."""

    return [WorldSportTimingBoard(**item) for item in PAU_OCT_2026]


def collect_boards(
    boards: Sequence[WorldSportTimingBoard],
    *,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Fetch and parse each configured World Sport Timing board."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    results: list[EventingResult] = []
    for board in boards:
        html = fetch_result_html(board.url)
        results.extend(parse_result_page(html, board=board, collected_at=collected))
    return results


def _parse_row(
    row: dict[str, object],
    *,
    board: WorldSportTimingBoard,
    collected_at: datetime,
) -> EventingResult | None:
    rider_name = _clean_text(str(row.get("rider") or ""))
    horse_name = _clean_text(str(row.get("horse") or ""))
    cells = row.get("cells")
    if not rider_name or not horse_name or not isinstance(cells, list) or len(cells) < 5:
        return None

    total_cell = _first_line(str(cells[-1]))
    if not total_cell or STATUS_RE.search(total_cell.split()[0]):
        return None
    dressage = _parse_number(_first_line(str(cells[-5])))
    cross_country = _parse_pair(str(cells[-4]))
    show_jumping = _parse_pair(str(cells[-2]))
    total = _parse_number(total_cell)
    if dressage is None or cross_country is None or show_jumping is None or total is None:
        raise ValueError(f"{board.level} row {rider_name} / {horse_name} is missing a phase penalty")

    xc_jump, xc_time = cross_country
    sj_jump, sj_time = show_jumping
    show_jumping_penalties = round(sj_jump + sj_time, 1)
    calculated = round(dressage + xc_jump + xc_time + show_jumping_penalties, 1)
    if abs(calculated - total) > 0.05:
        raise ValueError(
            f"{board.level} row {rider_name} / {horse_name} total {total} does not match phases {calculated}"
        )

    nation = _clean_text(str(row.get("nation") or ""))
    rider_label = f"{rider_name} ({nation})" if nation else rider_name
    bib = _clean_text(_first_line(str(cells[1]))) if len(cells) > 1 else ""
    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(board.url, board.level, bib, rider_name, horse_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_label,
        horse_name=horse_name,
        event_name=board.event_name,
        event_date=board.event_date,
        level=board.level,
        country=board.country,
        dressage_score=dressage,
        show_jumping_penalties=show_jumping_penalties,
        cross_country_jump_penalties=xc_jump,
        cross_country_time_penalties=xc_time,
        collected_at=collected_at,
        is_user_entered=False,
    )


def _first_line(value: str) -> str:
    return value.replace("\xa0", " ").split("\n", 1)[0].strip()


def _parse_number(value: str) -> float | None:
    token = value.strip().split()[0] if value.strip() else ""
    if not token or STATUS_RE.search(token):
        return None
    match = NUMBER_RE.match(token.replace(",", "."))
    if match is None:
        return None
    return float(match.group(1))


def _parse_pair(value: str) -> tuple[float, float] | None:
    match = PAIR_RE.match(_first_line(value))
    if match is None:
        return None
    return float(match.group(1)), float(match.group(2))


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"worldsporttiming:{digest}"


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect World Sport Timing eventing finals")
    parser.add_argument(
        "--morven-park-2026",
        action="store_true",
        help="Pull the Morven Park October 2026 CCI4*-L and CCI4*-S finals",
    )
    parser.add_argument(
        "--mondial-du-lion-2026",
        action="store_true",
        help="Pull the finished Mondial du Lion October 2026 6- and 7-year-old finals",
    )
    parser.add_argument(
        "--pau-2026",
        action="store_true",
        help="Pull the finished Les 5 Etoiles de Pau October 2026 CCI5*-L final",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--start-date", type=_date_arg, help="Live snapshot window start, YYYY-MM-DD")
    parser.add_argument("--end-date", type=_date_arg, help="Live snapshot window end, YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    boards: list[WorldSportTimingBoard] = []
    if args.morven_park_2026:
        boards.extend(morven_park_oct_2026_boards())
    if args.mondial_du_lion_2026:
        boards.extend(mondial_du_lion_oct_2026_boards())
    if args.pau_2026:
        boards.extend(pau_oct_2026_boards())
    if not boards:
        raise SystemExit("Specify --morven-park-2026, --mondial-du-lion-2026, or --pau-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_boards(boards, collected_at=collected_at)
    print(
        "World Sport Timing collect complete: "
        f"boards={len(boards)}, results_collected={len(results)}"
    )
    if args.dry_run:
        return 0
    if args.start_date is None or args.end_date is None:
        raise SystemExit("Pass --start-date and --end-date to write the live snapshot")

    merged = merge_into_store(args.output, results)
    live_payload = build_live_score_payload(
        merged,
        start_date=args.start_date,
        end_date=args.end_date,
    )
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
