"""Horse index records built from collected eventing results."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .results import EventingResult, load_results


DEFAULT_HORSE_INDEX_FILE = Path(__file__).resolve().parents[1] / "data" / "horse_index.json"


@dataclass(frozen=True)
class HorseIndexRecord:
    """A consolidated horse profile derived from official/public results."""

    horse_name: str
    countries: tuple[str, ...]
    riders: tuple[str, ...]
    levels: tuple[str, ...]
    source_ids: tuple[str, ...]
    first_seen_on: date
    last_seen_on: date
    latest_event_name: str
    result_count: int
    is_currently_eventing: bool


def build_horse_index(
    results: list[EventingResult],
    *,
    active_since: date | None = None,
) -> list[HorseIndexRecord]:
    """Build one record per horse from every collected eventing result."""

    if active_since is None:
        active_since = date.today() - timedelta(days=730)

    grouped: dict[str, list[EventingResult]] = {}
    for result in results:
        grouped.setdefault(_horse_key(result.horse_name), []).append(result)

    records: list[HorseIndexRecord] = []
    for horse_results in grouped.values():
        ordered = sorted(horse_results, key=lambda result: result.event_date)
        latest = ordered[-1]
        records.append(
            HorseIndexRecord(
                horse_name=latest.horse_name,
                countries=tuple(sorted({result.country for result in ordered if result.country})),
                riders=tuple(sorted({result.rider_name for result in ordered if result.rider_name})),
                levels=tuple(sorted({result.level for result in ordered if result.level})),
                source_ids=tuple(sorted({result.source_id for result in ordered if result.source_id})),
                first_seen_on=ordered[0].event_date,
                last_seen_on=latest.event_date,
                latest_event_name=latest.event_name,
                result_count=len(ordered),
                is_currently_eventing=latest.event_date >= active_since,
            )
        )

    return sorted(records, key=lambda record: (not record.is_currently_eventing, record.horse_name.lower()))


def save_horse_index(records: list[HorseIndexRecord], path: Path | str = DEFAULT_HORSE_INDEX_FILE) -> None:
    """Write horse index records as JSON."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "horse_count": len(records),
        "current_horse_count": sum(1 for record in records if record.is_currently_eventing),
        "horses": [horse_index_record_to_mapping(record) for record in records],
    }
    with output_path.open("w", encoding="utf-8") as index_file:
        json.dump(payload, index_file, indent=2, sort_keys=True)
        index_file.write("\n")


def horse_index_record_to_mapping(record: HorseIndexRecord) -> dict[str, object]:
    return {
        "horse_name": record.horse_name,
        "countries": list(record.countries),
        "riders": list(record.riders),
        "levels": list(record.levels),
        "source_ids": list(record.source_ids),
        "first_seen_on": record.first_seen_on.isoformat(),
        "last_seen_on": record.last_seen_on.isoformat(),
        "latest_event_name": record.latest_event_name,
        "result_count": record.result_count,
        "is_currently_eventing": record.is_currently_eventing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a horse index from collected eventing results")
    parser.add_argument("--results", type=Path, required=True, help="Input JSON result store")
    parser.add_argument("--output", type=Path, default=DEFAULT_HORSE_INDEX_FILE, help="Output JSON horse index")
    parser.add_argument("--active-window-days", type=int, default=730, help="Days since last start to mark active")
    args = parser.parse_args(argv)

    results = load_results(args.results)
    active_since = date.today() - timedelta(days=args.active_window_days)
    records = build_horse_index(results, active_since=active_since)
    save_horse_index(records, args.output)
    print(
        "Horse index complete: "
        f"horses={len(records)}, "
        f"currently_eventing={sum(1 for record in records if record.is_currently_eventing)}, "
        f"output={args.output}"
    )
    return 0


def _horse_key(horse_name: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in horse_name).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
