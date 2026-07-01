"""PostgreSQL persistence for FEI eventing results and predictions."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from equibets.fei_bot import FeiEvent
from equibets.results import EventingResult, PredictionEvidence


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    fei_event_id text PRIMARY KEY,
    event_name text NOT NULL,
    venue text NOT NULL DEFAULT '',
    country text NOT NULL DEFAULT '',
    start_date date,
    end_date date,
    event_url text NOT NULL,
    result_page_url text NOT NULL DEFAULT '',
    discipline text NOT NULL DEFAULT 'Eventing',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS classes (
    id bigserial PRIMARY KEY,
    fei_event_id text NOT NULL REFERENCES events(fei_event_id) ON DELETE CASCADE,
    class_level text NOT NULL,
    result_page_url text NOT NULL DEFAULT '',
    UNIQUE (fei_event_id, class_level, result_page_url)
);

CREATE TABLE IF NOT EXISTS riders (
    rider_key text PRIMARY KEY,
    fei_id text UNIQUE,
    rider_name text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS horses (
    horse_key text PRIMARY KEY,
    fei_id text UNIQUE,
    horse_name text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS combinations (
    combination_key text PRIMARY KEY,
    rider_key text NOT NULL REFERENCES riders(rider_key),
    horse_key text NOT NULL REFERENCES horses(horse_key),
    combination_id text NOT NULL DEFAULT '',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS result_rows (
    source_record_id text PRIMARY KEY,
    source_id text NOT NULL CHECK (source_id = 'data_fei'),
    source_priority integer NOT NULL,
    fei_event_id text REFERENCES events(fei_event_id),
    class_id bigint REFERENCES classes(id),
    combination_key text NOT NULL REFERENCES combinations(combination_key),
    placing text NOT NULL DEFAULT '',
    dressage_score numeric,
    cross_country_jump_penalties numeric NOT NULL DEFAULT 0,
    cross_country_time_penalties numeric NOT NULL DEFAULT 0,
    show_jumping_jump_penalties numeric NOT NULL DEFAULT 0,
    show_jumping_time_penalties numeric NOT NULL DEFAULT 0,
    total_score numeric,
    status text NOT NULL DEFAULT 'completed',
    mer_status text NOT NULL DEFAULT '',
    event_level text NOT NULL,
    event_date date NOT NULL,
    event_country text NOT NULL,
    event_name text NOT NULL,
    source_url text NOT NULL,
    collected_at timestamptz NOT NULL,
    is_user_entered boolean NOT NULL DEFAULT false,
    raw_payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS result_rows_duplicate_key
    ON result_rows (combination_key, lower(event_name), event_date, lower(event_level));

CREATE INDEX IF NOT EXISTS result_rows_filter_idx
    ON result_rows (event_date DESC, event_level, event_country, status);

CREATE TABLE IF NOT EXISTS horse_result_history (
    source_record_id text NOT NULL REFERENCES result_rows(source_record_id) ON DELETE CASCADE,
    horse_key text NOT NULL REFERENCES horses(horse_key),
    combination_key text REFERENCES combinations(combination_key),
    history_type text NOT NULL CHECK (history_type IN ('horse', 'combination')),
    collected_at timestamptz NOT NULL,
    PRIMARY KEY (source_record_id, history_type)
);

CREATE TABLE IF NOT EXISTS predictions (
    combination_key text NOT NULL REFERENCES combinations(combination_key),
    target_level text NOT NULL,
    predicted_final_score_low numeric NOT NULL,
    predicted_final_score_high numeric NOT NULL,
    evidence jsonb NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (combination_key, target_level)
);

CREATE TABLE IF NOT EXISTS scrape_logs (
    id bigserial PRIMARY KEY,
    run_id text NOT NULL,
    target_type text NOT NULL,
    target_url text NOT NULL DEFAULT '',
    status text NOT NULL,
    message text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now()
);
"""


class PostgresStore:
    """Small repository around psycopg connections."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    @classmethod
    def connect(cls, database_url: str | None = None) -> "PostgresStore":
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install PostgreSQL support with `python3 -m pip install -e .`.") from exc
        return cls(psycopg.connect(database_url or os.environ["DATABASE_URL"]))

    def initialize(self) -> None:
        self.connection.execute(SCHEMA_SQL)
        self.connection.commit()

    def upsert_event(self, event: FeiEvent) -> None:
        self.connection.execute(
            """
            INSERT INTO events (
                fei_event_id, event_name, venue, country, start_date, end_date,
                event_url, result_page_url, discipline, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fei_event_id) DO UPDATE SET
                event_name = EXCLUDED.event_name,
                venue = EXCLUDED.venue,
                country = EXCLUDED.country,
                start_date = EXCLUDED.start_date,
                end_date = EXCLUDED.end_date,
                event_url = EXCLUDED.event_url,
                result_page_url = EXCLUDED.result_page_url,
                discipline = EXCLUDED.discipline,
                updated_at = EXCLUDED.updated_at
            """,
            (
                event.source_event_id,
                event.name,
                event.venue or event.name,
                event.country,
                event.start_date,
                event.end_date,
                event.url,
                event.result_page_url,
                event.discipline,
                _now(),
            ),
        )

    def upsert_class(self, event: FeiEvent, level: str, result_page_url: str) -> int | None:
        cursor = self.connection.execute(
            """
            INSERT INTO classes (fei_event_id, class_level, result_page_url)
            VALUES (%s, %s, %s)
            ON CONFLICT (fei_event_id, class_level, result_page_url)
            DO UPDATE SET class_level = EXCLUDED.class_level
            RETURNING id
            """,
            (event.source_event_id, level, result_page_url),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else None

    def upsert_result(self, result: EventingResult, *, event: FeiEvent | None = None, class_id: int | None = None) -> None:
        if result.source_id != "data_fei":
            raise ValueError("PostgreSQL result store accepts FEI rows only")
        rider_key = _entity_key(result.rider_fei_id, result.rider_name)
        horse_key = _entity_key(result.horse_fei_id, result.horse_name)
        combination_key = _combination_key(result)
        self.connection.execute(
            """
            INSERT INTO riders (rider_key, fei_id, rider_name, updated_at)
            VALUES (%s, NULLIF(%s, ''), %s, %s)
            ON CONFLICT (rider_key) DO UPDATE SET
                fei_id = COALESCE(EXCLUDED.fei_id, riders.fei_id),
                rider_name = EXCLUDED.rider_name,
                updated_at = EXCLUDED.updated_at
            """,
            (rider_key, result.rider_fei_id, result.rider_name, _now()),
        )
        self.connection.execute(
            """
            INSERT INTO horses (horse_key, fei_id, horse_name, updated_at)
            VALUES (%s, NULLIF(%s, ''), %s, %s)
            ON CONFLICT (horse_key) DO UPDATE SET
                fei_id = COALESCE(EXCLUDED.fei_id, horses.fei_id),
                horse_name = EXCLUDED.horse_name,
                updated_at = EXCLUDED.updated_at
            """,
            (horse_key, result.horse_fei_id, result.horse_name, _now()),
        )
        self.connection.execute(
            """
            INSERT INTO combinations (combination_key, rider_key, horse_key, combination_id, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (combination_key) DO UPDATE SET
                rider_key = EXCLUDED.rider_key,
                horse_key = EXCLUDED.horse_key,
                combination_id = EXCLUDED.combination_id,
                updated_at = EXCLUDED.updated_at
            """,
            (combination_key, rider_key, horse_key, result.combination_id, _now()),
        )
        self.connection.execute(
            """
            INSERT INTO result_rows (
                source_record_id, source_id, source_priority, fei_event_id, class_id,
                combination_key, placing, dressage_score, cross_country_jump_penalties,
                cross_country_time_penalties, show_jumping_jump_penalties,
                show_jumping_time_penalties, total_score, status, mer_status,
                event_level, event_date, event_country, event_name, source_url,
                collected_at, is_user_entered, raw_payload
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            ON CONFLICT (source_record_id) DO UPDATE SET
                placing = EXCLUDED.placing,
                dressage_score = EXCLUDED.dressage_score,
                cross_country_jump_penalties = EXCLUDED.cross_country_jump_penalties,
                cross_country_time_penalties = EXCLUDED.cross_country_time_penalties,
                show_jumping_jump_penalties = EXCLUDED.show_jumping_jump_penalties,
                show_jumping_time_penalties = EXCLUDED.show_jumping_time_penalties,
                total_score = EXCLUDED.total_score,
                status = EXCLUDED.status,
                mer_status = EXCLUDED.mer_status,
                source_url = EXCLUDED.source_url,
                collected_at = EXCLUDED.collected_at,
                raw_payload = EXCLUDED.raw_payload
            """,
            (
                result.source_record_id,
                result.source_id,
                result.source_priority,
                event.source_event_id if event else None,
                class_id,
                combination_key,
                result.placing,
                result.dressage_score,
                result.cross_country_jump_penalties,
                result.cross_country_time_penalties,
                result.show_jumping_penalties,
                result.show_jumping_time_penalties,
                result.total_score,
                result.status,
                result.mer_status,
                result.level,
                result.event_date,
                result.country,
                result.event_name,
                result.source_url,
                result.collected_at,
                result.is_user_entered,
                json.dumps(_result_payload(result)),
            ),
        )

    def link_history(self, result: EventingResult, *, history_type: str) -> None:
        horse_key = _entity_key(result.horse_fei_id, result.horse_name)
        rider_key = _entity_key(result.rider_fei_id, result.rider_name)
        combination_key = _combination_key(result)
        self.connection.execute(
            """
            INSERT INTO horse_result_history (
                source_record_id, horse_key, combination_key, history_type, collected_at
            ) VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (source_record_id, history_type) DO UPDATE SET
                collected_at = EXCLUDED.collected_at
            """,
            (result.source_record_id, horse_key, combination_key, history_type, result.collected_at),
        )

    def upsert_prediction(self, evidence: PredictionEvidence) -> None:
        combination_key = f"{_slug(evidence.rider_name)}:{_slug(evidence.horse_name)}"
        self.connection.execute(
            """
            INSERT INTO predictions (
                combination_key, target_level, predicted_final_score_low,
                predicted_final_score_high, evidence, created_at
            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (combination_key, target_level) DO UPDATE SET
                predicted_final_score_low = EXCLUDED.predicted_final_score_low,
                predicted_final_score_high = EXCLUDED.predicted_final_score_high,
                evidence = EXCLUDED.evidence,
                created_at = EXCLUDED.created_at
            """,
            (
                combination_key,
                evidence.target_level,
                evidence.predicted_final_score_low,
                evidence.predicted_final_score_high,
                json.dumps(asdict(evidence)),
                _now(),
            ),
        )

    def log(self, run_id: str, target_type: str, status: str, message: str = "", target_url: str = "") -> None:
        self.connection.execute(
            """
            INSERT INTO scrape_logs (run_id, target_type, target_url, status, message, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (run_id, target_type, target_url, status, message[:1000], _now()),
        )

    def commit(self) -> None:
        self.connection.commit()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _entity_key(fei_id: str, name: str) -> str:
    return fei_id or _slug(name)


def _combination_key(result: EventingResult) -> str:
    return f"{_slug(result.rider_name)}:{_slug(result.horse_name)}"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _result_payload(result: EventingResult) -> dict[str, object]:
    return {
        "source_id": result.source_id,
        "source_record_id": result.source_record_id,
        "rider_fei_id": result.rider_fei_id,
        "horse_fei_id": result.horse_fei_id,
        "combination_id": result.combination_id,
        "source_url": result.source_url,
    }
