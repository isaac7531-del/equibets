"""FEI search-page configuration and export normalization."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO

from equibets.results import EventingResult


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "fei_search_pages.json"
DEFAULT_COLLECTED_AT = "2026-05-14T00:00:00"
DEFAULT_SOURCE_PRIORITY = 0


@dataclass(frozen=True)
class FEIWorldRanking:
    """One FEI world-ranking row for rider form context."""

    ranking_name: str
    rank: int
    rider_name: str
    country: str
    points: float
    as_of: str
    source_url: str


def load_fei_search_pages(path: Path | str = DATA_FILE) -> dict[str, dict[str, str]]:
    """Load FEI search pages used for rider, horse, and calendar lookups."""

    with Path(path).open(encoding="utf-8") as pages_file:
        payload = json.load(pages_file)

    pages = payload.get("pages")
    if not isinstance(pages, dict):
        raise ValueError("pages must be an object")

    return {name: _validate_page(name, values) for name, values in pages.items()}


def load_fei_results_csv(csv_file: TextIO, *, collected_at: str = DEFAULT_COLLECTED_AT) -> list[EventingResult]:
    """Normalize rows exported from FEI search/results pages.

    Expected columns are intentionally plain so exports can be mapped from FEI
    result tables without coupling the app to the ASP.NET page structure.
    """

    return [
        EventingResult.from_mapping(_result_mapping(row, index, collected_at))
        for index, row in enumerate(csv.DictReader(csv_file), start=1)
    ]


def load_fei_world_rankings_csv(csv_file: TextIO) -> list[FEIWorldRanking]:
    """Normalize rows exported from the FEI world rankings page."""

    rankings = []
    for row in csv.DictReader(csv_file):
        rankings.append(
            FEIWorldRanking(
                ranking_name=_first_present(row, "ranking_name", "ranking", "list"),
                rank=int(_number(row, "rank", "position")),
                rider_name=_first_present(row, "rider_name", "person_name", "athlete"),
                country=_first_present(row, "country", "nf", "nation"),
                points=_number(row, "points", "score"),
                as_of=_first_present(row, "as_of", "date", "published_at"),
                source_url=load_fei_search_pages()["world_rankings"]["url"],
            )
        )

    return rankings


def _validate_page(name: str, values: object) -> dict[str, str]:
    if not isinstance(values, dict):
        raise ValueError(f"{name} must be an object")

    page = {
        "label": _required_str(values, "label"),
        "url": _required_str(values, "url"),
        "use": _required_str(values, "use"),
    }

    if not page["url"].startswith("https://data.fei.org/"):
        raise ValueError(f"{name} must use a data.fei.org URL")

    return page


def _result_mapping(row: dict[str, str], row_number: int, collected_at: str) -> dict[str, object]:
    rider_name = _first_present(row, "rider_name", "person_name", "athlete")
    horse_name = _first_present(row, "horse_name", "horse")
    event_name = _first_present(row, "event_name", "event")
    level = _first_present(row, "level", "competition_level")
    country = _first_present(row, "country", "nf", "nation")
    event_date = _first_present(row, "event_date", "date")
    source_record_id = row.get("source_record_id") or f"fei-export-{row_number}"

    return {
        "source_id": "data_fei",
        "source_record_id": source_record_id,
        "source_priority": DEFAULT_SOURCE_PRIORITY,
        "rider_name": rider_name,
        "horse_name": horse_name,
        "event_name": event_name,
        "event_date": _iso_date(event_date),
        "level": level,
        "country": country,
        "dressage_score": _number(row, "dressage_score", "dressage"),
        "show_jumping_penalties": _number(row, "show_jumping_penalties", "show_jumping", "sj"),
        "cross_country_jump_penalties": _number(
            row,
            "cross_country_jump_penalties",
            "cross_country_jump",
            "xc_jump",
        ),
        "cross_country_time_penalties": _number(
            row,
            "cross_country_time_penalties",
            "cross_country_time",
            "xc_time",
        ),
        "collected_at": collected_at,
        "is_user_entered": False,
    }


def _required_str(values: dict[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _first_present(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value and value.strip():
            return value.strip()
    raise ValueError(f"Missing required FEI export field: {' or '.join(keys)}")


def _number(row: dict[str, str], *keys: str) -> float:
    raw_value = _first_present(row, *keys)
    return float(raw_value)


def _iso_date(value: str) -> str:
    value = value.strip()
    for date_format in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, date_format).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unsupported FEI date format: {value}")
