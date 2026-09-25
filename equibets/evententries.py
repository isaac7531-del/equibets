"""Collect live eventing scores from public Event Entries scoring boards.

Stable View and similar shows publish dressage through a GWT scoring board
before USEA posts final results. Horse-detail text still contains heights, and
judge movement marks are not penalties. A row is ingested only after the board
publishes a one-decimal dressage penalty that follows the judge percentages.
Repeated rider names are read from the GWT index stream, because the string
table stores each distinct rider only once.

Show jumping is read only when the four numbers before that dressage penalty
are stadium faults, the elapsed round time, the time penalty, and a to-date
total that equals dressage plus those two penalties. Cross-country columns
stay at zero until their own jump and time cells publish.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
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


SOURCE_ID = "evententries"
# USEA national finals use priority 50. This live board stays in the store
# until those finals exist, then consolidation keeps the USEA row.
SOURCE_PRIORITY = 55
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
RPC_URL = "https://evententries.com/evententries/sf"
MODULE_BASE = "https://evententries.com/evententries/"
GWT_POLICY = "388C357899641117D1A454BDD8BDB302"
GWT_PERMUTATION = "D424D80087469774D4CE05FE306DA273"
GWT_INTERFACE = "com.kyler.ee.client.ServerFuncs"
GWT_METHOD = "LoadScoringBoard"
HORSE_BIO_RE = re.compile(r"\b(?:Owner|Gender|Breed|FEI):")
RIDER_RE = re.compile(r"^.+\([A-Z]{3}\)$")
PERCENT_RE = re.compile(r"^\d{1,3}\.\d{2}$")
PENALTY_RE = re.compile(r"^\d{1,3}\.\d$")
LEVEL_RE = re.compile(r"\bCCI(\d)-([SL])\b", re.IGNORECASE)
STATUS_RE = re.compile(r"^(?:EL|RT|WD|RET|DSQ|DNS|HC)$", re.IGNORECASE)

# Stable View Oktoberfest, Aiken, 25–27 Sep 2026 (USEA 19093).
# Class tokens are the public LiveScores board ids. CCI1*-S is included so a
# later dressage update is picked up; rows without a dressage penalty are skipped.
STABLE_VIEW_SEP_2026 = {
    "event_title": "Stable View",
    "event_date": date(2026, 9, 25),
    "country": "USA",
    "classes": (
        {
            "level": "CCI4*-S",
            "token": "mOjO68Eb7vmHDk44djpYrZunX17L05N7JNl_kPVlNRcwZIKJl0zhG5Il$dEkIKFc",
        },
        {
            "level": "CCI3*-S",
            "token": "wBM6jb$kYLIN7jm2JPp5mwn8h17WZzRsJkfEjOqU4r9n3Zjgo2V3WfRgq1r_jChq",
        },
        {
            "level": "CCI2*-S",
            "token": "4mRGd$QLVWoAgsIERSD4s5V$k$5uJoXoucw2_S_kOLZFSDUgqFr4pYI7UdKWBt9J",
        },
        {
            "level": "CCI1*-S",
            "token": "y$$qRJuvporwZ6MRbssLY0dmrEWDk5YIKHGCB32RW7NFSDUgqFr4pYI7UdKWBt9J",
        },
    ),
}


@dataclass(frozen=True)
class EventEntriesClass:
    """One public Event Entries class scoring board."""

    token: str
    level: str
    event_title: str
    event_date: date
    country: str


def scoring_board_payload(token: str) -> str:
    """Return the GWT-RPC body for one scoring board token."""

    return (
        "7|0|6|"
        f"{MODULE_BASE}|{GWT_POLICY}|{GWT_INTERFACE}|{GWT_METHOD}|java.lang.String|"
        f"{token}|1|2|3|4|1|5|6|"
    )


def fetch_scoring_board(token: str, *, timeout: float = 30.0) -> bytes:
    """Fetch one public scoring board as the raw GWT-RPC body."""

    request = Request(
        RPC_URL,
        data=scoring_board_payload(token).encode("utf-8"),
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Content-Type": "text/x-gwt-rpc; charset=UTF-8",
            "X-GWT-Permutation": GWT_PERMUTATION,
            "X-GWT-Module-Base": MODULE_BASE,
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch Event Entries board: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch Event Entries board: {exc.reason}") from exc


def gwt_string_table(body: bytes) -> list[str]:
    """Return the decoded string table from a GWT-RPC scoring response."""

    text = body.decode("utf-8", errors="replace")
    marker = text.rfind(',["')
    if marker < 0:
        raise RuntimeError("Event Entries payload has no string table")
    array_text = re.sub(r",0,7\]\s*$", "", text[marker + 1 :])
    payload = json.loads(array_text)
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise RuntimeError("Event Entries string table is not a list of strings")
    return payload


def gwt_decoded_values(body: bytes) -> list[str]:
    """Resolve the GWT value stream, including repeated string-table indexes.

    The string table lists each distinct value once. A rider with two horses
    is stored as two indexes to the same rider string, so walking the table
    itself drops the second horse.
    """

    text = body.decode("utf-8", errors="replace")
    if not text.startswith("//OK["):
        raise RuntimeError("Event Entries payload is not a GWT-RPC response")
    marker = text.rfind(',["')
    if marker < 0:
        raise RuntimeError("Event Entries payload has no string table")
    strings = gwt_string_table(body)
    decoded: list[str] = []
    for token in text[5:marker].split(","):
        if re.fullmatch(r"-?\d+", token):
            index = int(token) - 1
            if 0 <= index < len(strings):
                decoded.append(strings[index])
                continue
        decoded.append(token)
    return decoded


def parse_scoring_board(
    body: bytes,
    *,
    event: EventEntriesClass,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse a scoring board into rows that already have a dressage penalty."""

    return parse_scoring_values(
        gwt_decoded_values(body),
        event=event,
        collected_at=collected_at,
    )


def parse_scoring_strings(
    strings: Sequence[str],
    *,
    event: EventEntriesClass,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse a GWT string table into scored eventing rows."""

    level = _level_from_strings(strings) or event.level
    if not level.startswith("CCI"):
        return []
    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for block in _horse_blocks(strings):
        parsed = _parse_block(block, event=event, level=level, collected_at=collected)
        if parsed is not None:
            results.append(parsed)
    return results


def parse_scoring_values(
    values: Sequence[str],
    *,
    event: EventEntriesClass,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse a decoded GWT value stream into scored eventing rows."""

    level = _level_from_strings(values) or event.level
    if not level.startswith("CCI"):
        return []
    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for index, value in enumerate(values):
        if "\n" not in value or not HORSE_BIO_RE.search(value):
            continue
        parsed = _parse_stream_entry(
            values,
            index,
            event=event,
            level=level,
            collected_at=collected,
        )
        if parsed is not None:
            results.append(parsed)
    return results


def stable_view_sep_2026_classes() -> list[EventEntriesClass]:
    """Return the Stable View Oktoberfest 2026 CCI scoring boards."""

    return [
        EventEntriesClass(
            token=str(item["token"]),
            level=str(item["level"]),
            event_title=str(STABLE_VIEW_SEP_2026["event_title"]),
            event_date=STABLE_VIEW_SEP_2026["event_date"],
            country=str(STABLE_VIEW_SEP_2026["country"]),
        )
        for item in STABLE_VIEW_SEP_2026["classes"]
    ]


def collect_stable_view_2026(*, collected_at: datetime | None = None) -> list[EventingResult]:
    """Fetch and parse scored CCI classes at Stable View Oktoberfest."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    results: list[EventingResult] = []
    for event in stable_view_sep_2026_classes():
        body = fetch_scoring_board(event.token)
        results.extend(parse_scoring_board(body, event=event, collected_at=collected))
    return results


def _horse_blocks(strings: Sequence[str]) -> list[list[str]]:
    starts = [
        index
        for index, value in enumerate(strings)
        if "\n" in value and HORSE_BIO_RE.search(value)
    ]
    blocks: list[list[str]] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(strings)
        blocks.append(list(strings[start:end]))
    return blocks


def _parse_block(
    block: Sequence[str],
    *,
    event: EventEntriesClass,
    level: str,
    collected_at: datetime,
) -> EventingResult | None:
    if any(STATUS_RE.match(token.strip()) for token in block):
        return None
    horse_name = ""
    rider_name = ""
    seen_percentage = False
    penalties: list[float] = []
    for token in block[1:]:
        text = _clean_text(token)
        if not text or "\n" in token:
            continue
        if not horse_name and not RIDER_RE.match(text) and PERCENT_RE.match(text) is None:
            if text.isdigit() or STATUS_RE.match(text):
                continue
            horse_name = text
            continue
        if RIDER_RE.match(text):
            rider_name = text
            continue
        if PERCENT_RE.match(text):
            seen_percentage = True
            continue
        if seen_percentage and PENALTY_RE.match(text):
            penalties.append(round(float(text), 1))
    if not horse_name or not rider_name or not penalties:
        return None
    dressage = penalties[0]
    if dressage <= 0:
        return None
    # The string-table walk is the dressage-only fallback. Live boards are
    # parsed from the value stream, which can also see show jumping.
    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(event.token, level, rider_name, horse_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_name,
        horse_name=horse_name,
        event_name=f"{event.event_title} · {level}",
        event_date=event.event_date,
        level=level,
        country=event.country,
        dressage_score=dressage,
        show_jumping_penalties=0.0,
        cross_country_jump_penalties=0.0,
        cross_country_time_penalties=0.0,
        collected_at=collected_at,
        is_user_entered=False,
    )


def _parse_stream_entry(
    values: Sequence[str],
    bio_index: int,
    *,
    event: EventEntriesClass,
    level: str,
    collected_at: datetime,
) -> EventingResult | None:
    """Read one horse from the value stream immediately before its bio string."""

    horse_name = ""
    if bio_index > 0 and "\n" not in values[bio_index - 1]:
        horse_name = _clean_text(values[bio_index - 1])
    if not horse_name:
        horse_name = _clean_text(values[bio_index].split("\n", 1)[0])

    rider_name = ""
    seen_percentage = False
    dressage: float | None = None
    dressage_index: int | None = None
    window_start = max(0, bio_index - 40)
    for index in range(bio_index - 1, window_start - 1, -1):
        token = values[index]
        if token.startswith("com.kyler.ee.shared.ScoringBoardEntry"):
            break
        if STATUS_RE.match(_clean_text(token)):
            return None
        if not rider_name and token.startswith("java.util.ArrayList/") and index + 1 < bio_index:
            candidate = _clean_text(values[index + 1])
            if RIDER_RE.match(candidate):
                rider_name = candidate
        text = _clean_text(token)
        if PERCENT_RE.match(text):
            seen_percentage = True
            continue
        if seen_percentage and dressage is None and PENALTY_RE.match(text):
            dressage = round(float(text), 1)
            dressage_index = index
            break
    if not horse_name or not rider_name or dressage is None or dressage <= 0 or dressage_index is None:
        return None
    show_jumping = _show_jumping_penalties(values, dressage_index, dressage)
    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(event.token, level, rider_name, horse_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_name,
        horse_name=horse_name,
        event_name=f"{event.event_title} · {level}",
        event_date=event.event_date,
        level=level,
        country=event.country,
        dressage_score=dressage,
        show_jumping_penalties=show_jumping,
        cross_country_jump_penalties=0.0,
        cross_country_time_penalties=0.0,
        collected_at=collected_at,
        is_user_entered=False,
    )


def _show_jumping_penalties(values: Sequence[str], dressage_index: int, dressage: float) -> float:
    """Return stadium faults plus time penalties when the to-date total matches.

    Walking away from the dressage penalty, a published show-jumping row is
    an optional dressage rank, stadium faults, elapsed seconds, the time
    penalty, and the to-date score. Dressage-only rows do not have that total,
    so they stay at zero jumping penalties.
    """

    numbers: list[str] = []
    for index in range(dressage_index - 1, max(-1, dressage_index - 40), -1):
        token = values[index]
        if token.startswith("com.kyler.ee.shared.ScoringBoardEntry"):
            break
        if "\n" in token and HORSE_BIO_RE.search(token):
            break
        text = _clean_text(token)
        if not text or token.startswith("com.kyler.ee.shared.") or token.startswith("java."):
            continue
        if PERCENT_RE.match(text) or RIDER_RE.match(text):
            break
        if PENALTY_RE.match(text) or re.fullmatch(r"\d{1,3}", text):
            numbers.append(text)
            if len(numbers) >= 6:
                break
            continue
        # Rail-by-rail notes sit between the dressage rank and stadium faults.
        continue
    cursor = 0
    if (
        cursor + 1 < len(numbers)
        and re.fullmatch(r"\d{1,3}", numbers[cursor])
        and PENALTY_RE.match(numbers[cursor + 1])
    ):
        cursor += 1
    if cursor + 3 >= len(numbers):
        return 0.0
    jump = _one_decimal(numbers[cursor])
    elapsed = _whole_number(numbers[cursor + 1])
    time_penalties = _one_decimal(numbers[cursor + 2])
    to_date = _one_decimal(numbers[cursor + 3])
    if None in {jump, elapsed, time_penalties, to_date}:
        return 0.0
    assert jump is not None
    assert elapsed is not None
    assert time_penalties is not None
    assert to_date is not None
    if not 40 <= elapsed <= 200:
        return 0.0
    if round(dressage + jump + time_penalties, 1) != round(to_date, 1):
        return 0.0
    return round(jump + time_penalties, 1)


def _one_decimal(value: str) -> float | None:
    if PENALTY_RE.match(value) is None:
        return None
    return round(float(value), 1)


def _whole_number(value: str) -> int | None:
    if re.fullmatch(r"\d{1,3}", value) is None:
        return None
    return int(value)


def _level_from_strings(strings: Sequence[str]) -> str | None:
    for value in strings:
        if "\n" in value:
            continue
        match = LEVEL_RE.search(value)
        if match:
            return f"CCI{match.group(1)}*-{match.group(2).upper()}"
    return None


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"evententries:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Event Entries live eventing scores")
    parser.add_argument(
        "--stable-view-2026",
        action="store_true",
        help="Pull Stable View Oktoberfest 2026 scores from the public scoring boards",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.stable_view_2026:
        raise SystemExit("Specify --stable-view-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_stable_view_2026(collected_at=collected_at)
    print(f"Event Entries collect complete: results_collected={len(results)}")
    if args.dry_run:
        for result in sorted(results, key=lambda item: (item.level, item.finishing_score, item.rider_name)):
            print(
                f"{result.level} {result.rider_name} / {result.horse_name} "
                f"dr={result.dressage_score} sj={result.show_jumping_penalties} "
                f"xc={result.cross_country_jump_penalties}+{result.cross_country_time_penalties}"
            )
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
