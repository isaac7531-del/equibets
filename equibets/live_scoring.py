"""Refresh current-event result feeds into a live-scoring snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from .results import EventingResult, consolidate_results, predict_finishing_score
from .sources import DATA_FILE, EventSource, load_event_sources


DEFAULT_OUTPUT_FILE = Path("public/live_scores.json")
DEFAULT_HTTP_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class PullSummary:
    """Counters describing one live-scoring refresh."""

    discovered_payload_count: int
    pulled_result_count: int
    skipped_result_count: int
    source_ids: tuple[str, ...]


def refresh_live_scoring(
    resources: Sequence[str | Path],
    *,
    source_path: str | Path = DATA_FILE,
    collected_at: datetime | None = None,
    since: datetime | None = None,
    event_date_from: date | None = None,
    event_date_to: date | None = None,
) -> dict[str, Any]:
    """Pull result payloads and return a consolidated live-scoring snapshot.

    Resources can be local JSON files, directories containing JSON payloads, URLs,
    or manifest JSON files with ``result_urls``/``search_results`` entries. This
    keeps the search step provider-agnostic: a cron job can write search hits to a
    manifest, and this refresh turns those hits into normalized scoring data.
    """

    if not resources:
        raise ValueError("at least one result resource is required")

    collected_at = _normalize_datetime(collected_at or datetime.now(UTC))
    sources = load_event_sources(source_path)
    source_index = {source.id: source for source in sources}
    discovered_payloads = discover_payloads(resources)

    pulled_results: list[EventingResult] = []
    skipped_result_count = 0
    for payload_resource in discovered_payloads:
        payload = _read_json_resource(payload_resource)
        normalized_results, skipped = _normalize_payload_results(
            payload,
            source_index=source_index,
            collected_at=collected_at,
        )
        skipped_result_count += skipped
        for result in normalized_results:
            if since is not None and result.collected_at < _normalize_datetime(since):
                continue
            if event_date_from is not None and result.event_date < event_date_from:
                continue
            if event_date_to is not None and result.event_date > event_date_to:
                continue
            pulled_results.append(result)

    summary = PullSummary(
        discovered_payload_count=len(discovered_payloads),
        pulled_result_count=len(pulled_results),
        skipped_result_count=skipped_result_count,
        source_ids=tuple(sorted({result.source_id for result in pulled_results})),
    )
    return build_live_scoring_snapshot(pulled_results, summary=summary, collected_at=collected_at)


def discover_payloads(resources: Sequence[str | Path]) -> list[str]:
    """Search local paths and manifests for JSON result payloads."""

    discovered: list[str] = []
    visited: set[str] = set()

    def add_resource(resource: str | Path, base_resource: str | None = None) -> None:
        resource_text = _resolve_resource(str(resource), base_resource)
        if resource_text in visited:
            return
        visited.add(resource_text)

        if _is_url(resource_text):
            payload = _read_json_resource(resource_text)
            links = _extract_manifest_links(payload)
            if links:
                for link in links:
                    add_resource(link, resource_text)
                return
            discovered.append(resource_text)
            return

        path = Path(resource_text)
        if path.is_dir():
            for child in sorted(path.rglob("*.json")):
                add_resource(child)
            return
        if not path.exists():
            raise FileNotFoundError(f"result resource not found: {path}")

        payload = _read_json_resource(path)
        links = _extract_manifest_links(payload)
        if links:
            for link in links:
                add_resource(link, str(path))
            return
        discovered.append(str(path))

    for resource in resources:
        add_resource(resource)

    return discovered


def build_live_scoring_snapshot(
    results: Sequence[EventingResult],
    *,
    summary: PullSummary | None = None,
    collected_at: datetime | None = None,
) -> dict[str, Any]:
    """Create the JSON-serializable live-scoring artifact."""

    collected_at = _normalize_datetime(collected_at or datetime.now(UTC))
    consolidated = consolidate_results(list(results))
    predictions = _build_predictions(consolidated)
    source_ids = tuple(sorted({result.source_id for result in results}))
    summary = summary or PullSummary(
        discovered_payload_count=0,
        pulled_result_count=len(results),
        skipped_result_count=0,
        source_ids=source_ids,
    )

    return {
        "version": 1,
        "collected_at": _format_datetime(collected_at),
        "summary": {
            "discovered_payload_count": summary.discovered_payload_count,
            "pulled_result_count": summary.pulled_result_count,
            "consolidated_result_count": len(consolidated),
            "skipped_result_count": summary.skipped_result_count,
            "source_ids": list(summary.source_ids),
        },
        "results": [_result_to_mapping(result) for result in consolidated],
        "predictions": [_prediction_to_mapping(prediction) for prediction in predictions],
    }


def write_live_scoring_snapshot(snapshot: Mapping[str, Any], output_path: str | Path) -> None:
    """Write a live-scoring snapshot as pretty JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "resources",
        nargs="+",
        help="JSON files, directories, URLs, or search manifests to pull current-event results from.",
    )
    parser.add_argument(
        "--sources",
        default=str(DATA_FILE),
        help="Path to the event source registry JSON.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_FILE),
        help="Where to write the live scoring snapshot JSON.",
    )
    parser.add_argument(
        "--since",
        help="Only include results collected at or after this ISO timestamp.",
    )
    parser.add_argument(
        "--current-window-days",
        type=int,
        default=14,
        help="Include events from this many days before today.",
    )
    parser.add_argument(
        "--upcoming-window-days",
        type=int,
        default=7,
        help="Include events through this many days after today.",
    )
    args = parser.parse_args(argv)

    today = datetime.now(UTC).date()
    snapshot = refresh_live_scoring(
        args.resources,
        source_path=args.sources,
        since=_parse_datetime(args.since) if args.since else None,
        event_date_from=today - timedelta(days=args.current_window_days),
        event_date_to=today + timedelta(days=args.upcoming_window_days),
    )
    write_live_scoring_snapshot(snapshot, args.output)
    print(
        "Wrote live scoring snapshot with "
        f"{snapshot['summary']['consolidated_result_count']} consolidated results to {args.output}",
        file=sys.stderr,
    )
    return 0


def _normalize_payload_results(
    payload: Mapping[str, Any],
    *,
    source_index: Mapping[str, EventSource],
    collected_at: datetime,
) -> tuple[list[EventingResult], int]:
    results: list[EventingResult] = []
    skipped = 0

    source_defaults = {
        "source_id": payload.get("source_id"),
        "source_priority": payload.get("source_priority"),
        "collected_at": payload.get("collected_at"),
    }
    for record in _iter_result_records(payload):
        try:
            normalized = _normalize_result_record(
                record,
                source_defaults=source_defaults,
                source_index=source_index,
                collected_at=collected_at,
            )
            results.append(EventingResult.from_mapping(normalized))
        except (TypeError, ValueError):
            skipped += 1

    return results, skipped


def _iter_result_records(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for record in payload.get("results", []):
        if isinstance(record, Mapping):
            yield record

    for event in payload.get("events", []):
        if not isinstance(event, Mapping):
            continue
        event_defaults = {
            "source_id": event.get("source_id", payload.get("source_id")),
            "source_priority": event.get("source_priority", payload.get("source_priority")),
            "event_name": event.get("event_name", event.get("name")),
            "event_date": event.get("event_date", event.get("date")),
            "level": event.get("level"),
            "country": event.get("country"),
            "collected_at": event.get("collected_at", payload.get("collected_at")),
        }
        for record in event.get("results", []):
            if isinstance(record, Mapping):
                yield {**event_defaults, **record}


def _normalize_result_record(
    record: Mapping[str, Any],
    *,
    source_defaults: Mapping[str, Any],
    source_index: Mapping[str, EventSource],
    collected_at: datetime,
) -> dict[str, Any]:
    source_id = _first_value(record, source_defaults, "source_id")
    if not isinstance(source_id, str) or not source_id:
        raise ValueError("source_id is required")

    source = source_index.get(source_id)
    source_priority = _first_value(record, source_defaults, "source_priority")
    if source_priority is None and source is not None:
        source_priority = source.priority

    normalized: dict[str, Any] = {
        "source_id": source_id,
        "source_record_id": _string_or_none(record.get("source_record_id"))
        or _stable_record_id(record, source_id),
        "source_priority": source_priority,
        "rider_name": record.get("rider_name", record.get("rider")),
        "horse_name": record.get("horse_name", record.get("horse")),
        "event_name": record.get("event_name", record.get("event")),
        "event_date": record.get("event_date", record.get("date")),
        "level": record.get("level"),
        "country": record.get("country"),
        "dressage_score": record.get("dressage_score", record.get("dressage_penalties")),
        "show_jumping_penalties": record.get("show_jumping_penalties", record.get("sj_penalties", 0)),
        "cross_country_jump_penalties": record.get(
            "cross_country_jump_penalties",
            record.get("xc_jump_penalties", 0),
        ),
        "cross_country_time_penalties": record.get(
            "cross_country_time_penalties",
            record.get("xc_time_penalties", 0),
        ),
        "collected_at": record.get("collected_at")
        or source_defaults.get("collected_at")
        or _format_datetime(collected_at),
        "is_user_entered": record.get("is_user_entered", False),
    }

    if normalized["country"] is None and source is not None:
        normalized["country"] = _default_country(source)

    return normalized


def _extract_manifest_links(payload: Mapping[str, Any]) -> list[str]:
    links: list[str] = []
    for key in ("result_urls", "urls", "documents", "search_results"):
        value = payload.get(key)
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str):
                links.append(item)
            elif isinstance(item, Mapping) and isinstance(item.get("url"), str):
                links.append(item["url"])
    return links


def _read_json_resource(resource: str | Path) -> Mapping[str, Any]:
    if _is_url(str(resource)):
        request = Request(str(resource), headers={"User-Agent": "equibets-live-scoring/1.0"})
        with urlopen(request, timeout=DEFAULT_HTTP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    else:
        with Path(resource).open(encoding="utf-8") as resource_file:
            payload = json.load(resource_file)

    if not isinstance(payload, Mapping):
        raise ValueError(f"JSON payload must be an object: {resource}")
    return payload


def _build_predictions(consolidated_results: Sequence[EventingResult]) -> list[Any]:
    predictions = []
    seen_keys: set[str] = set()
    for result in sorted(consolidated_results, key=lambda item: (item.rider_name, item.horse_name)):
        if result.combination_key in seen_keys:
            continue
        seen_keys.add(result.combination_key)
        predictions.append(
            predict_finishing_score(
                list(consolidated_results),
                result.rider_name,
                result.horse_name,
            )
        )

    return sorted(predictions, key=lambda prediction: prediction.likely_finishing_score)


def _result_to_mapping(result: EventingResult) -> dict[str, Any]:
    return {
        "source_id": result.source_id,
        "source_record_id": result.source_record_id,
        "source_priority": result.source_priority,
        "rider_name": result.rider_name,
        "horse_name": result.horse_name,
        "event_name": result.event_name,
        "event_date": result.event_date.isoformat(),
        "level": result.level,
        "country": result.country,
        "dressage_score": result.dressage_score,
        "show_jumping_penalties": result.show_jumping_penalties,
        "cross_country_jump_penalties": result.cross_country_jump_penalties,
        "cross_country_time_penalties": result.cross_country_time_penalties,
        "finishing_score": result.finishing_score,
        "collected_at": _format_datetime(result.collected_at),
        "is_user_entered": result.is_user_entered,
    }


def _prediction_to_mapping(prediction: Any) -> dict[str, Any]:
    return {
        "rider_name": prediction.rider_name,
        "horse_name": prediction.horse_name,
        "likely_finishing_score": prediction.likely_finishing_score,
        "recent_result_count": prediction.recent_result_count,
        "best_recent_score": prediction.best_recent_score,
        "worst_recent_score": prediction.worst_recent_score,
        "source_ids": list(prediction.source_ids),
        "confidence": prediction.confidence,
    }


def _resolve_resource(resource: str, base_resource: str | None) -> str:
    if base_resource is None or _is_url(resource) or Path(resource).is_absolute():
        return resource
    if _is_url(base_resource):
        return urljoin(base_resource, resource)
    return str((Path(base_resource).parent / resource).resolve())


def _is_url(resource: str) -> bool:
    return urlparse(resource).scheme in {"http", "https"}


def _first_value(record: Mapping[str, Any], defaults: Mapping[str, Any], key: str) -> Any:
    return record.get(key) if record.get(key) is not None else defaults.get(key)


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _stable_record_id(record: Mapping[str, Any], source_id: str) -> str:
    parts = [
        source_id,
        str(record.get("event_date", record.get("date", ""))),
        str(record.get("event_name", record.get("event", ""))),
        str(record.get("level", "")),
        str(record.get("rider_name", record.get("rider", ""))),
        str(record.get("horse_name", record.get("horse", ""))),
    ]
    return "::".join(_slug(part) for part in parts if part)


def _default_country(source: EventSource) -> str | None:
    countries = [country for country in source.countries if not country.startswith("all_")]
    return countries[0] if len(countries) == 1 else None


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _format_datetime(value: datetime) -> str:
    return _normalize_datetime(value).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    return "".join(character.lower() if character.isalnum() else "-" for character in value).strip("-")


if __name__ == "__main__":
    raise SystemExit(main())
