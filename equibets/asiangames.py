"""Collect Asian Games eventing scores from the public results API.

FEI event detail pages are challenge-blocked while the Games are running.
Individual phase scores are published at
``https://back.results.asiangames2026.org`` for dressage, show jumping, and
cross-country. Team classifications repeat the same combinations and are not
ingested. Rows leave the scored field when a phase marks them EL/RT, and
cross-country rows are stored only after both jump and time penalties exist.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import zlib
from collections.abc import Mapping, Sequence
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


SOURCE_ID = "asiangames"
SOURCE_PRIORITY = 6
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
RESULTS_URL = "https://back.results.asiangames2026.org/s/AG2026/en/EQU/results/{code}"
DRESSAGE_CODE = "O.EVENINDV----------.DRSS.000100--"
JUMPING_CODE = "O.EVENINDV----------.JMP-.000300--"
CROSS_COUNTRY_CODE = "O.EVENINDV----------.XC--.000200--"
SKIP_IRM = {"EL", "RT", "WD", "RET", "DSQ", "DNS"}

# 20th Asian Games eventing, JRA Equestrian Park, Tokyo. Dressage and the
# first jumping round opened on 22 Sep 2026; cross-country is 23 Sep 2026.
ASIAN_GAMES_EVENTING_2026 = {
    "event_name": "Asian Games · Eventing Individual",
    "level": "Eventing Individual",
    "event_date": date(2026, 9, 22),
    "country": "JPN",
}


def results_url(code: str) -> str:
    """Return the public individual-phase results URL."""

    return RESULTS_URL.format(code=code)


def fetch_results(code: str, *, timeout: float = 30.0) -> dict[str, Any]:
    """Fetch one Asian Games results document."""

    url = results_url(code)
    request = Request(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = _decode_body(response.read())
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Asian Games results payload for {code} is not an object")
    return payload


def parse_individual_results(
    dressage: Mapping[str, Any],
    jumping: Mapping[str, Any],
    cross_country: Mapping[str, Any],
    *,
    event_name: str,
    level: str,
    event_date: date,
    country: str,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Join individual phase documents into one eventing result per combination."""

    collected = collected_at or datetime.now(timezone.utc)
    dressage_rows = _competitors_by_reg(dressage)
    jumping_rows = _competitors_by_reg(jumping)
    cross_country_rows = _competitors_by_reg(cross_country)
    results: list[EventingResult] = []
    for reg, dressage_row in dressage_rows.items():
        parsed = _parse_combination(
            reg,
            dressage_row,
            jumping_rows.get(reg),
            cross_country_rows.get(reg),
            event_name=event_name,
            level=level,
            event_date=event_date,
            country=country,
            collected_at=collected,
        )
        if parsed is not None:
            results.append(parsed)
    return results


def collect_asian_games_2026(*, collected_at: datetime | None = None) -> list[EventingResult]:
    """Fetch and parse the 2026 Asian Games individual eventing phases."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    event = ASIAN_GAMES_EVENTING_2026
    return parse_individual_results(
        fetch_results(DRESSAGE_CODE),
        fetch_results(JUMPING_CODE),
        fetch_results(CROSS_COUNTRY_CODE),
        event_name=str(event["event_name"]),
        level=str(event["level"]),
        event_date=event["event_date"],
        country=str(event["country"]),
        collected_at=collected,
    )


def _parse_combination(
    reg: str,
    dressage_row: Mapping[str, Any],
    jumping_row: Mapping[str, Any] | None,
    cross_country_row: Mapping[str, Any] | None,
    *,
    event_name: str,
    level: str,
    event_date: date,
    country: str,
    collected_at: datetime,
) -> EventingResult | None:
    if _skipped_irm(dressage_row) or _skipped_irm(jumping_row) or _skipped_irm(cross_country_row):
        return None
    dressage_score = _parse_number(dressage_row.get("Result"))
    if dressage_score is None:
        return None
    cross_country_fields = _extension_map(cross_country_row)
    xc_jump = _parse_number(cross_country_fields.get("PEN_JUMP"))
    xc_time = _parse_number(cross_country_fields.get("PEN_TIME"))
    if xc_jump is None or xc_time is None:
        return None

    horse_name = _clean_text(_extension_map(dressage_row).get("HORSE"))
    rider_name = _clean_text(dressage_row.get("Name"))
    if not horse_name or not rider_name:
        return None
    show_jumping = _show_jumping_penalties(jumping_row)
    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(reg, horse_name, rider_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_name,
        horse_name=horse_name,
        event_name=event_name,
        event_date=event_date,
        level=level,
        country=country,
        dressage_score=dressage_score,
        show_jumping_penalties=show_jumping,
        cross_country_jump_penalties=xc_jump,
        cross_country_time_penalties=xc_time,
        collected_at=collected_at,
        is_user_entered=False,
    )


def _show_jumping_penalties(row: Mapping[str, Any] | None) -> float:
    fields = _extension_map(row)
    total = _parse_number(fields.get("TOTAL_PENALTIES"))
    if total is not None:
        return total
    jump = _parse_number(fields.get("PEN_JUMP"))
    time = _parse_number(fields.get("PEN_TIME"))
    if jump is None and time is None:
        return 0.0
    return round((jump or 0.0) + (time or 0.0), 1)


def _competitors_by_reg(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = payload.get("Competitors")
    if not isinstance(rows, list):
        return {}
    indexed: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        reg = _clean_text(row.get("Reg"))
        if reg:
            indexed[reg] = row
    return indexed


def _extension_map(row: Mapping[str, Any] | None) -> dict[str, str]:
    if row is None:
        return {}
    extensions = row.get("Extensions")
    if not isinstance(extensions, list):
        return {}
    values: dict[str, str] = {}
    for item in extensions:
        if not isinstance(item, Mapping):
            continue
        code = item.get("Code")
        if not isinstance(code, str) or not code or code in values:
            continue
        value = item.get("Value")
        values[code] = "" if value is None else str(value)
    return values


def _skipped_irm(row: Mapping[str, Any] | None) -> bool:
    if row is None:
        return False
    return str(row.get("IRM") or "").upper() in SKIP_IRM


def _decode_body(raw: bytes) -> Any:
    """Decode JSON, including gzip, zlib, and the API's UTF-8-wrapped zlib."""

    if raw.startswith(b"\x1f\x8b"):
        raw = gzip.decompress(raw)
    candidates = [raw]
    if raw[:1] == b"\x78":
        try:
            candidates.insert(0, zlib.decompress(raw))
        except zlib.error:
            recovered = zlib.decompress(raw.decode("utf-8").encode("latin-1"))
            candidates.insert(0, recovered)
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    raise RuntimeError("Asian Games results payload was not JSON")


def _parse_number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 1)
    text = _clean_text(str(value))
    if not text or re.search(r"[A-Za-z]", text):
        return None
    try:
        return round(float(text.replace(",", ".")), 1)
    except ValueError:
        return None


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"asiangames:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Asian Games eventing scores")
    parser.add_argument(
        "--asian-games-2026",
        action="store_true",
        help="Pull 2026 Asian Games individual eventing phase scores",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.asian_games_2026:
        raise SystemExit("Specify --asian-games-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_asian_games_2026(collected_at=collected_at)
    print(f"Asian Games collect complete: results_collected={len(results)}")
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
