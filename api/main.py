"""FastAPI backend for FEI Eventing results and predictions."""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from equibets.database import PostgresStore
from equibets.fei_bot import FeiDataBot, FeiHttpClient
from equibets.pipeline import run_daily_pipeline


app = FastAPI(title="Equibets FEI Eventing API")


class EventRerunRequest(BaseModel):
    event_url: str
    start_date: date | None = None
    end_date: date | None = None


class HorseRerunRequest(BaseModel):
    horse_name: str
    horse_fei_id: str = ""
    rider_name: str = ""
    max_history_pages: int | None = None


def database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured")
    return value


def connection(url: Annotated[str, Depends(database_url)]):
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="PostgreSQL dependencies are not installed") from exc
    with psycopg.connect(url, row_factory=dict_row) as conn:
        yield conn


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/events")
def events(
    conn: Annotated[Any, Depends(connection)],
    country: str | None = None,
    level: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT e.*, count(r.source_record_id) AS result_count
        FROM events e
        LEFT JOIN result_rows r ON r.fei_event_id = e.fei_event_id
        LEFT JOIN classes c ON c.id = r.class_id
        WHERE (r.source_id IS NULL OR r.source_id = 'data_fei')
          AND (%(country)s IS NULL OR e.country = %(country)s)
          AND (%(level)s IS NULL OR c.class_level = %(level)s OR r.event_level = %(level)s)
          AND (%(start_date)s IS NULL OR e.start_date >= %(start_date)s)
          AND (%(end_date)s IS NULL OR e.end_date <= %(end_date)s)
        GROUP BY e.fei_event_id
        ORDER BY e.start_date DESC NULLS LAST, e.event_name
    """
    return _rows(conn.execute(query, locals()).fetchall())


@app.get("/results")
def results(
    conn: Annotated[Any, Depends(connection)],
    country: str | None = None,
    level: str | None = None,
    rider: str | None = None,
    horse: str | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 250,
) -> list[dict[str, Any]]:
    query = """
        SELECT
            r.*, riders.rider_name, riders.fei_id AS rider_fei_id,
            horses.horse_name, horses.fei_id AS horse_fei_id
        FROM result_rows r
        JOIN combinations co ON co.combination_key = r.combination_key
        JOIN riders ON riders.rider_key = co.rider_key
        JOIN horses ON horses.horse_key = co.horse_key
        WHERE r.source_id = 'data_fei'
          AND (%(country)s IS NULL OR r.event_country = %(country)s)
          AND (%(level)s IS NULL OR r.event_level = %(level)s)
          AND (%(rider)s IS NULL OR riders.rider_name ILIKE '%%' || %(rider)s || '%%')
          AND (%(horse)s IS NULL OR horses.horse_name ILIKE '%%' || %(horse)s || '%%')
          AND (%(status)s IS NULL OR r.status = %(status)s)
          AND (%(start_date)s IS NULL OR r.event_date >= %(start_date)s)
          AND (%(end_date)s IS NULL OR r.event_date <= %(end_date)s)
        ORDER BY r.event_date DESC, r.event_name, r.total_score NULLS LAST
        LIMIT %(limit)s
    """
    return _rows(conn.execute(query, locals()).fetchall())


@app.get("/combinations/{combination_key}/history")
def combination_history(conn: Annotated[Any, Depends(connection)], combination_key: str) -> dict[str, Any]:
    result_rows = conn.execute(
        """
        SELECT r.*, riders.rider_name, horses.horse_name
        FROM result_rows r
        JOIN combinations co ON co.combination_key = r.combination_key
        JOIN riders ON riders.rider_key = co.rider_key
        JOIN horses ON horses.horse_key = co.horse_key
        WHERE r.combination_key = %s
          AND r.source_id = 'data_fei'
        ORDER BY r.event_date DESC
        """,
        (combination_key,),
    ).fetchall()
    prediction = conn.execute(
        "SELECT * FROM predictions WHERE combination_key = %s ORDER BY created_at DESC",
        (combination_key,),
    ).fetchall()
    return {"results": _rows(result_rows), "predictions": _rows(prediction)}


@app.get("/predictions")
def predictions(
    conn: Annotated[Any, Depends(connection)],
    level: str | None = None,
    rider: str | None = None,
    horse: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        SELECT p.*, riders.rider_name, horses.horse_name
        FROM predictions p
        JOIN combinations co ON co.combination_key = p.combination_key
        JOIN riders ON riders.rider_key = co.rider_key
        JOIN horses ON horses.horse_key = co.horse_key
        WHERE (%(level)s IS NULL OR p.target_level = %(level)s)
          AND (%(rider)s IS NULL OR riders.rider_name ILIKE '%%' || %(rider)s || '%%')
          AND (%(horse)s IS NULL OR horses.horse_name ILIKE '%%' || %(horse)s || '%%')
        ORDER BY p.created_at DESC
    """
    return _rows(conn.execute(query, locals()).fetchall())


@app.post("/admin/scrape/event")
def rerun_event(request: EventRerunRequest, url: Annotated[str, Depends(database_url)]) -> dict[str, Any]:
    summary = run_daily_pipeline(
        database_url=url,
        start_date=request.start_date,
        end_date=request.end_date,
        event_urls=[request.event_url],
    )
    return summary.__dict__


@app.post("/admin/scrape/horse")
def rerun_horse(request: HorseRerunRequest, url: Annotated[str, Depends(database_url)]) -> dict[str, int]:
    client = FeiHttpClient(cookie=os.environ.get("FEI_COOKIE"))
    bot = FeiDataBot(client)
    store = PostgresStore.connect(url)
    store.initialize()
    horse_history, combination_history, pages_opened = bot.collect_horse_history(
        horse_name=request.horse_name,
        horse_fei_id=request.horse_fei_id,
        rider_name=request.rider_name,
        max_pages=request.max_history_pages,
    )
    for result in horse_history:
        store.upsert_result(result)
        store.link_history(result, history_type="horse")
    for result in combination_history:
        store.link_history(result, history_type="combination")
    store.commit()
    return {
        "pages_opened": pages_opened,
        "horse_results_saved": len(horse_history),
        "combination_results_saved": len(combination_history),
    }


def _rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_jsonable(dict(row)) for row in rows]


def _jsonable(row: dict[str, Any]) -> dict[str, Any]:
    converted: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, (date, Decimal)):
            converted[key] = str(value)
        else:
            converted[key] = value
    return converted
