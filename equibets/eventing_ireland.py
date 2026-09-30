"""Collect live eventing scores from the public Eventing Ireland results API.

Class results are published at
``https://api.eventingireland.com/public/event/class/results/<classId>``.
Dressage penalties are ``drscore`` once that value is positive. ``drpen`` stays
0 while those penalties are already on the public board, so it is not the
ingest gate. Jumping and cross-country stay 0 until those cells are numeric.
"""

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


SOURCE_ID = "eventing_ireland"
SOURCE_PRIORITY = 9
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
RESULTS_URL = "https://api.eventingireland.com/public/event/class/results/{class_id}"
LEVEL_RE = re.compile(r"(CCI[O]?\d\*(?:-NC)?-(?:S|L|Intro))", re.IGNORECASE)
SKIP_STATUS = {"EL", "RT", "WD", "RET", "DSQ", "DNS", "E", "R", "RF", "MR", "HC"}
NATIONS = {
    "AE": "UAE",
    "AR": "ARG",
    "AT": "AUT",
    "AU": "AUS",
    "BE": "BEL",
    "BR": "BRA",
    "CA": "CAN",
    "CH": "SUI",
    "CL": "CHI",
    "CN": "CHN",
    "CZ": "CZE",
    "DE": "GER",
    "DK": "DEN",
    "ES": "ESP",
    "FI": "FIN",
    "FR": "FRA",
    "GB": "GBR",
    "HK": "HKG",
    "HU": "HUN",
    "IE": "IRL",
    "IN": "IND",
    "IT": "ITA",
    "JP": "JPN",
    "KR": "KOR",
    "LU": "LUX",
    "MX": "MEX",
    "NL": "NED",
    "NO": "NOR",
    "NZ": "NZL",
    "PL": "POL",
    "PT": "POR",
    "QA": "QAT",
    "SA": "KSA",
    "SE": "SWE",
    "SG": "SGP",
    "TH": "THA",
    "US": "USA",
    "UY": "URU",
    "ZA": "RSA",
}

# Ballindenisk International 2, 23–27 Sep 2026. Eventing Ireland event 9688.
# The event document URL is not public. These class ids are the CCI sections.
BALLINDENISK_SEP_2026 = {
    "event_title": "Ballindenisk",
    "country": "IRL",
    "class_ids": (28578, 28581, 28579, 28582, 28580, 28583, 28584),
}


@dataclass(frozen=True)
class EventingIrelandClass:
    """One public Eventing Ireland class results document."""

    class_id: int
    event_title: str
    country: str


def results_url(class_id: int) -> str:
    """Return the public class results URL."""

    return RESULTS_URL.format(class_id=class_id)


def fetch_class_results(class_id: int, *, timeout: float = 30.0) -> dict[str, Any]:
    """Fetch one public class results document."""

    url = results_url(class_id)
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Eventing Ireland class {class_id} is not an object")
    return payload


def parse_class_results(
    payload: Mapping[str, Any],
    *,
    event: EventingIrelandClass,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse class results into rows that already have a dressage penalty."""

    records = payload.get("records")
    if not isinstance(records, list):
        return []
    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for record in records:
        if not isinstance(record, Mapping):
            continue
        parsed = _parse_record(record, event=event, collected_at=collected)
        if parsed is not None:
            results.append(parsed)
    return results


def collect_ballindenisk_2026(*, collected_at: datetime | None = None) -> list[EventingResult]:
    """Fetch and parse scored CCI classes at Ballindenisk International 2."""

    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    event = ballindenisk_sep_2026_event()
    results: list[EventingResult] = []
    for class_id in event_class_ids():
        payload = fetch_class_results(class_id)
        results.extend(
            parse_class_results(
                payload,
                event=EventingIrelandClass(class_id, event.event_title, event.country),
                collected_at=collected,
            )
        )
    return results


def ballindenisk_sep_2026_event() -> EventingIrelandClass:
    """Return the Ballindenisk September 2026 public event label."""

    return EventingIrelandClass(
        class_id=0,
        event_title=str(BALLINDENISK_SEP_2026["event_title"]),
        country=str(BALLINDENISK_SEP_2026["country"]),
    )


def event_class_ids() -> tuple[int, ...]:
    """Return the Ballindenisk CCI class ids."""

    class_ids = BALLINDENISK_SEP_2026["class_ids"]
    if not isinstance(class_ids, tuple):
        raise RuntimeError("Ballindenisk class ids are not configured")
    return class_ids


def _parse_record(
    record: Mapping[str, Any],
    *,
    event: EventingIrelandClass,
    collected_at: datetime,
) -> EventingResult | None:
    if record.get("HC") is True:
        return None
    status = _clean_text(record.get("drstatus")).upper()
    if status in SKIP_STATUS:
        return None
    level = _level(record.get("classname"))
    event_date = _parse_date(record.get("eventdate"))
    if level is None or event_date is None:
        return None
    dressage = _required_penalty(record.get("drscore"))
    if dressage is None or dressage <= 0:
        return None
    show_jumping = _phase_total(record.get("sjjumppen"), record.get("sjtimepen"))
    cross_country_jump = _phase_penalty(record.get("xcjumppen"))
    cross_country_time = _phase_penalty(record.get("xctimepen"))
    if None in {show_jumping, cross_country_jump, cross_country_time}:
        return None

    rider_name = _rider_name(record.get("ridername"), record.get("ridernationality"))
    horse_name = _clean_text(record.get("horsename"))
    if not rider_name or not horse_name:
        return None
    assert show_jumping is not None
    assert cross_country_jump is not None
    assert cross_country_time is not None
    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(event.class_id, level, record.get("resultid"), rider_name, horse_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_name,
        horse_name=horse_name,
        event_name=f"{event.event_title} · {level}",
        event_date=event_date,
        level=level,
        country=event.country,
        dressage_score=dressage,
        show_jumping_penalties=show_jumping,
        cross_country_jump_penalties=cross_country_jump,
        cross_country_time_penalties=cross_country_time,
        collected_at=collected_at,
        is_user_entered=False,
    )


def _level(value: object) -> str | None:
    match = LEVEL_RE.search(_clean_text(value))
    if match is None:
        return None
    return match.group(1).upper().replace("INTRO", "Intro")


def _rider_name(name: object, nationality: object) -> str:
    rider = _clean_text(name)
    nation = _nation(nationality)
    if rider and nation:
        return f"{rider} ({nation})"
    return rider


def _nation(value: object) -> str:
    text = _clean_text(value).upper()
    if not text:
        return ""
    if len(text) == 3:
        return text
    return NATIONS.get(text, text)


def _required_penalty(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return round(float(value), 1)
    text = _clean_text(value)
    if not text or text in {"-", "--"} or re.search(r"[A-Za-z]", text):
        return None
    try:
        return round(float(text.replace(",", ".")), 1)
    except ValueError:
        return None


def _phase_penalty(value: object) -> float | None:
    """Return 0 before a phase publishes, or None when the cell is a status."""

    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return round(float(value), 1)
    text = _clean_text(value)
    if not text or text in {"-", "--"}:
        return 0.0
    if re.search(r"[A-Za-z]", text):
        return None
    try:
        return round(float(text.replace(",", ".")), 1)
    except ValueError:
        return None


def _phase_total(*values: object) -> float | None:
    total = 0.0
    for value in values:
        parsed = _phase_penalty(value)
        if parsed is None:
            return None
        total += parsed
    return round(total, 1)


def _parse_date(value: object) -> date | None:
    text = _clean_text(value)
    if len(text) >= 10:
        text = text[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"eventing_ireland:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Eventing Ireland live eventing scores")
    parser.add_argument(
        "--ballindenisk-2026",
        action="store_true",
        help="Pull Ballindenisk September 2026 CCI scores from the public class API",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.ballindenisk_2026:
        raise SystemExit("Specify --ballindenisk-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_ballindenisk_2026(collected_at=collected_at)
    print(f"Eventing Ireland collect complete: results_collected={len(results)}")
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
