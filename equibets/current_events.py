"""Current-event search and live-result pull helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from equibets.results import EventingResult
from equibets.sources import DATA_FILE, EventSource, load_event_sources, sources_for_region


@dataclass(frozen=True)
class CurrentEventQuery:
    """Search terms for finding current public eventing results."""

    event_name: str = ""
    rider_name: str = ""
    horse_name: str = ""
    region: str = "global"
    year: int | None = None


@dataclass(frozen=True)
class CurrentEventSearch:
    """A source-prioritized public search URL."""

    source_id: str
    source_name: str
    source_priority: int
    query: str
    search_url: str


def build_current_event_searches(
    query: CurrentEventQuery,
    *,
    path: Path | str = DATA_FILE,
    limit: int = 5,
) -> list[CurrentEventSearch]:
    """Build source-prioritized searches for fresh public results."""

    searches: list[CurrentEventSearch] = []
    for source in _sources_for_query_region(query.region, path):
        terms = [
            query.event_name.strip(),
            query.rider_name.strip(),
            query.horse_name.strip(),
            "eventing results",
            str(query.year or datetime.now().year),
            source.name,
            _site_filter(source),
        ]
        search_query = " ".join(term for term in terms if term)
        searches.append(
            CurrentEventSearch(
                source_id=source.id,
                source_name=source.name,
                source_priority=source.priority,
                query=search_query,
                search_url=f"https://duckduckgo.com/?q={quote_plus(search_query)}",
            )
        )

    return searches[:limit]


def pull_results_from_url(url: str, *, timeout: float = 15) -> list[EventingResult]:
    """Pull a JSON result feed and normalize it into EventingResult records."""

    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)

    return results_from_payload(payload)


def results_from_payload(payload: object) -> list[EventingResult]:
    """Normalize a result feed payload into EventingResult records."""

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
        records = payload["results"]
    else:
        records = []

    return [
        EventingResult.from_mapping(record)
        for record in records
        if isinstance(record, dict)
    ]


def searches_as_dicts(searches: list[CurrentEventSearch]) -> list[dict[str, object]]:
    """Serialize searches for command-line or automation output."""

    return [asdict(search) for search in searches]


def _sources_for_query_region(region: str, path: Path | str) -> list[EventSource]:
    normalized_region = region.lower().replace(" ", "_")
    if normalized_region == "global":
        sources = load_event_sources(path)
    else:
        sources = sources_for_region(normalized_region, path=path)

    return [
        source
        for source in sources
        if source.status in {"active", "planned"}
    ]


def _site_filter(source: EventSource) -> str:
    if not source.base_url:
        return ""

    host = urlparse(source.base_url).netloc
    return f"site:{host}" if host else ""
