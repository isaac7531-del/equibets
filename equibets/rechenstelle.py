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


@dataclass(frozen=True)
class RechenstelleBoard:
    """One Rechenstelle leaderboard page to ingest."""

    url: str
    event_name: str
    level: str
    event_date: date
    country: str


class _LeaderboardParser(HTMLParser):
    """Extract parent standing rows from a Rechenstelle leaderboard table."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[dict[str, str | None]]] = []
        self.title = ""
        self.last_update = ""
        self._capture_title = False
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
    results: list[EventingResult] = []

    for row in parser.rows:
        if len(row) < 8:
            continue
        rider_name = _clean_text(row[2].get("text"))
        horse_name = _clean_text(row[4].get("text"))
        dressage = _parse_number(row[7].get("text"))
        if not rider_name or not horse_name or dressage is None:
            continue

        xc_jump = _parse_number(row[9].get("text")) if len(row) > 9 else None
        xc_time = _parse_number(row[10].get("text")) if len(row) > 10 else None
        show_jumping = _parse_number(row[13].get("text")) if len(row) > 13 else None
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
                show_jumping_penalties=show_jumping or 0.0,
                cross_country_jump_penalties=xc_jump or 0.0,
                cross_country_time_penalties=xc_time or 0.0,
                collected_at=collected,
                is_user_entered=False,
            )
        )
    return results


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


def merge_into_store(store_path: Path, new_results: Iterable[EventingResult]) -> list[EventingResult]:
    """Merge Rechenstelle rows into the shared results store."""

    store = FeiResultStore(store_path)
    merged = consolidate_results([*store.load(), *new_results])
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
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.millstreet_july_2026:
        raise SystemExit("Specify --millstreet-july-2026")

    boards = millstreet_july_2026_boards()
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
