"""Collect live eventing scores from the public ShowConnect scoring API."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from equibets.live_scores import (
    build_live_score_payload,
    current_event_window,
    write_live_score_payload,
)
from equibets.rechenstelle import merge_into_store
from equibets.results import EventingResult


SOURCE_ID = "showconnect"
SOURCE_PRIORITY = 12
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SCORING_LIVE_URL = "https://scripts.showconnect.org/api/sc/event/{show_connect_id}/scoringLive"
SKIP_DIVISION_RE = re.compile(
    r"young event horse|\byeh\b|non-compete|non compete",
    re.IGNORECASE,
)
FEI_LEVEL_RE = re.compile(r"^CCI", re.IGNORECASE)

# Twin Rivers Fall International, 17–20 Sep 2026.
# HTML scoring pages are Squarespace shells; numeric scores come from the
# public scoringLive JSON.
TWIN_RIVERS_FALL_2026 = {
    "show_connect_id": 1193,
    "event_title": "Twin Rivers",
    "event_date": date(2026, 9, 17),
    "country": "USA",
}

# Spokane Sport Horse Fall Horse Trials, 24–27 Sep 2026 (USEA 19091).
# National horse-trial divisions on the same scoringLive document are skipped.
SPOKANE_FALL_2026 = {
    "show_connect_id": 1194,
    "event_title": "Spokane",
    "event_date": date(2026, 9, 24),
    "country": "USA",
}


@dataclass(frozen=True)
class ShowConnectEvent:
    """One ShowConnect event to ingest from scoringLive JSON."""

    show_connect_id: int
    event_title: str
    event_date: date
    country: str


def scoring_live_url(show_connect_id: int) -> str:
    """Return the public scoringLive URL for a ShowConnect event."""

    return SCORING_LIVE_URL.format(show_connect_id=show_connect_id)


def fetch_scoring_live(show_connect_id: int, *, timeout: float = 30.0) -> dict[str, Any]:
    """Fetch and decode a ShowConnect scoringLive payload."""

    url = scoring_live_url(show_connect_id)
    request = Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"ShowConnect scoringLive payload for {show_connect_id} is not an object")
    return payload


def parse_scoring_live(
    payload: Mapping[str, Any],
    *,
    event: ShowConnectEvent,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse scoringLive JSON into EventingResult rows with numeric dressage."""

    collected = collected_at or datetime.now(timezone.utc)
    divisions = {
        item.get("DivisionId"): item
        for item in payload.get("DivisionsList") or []
        if isinstance(item, Mapping)
    }
    results: list[EventingResult] = []
    for row in payload.get("ScoringList") or []:
        if not isinstance(row, Mapping):
            continue
        parsed = _parse_scoring_row(row, divisions=divisions, event=event, collected_at=collected)
        if parsed is not None:
            results.append(parsed)
    return results


def twin_rivers_fall_2026_event() -> ShowConnectEvent:
    """Return the Twin Rivers Fall 2026 ShowConnect event."""

    return ShowConnectEvent(**TWIN_RIVERS_FALL_2026)


def spokane_fall_2026_event() -> ShowConnectEvent:
    """Return the Spokane Fall 2026 ShowConnect event."""

    return ShowConnectEvent(**SPOKANE_FALL_2026)


def collect_events(
    events: Sequence[ShowConnectEvent],
    *,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Fetch and parse each configured ShowConnect event."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    results: list[EventingResult] = []
    for event in events:
        payload = fetch_scoring_live(event.show_connect_id)
        results.extend(parse_scoring_live(payload, event=event, collected_at=collected))
    return results


def _parse_scoring_row(
    row: Mapping[str, Any],
    *,
    divisions: Mapping[Any, Mapping[str, Any]],
    event: ShowConnectEvent,
    collected_at: datetime,
) -> EventingResult | None:
    division = divisions.get(row.get("DivisionId"), {})
    division_name = _clean_text(str(division.get("DivisionName") or ""))
    if not division_name or SKIP_DIVISION_RE.search(division_name):
        return None

    rider_name = _clean_text(str(row.get("RiderName") or ""))
    horse_name = _clean_text(str(row.get("HorseName") or ""))
    dressage = _parse_penalty(row.get("DressageScore"))
    if not rider_name or not horse_name or dressage is None:
        return None

    show_jumping = _sum_penalties(row.get("SJJumpPenalty"), row.get("SJTimePenalty"))
    xc_jump = _parse_penalty(row.get("XCJumpPenalty")) or 0.0
    xc_time = _parse_penalty(row.get("XCTimePenalty")) or 0.0
    level = _normalize_level(division_name)
    if not FEI_LEVEL_RE.match(level):
        return None
    start_no = row.get("Pinny") if row.get("Pinny") not in (None, "") else row.get("CRID")
    record_id = _record_id(event.show_connect_id, level, start_no, rider_name, horse_name)

    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=record_id,
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


def _normalize_level(division_name: str) -> str:
    level = _clean_text(division_name)
    level = re.sub(r"-Short\b", "-S", level, flags=re.IGNORECASE)
    level = re.sub(r"-Long\b", "-L", level, flags=re.IGNORECASE)
    return level


def _sum_penalties(*values: object) -> float:
    total = 0.0
    for value in values:
        parsed = _parse_penalty(value)
        if parsed is not None:
            total += parsed
    return round(total, 1)


def _parse_penalty(value: object) -> float | None:
    """Parse a numeric penalty, ignoring placeholders and status letters."""

    if value is None:
        return None
    text = _clean_text(str(value))
    if not text or text == "--" or re.search(r"[A-Za-z]", text):
        return None
    normalized = text.replace(",", "")
    try:
        return round(float(normalized), 1)
    except ValueError:
        return None


def _clean_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"showconnect:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect ShowConnect live eventing scores")
    parser.add_argument(
        "--twin-rivers-2026",
        action="store_true",
        help="Pull Twin Rivers Fall 2026 scores from the public scoringLive API",
    )
    parser.add_argument(
        "--spokane-2026",
        action="store_true",
        help="Pull Spokane Fall 2026 CCI scores from the public scoringLive API",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    events: list[ShowConnectEvent] = []
    if args.twin_rivers_2026:
        events.append(twin_rivers_fall_2026_event())
    if args.spokane_2026:
        events.append(spokane_fall_2026_event())
    if not events:
        raise SystemExit("Specify --twin-rivers-2026 and/or --spokane-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_events(events, collected_at=collected_at)
    print(
        "ShowConnect collect complete: "
        f"events={len(events)}, results_collected={len(results)}"
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
