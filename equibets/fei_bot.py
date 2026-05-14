"""FEI Data crawler and JSON result store.

The FEI site is an ASP.NET application, so the crawler preserves hidden form
fields from search pages and follows the event/result links discovered in the
returned HTML instead of relying on undocumented query parameters.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, build_opener

from equibets.results import EventingResult, consolidate_results


BASE_URL = "https://data.fei.org/"
CALENDAR_SEARCH_URL = urljoin(BASE_URL, "Calendar/Search.aspx")
PERSON_SEARCH_URL = urljoin(BASE_URL, "Person/Search.aspx")
HORSE_SEARCH_URL = urljoin(BASE_URL, "Horse/Search.aspx")
DEFAULT_RESULTS_FILE = Path(__file__).resolve().parents[1] / "data" / "fei_results.json"


@dataclass(frozen=True)
class FeiEvent:
    """A calendar event discovered from FEI Data."""

    source_event_id: str
    name: str
    url: str
    start_date: date | None = None
    end_date: date | None = None
    country: str = ""
    discipline: str = "Eventing"
    level: str = ""


@dataclass(frozen=True)
class FeiCrawlSummary:
    """Counts reported by one crawl run."""

    events_found: int
    events_opened: int
    result_pages_opened: int
    results_collected: int
    results_verified: int
    results_rejected: int


@dataclass(frozen=True)
class _Link:
    text: str
    href: str


@dataclass(frozen=True)
class _Cell:
    text: str
    links: tuple[_Link, ...]
    is_header: bool


@dataclass(frozen=True)
class _Row:
    cells: tuple[_Cell, ...]


@dataclass(frozen=True)
class _Table:
    rows: tuple[_Row, ...]


class FeiHttpClient:
    """Small HTTP client with cookie, rate-limit, and ASP.NET form support."""

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        user_agent: str = "EquibetsFEIBot/0.1",
        cookie: str | None = None,
        rate_limit_seconds: float = 1.0,
    ) -> None:
        self.base_url = base_url
        self.user_agent = user_agent
        self.cookie = cookie
        self.rate_limit_seconds = rate_limit_seconds
        self._opener = build_opener()
        self._last_request_at = 0.0

    def get(self, url: str) -> str:
        """Fetch a page as text."""

        return self._open(url, None)

    def post(self, url: str, data: Mapping[str, str]) -> str:
        """Submit a form as application/x-www-form-urlencoded."""

        body = urlencode(data).encode("utf-8")
        return self._open(url, body)

    def _open(self, url: str, body: bytes | None) -> str:
        wait_for = self.rate_limit_seconds - (time.monotonic() - self._last_request_at)
        if wait_for > 0:
            time.sleep(wait_for)

        headers = {"User-Agent": self.user_agent}
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        if self.cookie:
            headers["Cookie"] = self.cookie

        request = Request(url, data=body, headers=headers, method="POST" if body else "GET")
        try:
            with self._opener.open(request, timeout=45) as response:
                self._last_request_at = time.monotonic()
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, "replace")
        except HTTPError as exc:
            message = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"FEI request failed: {exc.code} {exc.reason}: {url}\n{message}") from exc


class FeiDataBot:
    """Collect eventing results from FEI calendar event pages."""

    def __init__(
        self,
        client: FeiHttpClient,
        *,
        verifier: "FeiVerifier | None" = None,
        raw_dir: Path | str | None = None,
    ) -> None:
        self.client = client
        self.verifier = verifier
        self.raw_dir = Path(raw_dir) if raw_dir else None

    def search_calendar(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        form_fields: Mapping[str, str] | None = None,
    ) -> list[FeiEvent]:
        """Submit the FEI calendar search page and return discovered events."""

        search_page = self.client.get(CALENDAR_SEARCH_URL)
        form = extract_form_fields(search_page)
        if start_date:
            start_value = start_date.isoformat()
            if not _set_matching_field(form, ("date", "start"), start_value):
                _set_matching_field(form, ("date", "from"), start_value)
        if end_date:
            end_value = end_date.isoformat()
            if not _set_matching_field(form, ("date", "end"), end_value):
                _set_matching_field(form, ("date", "to"), end_value)
        _set_matching_field(form, ("discipline",), "Eventing")
        _set_matching_field(form, ("search",), "Search")
        if form_fields:
            form.update(form_fields)

        results_page = self.client.post(CALENDAR_SEARCH_URL, form)
        _write_raw(self.raw_dir, CALENDAR_SEARCH_URL, results_page)
        return parse_calendar_events(results_page, CALENDAR_SEARCH_URL)

    def collect(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        event_urls: Sequence[str] = (),
        form_fields: Mapping[str, str] | None = None,
        max_events: int | None = None,
        verify: str = "none",
    ) -> tuple[list[EventingResult], FeiCrawlSummary]:
        """Collect normalized results from calendar events or explicit URLs."""

        if event_urls:
            events = [
                FeiEvent(
                    source_event_id=_stable_id(url),
                    name=urlsplit(url).path.rsplit("/", 1)[-1] or url,
                    url=url,
                    start_date=start_date,
                    end_date=end_date,
                )
                for url in event_urls
            ]
        else:
            events = self.search_calendar(
                start_date=start_date,
                end_date=end_date,
                form_fields=form_fields,
            )

        if max_events is not None:
            events = events[:max_events]

        collected_at = datetime.now(timezone.utc).replace(microsecond=0)
        all_results: list[EventingResult] = []
        result_pages_opened = 0
        verified = 0
        rejected = 0

        for event in events:
            event_results, pages_opened = self.collect_event(event, collected_at=collected_at)
            result_pages_opened += pages_opened
            for result in event_results:
                if verify == "none":
                    all_results.append(result)
                    continue

                is_verified = self._verify_result(result)
                if is_verified:
                    verified += 1
                    all_results.append(result)
                elif verify == "warn":
                    all_results.append(result)
                else:
                    rejected += 1

        return all_results, FeiCrawlSummary(
            events_found=len(events),
            events_opened=len(events),
            result_pages_opened=result_pages_opened,
            results_collected=len(all_results),
            results_verified=verified,
            results_rejected=rejected,
        )

    def collect_event(
        self,
        event: FeiEvent,
        *,
        collected_at: datetime,
    ) -> tuple[list[EventingResult], int]:
        """Open one event page, then each result page linked from it."""

        event_page = self.client.get(event.url)
        _write_raw(self.raw_dir, event.url, event_page)
        result_links = parse_result_links(event_page, event.url)
        if not result_links:
            return parse_eventing_results(event_page, event, event.url, collected_at), 1

        results: list[EventingResult] = []
        pages_opened = 1
        for result_url in result_links:
            result_page = self.client.get(result_url)
            pages_opened += 1
            _write_raw(self.raw_dir, result_url, result_page)
            results.extend(parse_eventing_results(result_page, event, result_url, collected_at))
        return results, pages_opened

    def _verify_result(self, result: EventingResult) -> bool:
        if self.verifier is None:
            return False
        return self.verifier.verify_person(result.rider_name) and self.verifier.verify_horse(result.horse_name)


class FeiVerifier:
    """Verify rider and horse names through the FEI person and horse searches."""

    def __init__(self, client: FeiHttpClient) -> None:
        self.client = client
        self._person_cache: dict[str, bool] = {}
        self._horse_cache: dict[str, bool] = {}

    def verify_person(self, name: str) -> bool:
        return self._verify(PERSON_SEARCH_URL, name, self._person_cache)

    def verify_horse(self, name: str) -> bool:
        return self._verify(HORSE_SEARCH_URL, name, self._horse_cache)

    def _verify(self, url: str, name: str, cache: dict[str, bool]) -> bool:
        key = _search_key(name)
        if key in cache:
            return cache[key]

        search_page = self.client.get(url)
        form = extract_form_fields(search_page)
        if not _set_matching_field(form, ("name",), name):
            _set_first_text_field(search_page, form, name)
        _set_matching_field(form, ("search",), "Search")

        result_page = self.client.post(url, form)
        normalized_page = _search_key(result_page)
        cache[key] = key in normalized_page
        return cache[key]


class FeiResultStore:
    """Persist FEI results in the project's JSON result format."""

    def __init__(self, path: Path | str = DEFAULT_RESULTS_FILE) -> None:
        self.path = Path(path)

    def load(self) -> list[EventingResult]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as results_file:
            payload = json.load(results_file)
        return [EventingResult.from_mapping(item) for item in payload.get("results", [])]

    def merge(self, new_results: Iterable[EventingResult]) -> list[EventingResult]:
        return consolidate_results([*self.load(), *new_results])

    def save(self, results: Sequence[EventingResult]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "source_id": "data_fei",
            "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "results": [result_to_mapping(result) for result in results],
        }
        with self.path.open("w", encoding="utf-8") as results_file:
            json.dump(payload, results_file, indent=2, sort_keys=True)
            results_file.write("\n")


def result_to_mapping(result: EventingResult) -> dict[str, object]:
    """Convert an EventingResult to JSON-serializable values."""

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
        "collected_at": result.collected_at.isoformat(),
        "is_user_entered": result.is_user_entered,
    }


def extract_form_fields(html: str) -> dict[str, str]:
    """Return named input fields and current values from an HTML form."""

    parser = _FormParser()
    parser.feed(html)
    return parser.fields


def parse_calendar_events(html: str, page_url: str = CALENDAR_SEARCH_URL) -> list[FeiEvent]:
    """Extract calendar events from FEI search results HTML."""

    events: list[FeiEvent] = []
    seen_urls: set[str] = set()
    for headers, row in _iter_table_rows(html):
        links = [link for cell in row.cells for link in cell.links]
        event_link = _choose_calendar_link(links)
        if event_link is None:
            continue

        event_url = urljoin(page_url, event_link.href)
        if event_url in seen_urls:
            continue

        data = _row_mapping(headers, row)
        event_name = (
            _first_value(data, ("show", "event", "name", "venue"))
            or event_link.text
            or event_url
        )
        start_date = _first_date(data, ("start", "from", "date"))
        end_date = _first_date(data, ("end", "to", "date")) or start_date
        country = _first_value(data, ("country", "nation", "nf")) or ""
        level = _first_value(data, ("level", "category", "type", "competition", "event code")) or ""
        discipline = _first_value(data, ("discipline",)) or "Eventing"

        events.append(
            FeiEvent(
                source_event_id=_stable_id(event_url),
                name=event_name,
                url=event_url,
                start_date=start_date,
                end_date=end_date,
                country=country,
                discipline=discipline,
                level=level,
            )
        )
        seen_urls.add(event_url)
    return events


def parse_result_links(html: str, page_url: str) -> list[str]:
    """Extract result page links from an event detail page."""

    parser = _LinkParser()
    parser.feed(html)
    urls: list[str] = []
    seen: set[str] = set()
    for link in parser.links:
        searchable = f"{link.text} {link.href}".lower()
        if not any(keyword in searchable for keyword in ("result", "ranking", "standing", "competition")):
            continue
        if any(skip in searchable for skip in ("calendar/search", "javascript:", "#")):
            continue
        url = urljoin(page_url, link.href)
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def parse_eventing_results(
    html: str,
    event: FeiEvent,
    source_url: str,
    collected_at: datetime,
) -> list[EventingResult]:
    """Normalize result rows from FEI result tables."""

    results: list[EventingResult] = []
    for headers, row in _iter_table_rows(html):
        data = _row_mapping(headers, row)
        rider_name = _first_value(data, ("rider", "athlete", "person"))
        horse_name = _first_value(data, ("horse",))
        if not rider_name or not horse_name:
            continue

        total = _number_from(data, ("total", "final", "score", "result"), ())
        dressage = _number_from(data, ("dressage", "dr", "phase a"), ("rank", "place"))
        show_jumping = _number_from(data, ("show jumping", "jumping", "sj"), ("cross", "xc", "rank", "place"))
        xc_jump = _number_from(data, ("cross country jumping", "xc jump", "cross jump", "obstacle"), ("time",))
        xc_time = _number_from(data, ("cross country time", "xc time", "time penalty"), ("dressage", "show"))

        if dressage is None:
            dressage = total
        if dressage is None:
            continue

        event_date = event.start_date or _first_date(data, ("date",))
        if event_date is None:
            continue

        level = _first_value(data, ("level", "category", "competition", "class")) or event.level or "Unknown"
        country = _first_value(data, ("country", "nation", "nf")) or event.country or "Unknown"
        record_id = _record_id(source_url, event.name, event_date, level, rider_name, horse_name)

        results.append(
            EventingResult(
                source_id="data_fei",
                source_record_id=record_id,
                source_priority=0,
                rider_name=rider_name,
                horse_name=horse_name,
                event_name=event.name,
                event_date=event_date,
                level=level,
                country=country,
                dressage_score=dressage,
                show_jumping_penalties=show_jumping or 0.0,
                cross_country_jump_penalties=xc_jump or 0.0,
                cross_country_time_penalties=xc_time or 0.0,
                collected_at=collected_at,
                is_user_entered=False,
            )
        )
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect FEI eventing results from data.fei.org")
    parser.add_argument("--start-date", type=_date_arg, help="Calendar start date, YYYY-MM-DD")
    parser.add_argument("--end-date", type=_date_arg, help="Calendar end date, YYYY-MM-DD")
    parser.add_argument("--event-url", action="append", default=[], help="Specific FEI event/result URL to open")
    parser.add_argument("--form-field", action="append", default=[], help="Extra FEI search form value as name=value")
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULTS_FILE, help="JSON result store path")
    parser.add_argument("--raw-dir", type=Path, help="Optional directory for raw FEI HTML responses")
    parser.add_argument("--max-events", type=int, help="Maximum events to open")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Delay between FEI requests in seconds")
    parser.add_argument("--cookie", help="FEI session cookie header")
    parser.add_argument("--cookie-env", default="FEI_COOKIE", help="Environment variable containing FEI cookie")
    parser.add_argument("--verify", choices=("none", "warn", "require"), default="none")
    parser.add_argument("--dry-run", action="store_true", help="Collect and summarize without writing output")
    args = parser.parse_args(argv)

    cookie = args.cookie or _env_value(args.cookie_env)
    client = FeiHttpClient(cookie=cookie, rate_limit_seconds=args.rate_limit)
    verifier = FeiVerifier(client) if args.verify != "none" else None
    bot = FeiDataBot(client, verifier=verifier, raw_dir=args.raw_dir)
    form_fields = _key_values(args.form_field)

    results, summary = bot.collect(
        start_date=args.start_date,
        end_date=args.end_date,
        event_urls=args.event_url,
        form_fields=form_fields,
        max_events=args.max_events,
        verify=args.verify,
    )

    if not args.dry_run:
        store = FeiResultStore(args.output)
        merged = store.merge(results)
        store.save(merged)
        written = len(merged)
    else:
        written = 0

    print(
        "FEI crawl complete: "
        f"events_found={summary.events_found}, "
        f"events_opened={summary.events_opened}, "
        f"result_pages_opened={summary.result_pages_opened}, "
        f"results_collected={summary.results_collected}, "
        f"results_verified={summary.results_verified}, "
        f"results_rejected={summary.results_rejected}, "
        f"results_in_store={written}"
    )
    return 0


class _FormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        values = dict(attrs)
        name = values.get("name")
        if name:
            self.fields[name] = values.get("value") or ""


class _InputParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_input_names: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "input":
            return
        values = dict(attrs)
        input_type = (values.get("type") or "text").lower()
        name = values.get("name")
        if name and input_type in {"text", "search"}:
            self.text_input_names.append(name)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[_Link] = []
        self._href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            self._href = dict(attrs).get("href")
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append(_Link(_clean_text(" ".join(self._text_parts)), self._href))
            self._href = None
            self._text_parts = []


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[_Table] = []
        self._table_depth = 0
        self._rows: list[_Row] = []
        self._cells: list[_Cell] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_links: list[_Link] | None = None
        self._cell_is_header = False
        self._link_href: str | None = None
        self._link_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "table":
            if self._table_depth == 0:
                self._rows = []
            self._table_depth += 1
        elif self._table_depth and tag == "tr":
            self._cells = []
        elif self._table_depth and tag in {"td", "th"}:
            self._cell_parts = []
            self._cell_links = []
            self._cell_is_header = tag == "th"
        elif self._cell_parts is not None and tag == "a":
            self._link_href = dict(attrs).get("href")
            self._link_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)
        if self._link_href is not None:
            self._link_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "a" and self._link_href is not None and self._cell_links is not None:
            self._cell_links.append(_Link(_clean_text(" ".join(self._link_parts)), self._link_href))
            self._link_href = None
            self._link_parts = []
        elif tag in {"td", "th"} and self._cells is not None and self._cell_parts is not None:
            self._cells.append(
                _Cell(
                    text=_clean_text(" ".join(self._cell_parts)),
                    links=tuple(self._cell_links or []),
                    is_header=self._cell_is_header,
                )
            )
            self._cell_parts = None
            self._cell_links = None
            self._cell_is_header = False
        elif tag == "tr" and self._cells is not None:
            if self._cells:
                self._rows.append(_Row(tuple(self._cells)))
            self._cells = None
        elif tag == "table" and self._table_depth:
            self._table_depth -= 1
            if self._table_depth == 0 and self._rows:
                self.tables.append(_Table(tuple(self._rows)))


def _iter_table_rows(html: str) -> Iterable[tuple[list[str], _Row]]:
    parser = _TableParser()
    parser.feed(html)
    for table in parser.tables:
        headers: list[str] = []
        for row in table.rows:
            if _is_header_row(row, has_headers=bool(headers)):
                headers = [_header(cell.text) for cell in row.cells]
                continue
            if headers:
                yield headers, row


def _is_header_row(row: _Row, *, has_headers: bool = False) -> bool:
    if any(cell.is_header for cell in row.cells):
        return True
    if has_headers:
        return False
    text = " ".join(cell.text.lower() for cell in row.cells)
    return not any(cell.links for cell in row.cells) and any(
        keyword in text
        for keyword in (
            "athlete",
            "rider",
            "horse",
            "show",
            "event",
            "country",
            "date",
            "discipline",
        )
    )


def _row_mapping(headers: Sequence[str], row: _Row) -> dict[str, str]:
    values: dict[str, str] = {}
    for index, cell in enumerate(row.cells):
        header = headers[index] if index < len(headers) and headers[index] else f"column_{index + 1}"
        values[header] = cell.text
    return values


def _choose_calendar_link(links: Sequence[_Link]) -> _Link | None:
    for link in links:
        candidate = f"{link.href} {link.text}".lower()
        if "calendar" in candidate and any(keyword in candidate for keyword in ("event", "show")):
            return link
    for link in links:
        candidate = f"{link.href} {link.text}".lower()
        if any(keyword in candidate for keyword in ("event", "show")):
            return link
    return None


def _set_matching_field(form: dict[str, str], required_tokens: Sequence[str], value: str | None) -> bool:
    if value is None:
        return False
    for name in form:
        normalized = _header(name)
        if all(token in normalized for token in required_tokens):
            form[name] = value
            return True
    return False


def _set_first_text_field(html: str, form: dict[str, str], value: str) -> None:
    parser = _InputParser()
    parser.feed(html)
    for name in parser.text_input_names:
        if name in form:
            form[name] = value
            return


def _first_value(data: Mapping[str, str], include_tokens: Sequence[str]) -> str | None:
    for header, value in data.items():
        if value and any(token in header for token in include_tokens):
            return value
    return None


def _first_date(data: Mapping[str, str], include_tokens: Sequence[str]) -> date | None:
    for header, value in data.items():
        if value and any(token in header for token in include_tokens):
            parsed = _parse_date(value)
            if parsed:
                return parsed
    return None


def _number_from(
    data: Mapping[str, str],
    include_tokens: Sequence[str],
    exclude_tokens: Sequence[str],
) -> float | None:
    for header, value in data.items():
        if not value:
            continue
        if not any(token in header for token in include_tokens):
            continue
        if any(token in header for token in exclude_tokens):
            continue
        return _parse_number(value)
    return None


def _parse_date(value: str) -> date | None:
    value = _clean_text(value)
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value[:32], pattern).date()
        except ValueError:
            continue
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        return date.fromisoformat(match.group(0))
    return None


def _parse_number(value: str) -> float | None:
    if re.search(r"\b(el|ret|wd|dns|dq)\b", value, re.IGNORECASE):
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", "."))
    if not match:
        return None
    return float(match.group(0))


def _record_id(*parts: object) -> str:
    return f"fei:{_stable_id('|'.join(str(part) for part in parts))}"


def _stable_id(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _search_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _header(value: str) -> str:
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return _search_key(spaced)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _write_raw(raw_dir: Path | None, url: str, html: str) -> None:
    if raw_dir is None:
        return
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{_stable_id(url)}.html"
    path.write_text(html, encoding="utf-8")


def _key_values(items: Sequence[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--form-field must be name=value, got {item!r}")
        name, value = item.split("=", 1)
        if not name:
            raise SystemExit("--form-field name cannot be empty")
        values[name] = value
    return values


def _date_arg(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc


def _env_value(name: str) -> str | None:
    import os

    return os.environ.get(name)


if __name__ == "__main__":
    raise SystemExit(main())
