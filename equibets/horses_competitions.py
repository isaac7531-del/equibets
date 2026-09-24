"""Collect live eventing scores from the public Horses & Competitions API.

The public ranking used by ``/live/event/<id>/`` is
``https://api.horses-and-competitions.com/fr/api/v1/event/<id>/show/<n>/ranking``.
Organizer ``gestion`` endpoints are not used. Rows stay out of the store until
dressage has a numeric penalty, so unpublished start lists are not ingested.
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


SOURCE_ID = "horses_competitions"
SOURCE_PRIORITY = 7
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
API_ROOT = "https://api.horses-and-competitions.com/fr/api/v1"
FEI_LEVEL_RE = re.compile(r"^CCI", re.IGNORECASE)
STATUS_RE = re.compile(r"[A-Za-z]")

# Le Concours Complet International de Lignières, 23–27 Sep 2026.
# Public event 4640. Dressage for CCI2*-L opened on 23 Sep; the other FEI
# classes on this event stay unscored until their dressage penalties publish.
LIGNIERES_SEP_2026 = {
    "event_id": 4640,
    "event_title": "Lignières",
    "country": "FRA",
}


@dataclass(frozen=True)
class HorsesCompetitionEvent:
    """One Horses & Competitions event whose public class rankings can be ingested."""

    event_id: int
    event_title: str
    country: str


def ranking_url(event_id: int, show_number: int) -> str:
    """Return the public class ranking URL."""

    return f"{API_ROOT}/event/{event_id}/show/{show_number}/ranking"


def fetch_ranking(event_id: int, show_number: int, *, timeout: float = 30.0) -> dict[str, Any]:
    """Fetch one public class ranking document."""

    url = ranking_url(event_id, show_number)
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Horses & Competitions ranking for {event_id}/{show_number} is not an object")
    return payload


def fetch_show_numbers(event_id: int, *, timeout: float = 30.0) -> list[int]:
    """Return public show numbers advertised on the event document."""

    url = f"{API_ROOT}/event/{event_id}"
    request = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"Failed to fetch {url}: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Horses & Competitions event {event_id} is not an object")
    shows = payload.get("shows")
    numbers: list[int] = []
    if isinstance(shows, dict):
        for day_shows in shows.values():
            if not isinstance(day_shows, list):
                continue
            for show in day_shows:
                if not isinstance(show, Mapping):
                    continue
                number = _show_number(show.get("id"))
                if number is not None:
                    numbers.append(number)
    return numbers


def parse_ranking(
    payload: Mapping[str, Any],
    *,
    event: HorsesCompetitionEvent,
    collected_at: datetime | None = None,
) -> list[EventingResult]:
    """Parse a public ranking into rows that already have a dressage penalty."""

    show = payload.get("show")
    ranking = payload.get("ranking")
    if not isinstance(show, Mapping) or not isinstance(ranking, list):
        return []
    level = _clean_text(show.get("name"))
    if not level or not FEI_LEVEL_RE.match(level):
        return []
    event_date = _parse_date(show.get("date"))
    if event_date is None:
        return []

    collected = collected_at or datetime.now(timezone.utc)
    results: list[EventingResult] = []
    for row in ranking:
        if not isinstance(row, Mapping):
            continue
        parsed = _parse_row(
            row,
            event=event,
            level=level,
            event_date=event_date,
            collected_at=collected,
        )
        if parsed is not None:
            results.append(parsed)
    return results


def collect_lignieres_2026(*, collected_at: datetime | None = None) -> list[EventingResult]:
    """Fetch and parse scored FEI classes at Lignières 2026."""

    event = lignieres_sep_2026_event()
    collected = collected_at or datetime.now(timezone.utc).replace(microsecond=0)
    results: list[EventingResult] = []
    for show_number in fetch_show_numbers(event.event_id):
        payload = fetch_ranking(event.event_id, show_number)
        results.extend(parse_ranking(payload, event=event, collected_at=collected))
    return results


def lignieres_sep_2026_event() -> HorsesCompetitionEvent:
    """Return the Lignières September 2026 public event."""

    return HorsesCompetitionEvent(**LIGNIERES_SEP_2026)


def _parse_row(
    row: Mapping[str, Any],
    *,
    event: HorsesCompetitionEvent,
    level: str,
    event_date: date,
    collected_at: datetime,
) -> EventingResult | None:
    if row.get("outOfRank") is True:
        return None
    result = row.get("result")
    if not isinstance(result, Mapping):
        return None
    test = result.get("test")
    if not isinstance(test, Mapping):
        return None
    dressage = test.get("dressage")
    if not isinstance(dressage, Mapping):
        return None
    if _status_label(dressage.get("indice_label")) or _status_label(result.get("total_label")):
        return None
    dressage_score = _scored_dressage(dressage)
    if dressage_score is None:
        return None

    rider = row.get("rider")
    horse = row.get("horse")
    if not isinstance(rider, Mapping) or not isinstance(horse, Mapping):
        return None
    rider_name = _rider_name(rider)
    horse_name = _clean_text(horse.get("name"))
    if not rider_name or not horse_name:
        return None

    return EventingResult(
        source_id=SOURCE_ID,
        source_record_id=_record_id(event.event_id, level, row.get("bib"), rider_name, horse_name),
        source_priority=SOURCE_PRIORITY,
        rider_name=rider_name,
        horse_name=horse_name,
        event_name=f"{event.event_title} · {level}",
        event_date=event_date,
        level=level,
        country=event.country,
        dressage_score=dressage_score,
        show_jumping_penalties=_show_jumping_penalties(test.get("jumping")),
        cross_country_jump_penalties=_cross_country_jump_penalties(test.get("eventing")),
        cross_country_time_penalties=_cross_country_time_penalties(test.get("eventing")),
        collected_at=collected_at,
        is_user_entered=False,
    )


def _scored_dressage(dressage: Mapping[str, Any]) -> float | None:
    """Return dressage penalties once the class has published a percentage."""

    percentage = _parse_number(dressage.get("total_percent"))
    total = _parse_number(dressage.get("total"))
    if percentage is None or percentage <= 0 or total is None:
        return None
    return round(total, 1)


def _show_jumping_penalties(value: object) -> float:
    if not isinstance(value, list):
        return 0.0
    total = 0.0
    for round_score in value:
        if not isinstance(round_score, Mapping):
            continue
        penalties = _parse_number(round_score.get("total"))
        if penalties is None:
            jump = _parse_number(round_score.get("pts")) or 0.0
            time = _parse_number(round_score.get("pts_time")) or 0.0
            penalties = jump + time
        total += penalties
    return round(total, 1)


def _cross_country_jump_penalties(value: object) -> float:
    if not isinstance(value, Mapping):
        return 0.0
    return round(_parse_number(value.get("pts")) or 0.0, 1)


def _cross_country_time_penalties(value: object) -> float:
    if not isinstance(value, Mapping):
        return 0.0
    return round(_parse_number(value.get("pts_time")) or 0.0, 1)


def _rider_name(rider: Mapping[str, Any]) -> str:
    name = _clean_text(f"{_clean_text(rider.get('firstname'))} {_clean_text(rider.get('lastname'))}")
    nation = _clean_text(rider.get("nation")).upper()
    if name and nation:
        return f"{name} ({nation})"
    return name


def _status_label(value: object) -> bool:
    text = _clean_text(value)
    return bool(text and STATUS_RE.search(text))


def _show_number(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    text = _clean_text(value)
    if text.isdigit():
        return int(text)
    return None


def _parse_date(value: object) -> date | None:
    text = _clean_text(value)
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_number(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _clean_text(value)
    if not text or STATUS_RE.search(text):
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def _record_id(*parts: object) -> str:
    digest = hashlib.sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:16]
    return f"horses_competitions:{digest}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Horses & Competitions live eventing scores")
    parser.add_argument(
        "--lignieres-2026",
        action="store_true",
        help="Pull Lignières September 2026 scores from the public ranking API",
    )
    parser.add_argument("--output", type=Path, default=Path("data/fei_results.json"))
    parser.add_argument("--live-output", type=Path, default=Path("src/data/live_scores.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.lignieres_2026:
        raise SystemExit("Specify --lignieres-2026")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0)
    results = collect_lignieres_2026(collected_at=collected_at)
    print(f"Horses & Competitions collect complete: results_collected={len(results)}")
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
