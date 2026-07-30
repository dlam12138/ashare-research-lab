"""Transactional, independent DuckDB repository for metric results."""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import asdict
from typing import Any

import duckdb

from ashare_research.metrics.identity import (
    validate_canonical_metric_result_id,
)
from ashare_research.metrics.models import (
    MetricDefinition,
    MetricLineage,
    MetricResult,
)

METRIC_SCHEMA_VERSION = "1.0"
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS metric_schema_meta (
    schema_name VARCHAR PRIMARY KEY,
    schema_version VARCHAR NOT NULL,
    applied_at VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_id VARCHAR NOT NULL,
    version VARCHAR NOT NULL,
    display_name_zh VARCHAR NOT NULL,
    formula VARCHAR NOT NULL,
    input_concept_ids VARCHAR NOT NULL,
    input_roles VARCHAR NOT NULL,
    unit VARCHAR NOT NULL,
    PRIMARY KEY (metric_id, version)
);
CREATE TABLE IF NOT EXISTS metric_runs (
    run_id VARCHAR PRIMARY KEY,
    status VARCHAR NOT NULL,
    started_at VARCHAR NOT NULL,
    completed_at VARCHAR DEFAULT '',
    result_count INTEGER DEFAULT 0,
    error_message VARCHAR DEFAULT ''
);
CREATE TABLE IF NOT EXISTS metric_results (
    metric_result_id VARCHAR PRIMARY KEY,
    metric_id VARCHAR NOT NULL,
    metric_definition_version VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    fiscal_year INTEGER NOT NULL,
    period_end VARCHAR NOT NULL,
    result_version INTEGER NOT NULL,
    supersedes_metric_result_id VARCHAR DEFAULT '',
    status VARCHAR NOT NULL,
    value DECIMAL(38,12),
    unit VARCHAR NOT NULL,
    formula VARCHAR NOT NULL,
    available_at VARCHAR NOT NULL,
    input_fact_ids VARCHAR NOT NULL,
    missing_input_description VARCHAR DEFAULT '',
    revision_review_status VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL
);
CREATE TABLE IF NOT EXISTS metric_lineage (
    metric_result_id VARCHAR NOT NULL,
    input_fact_id VARCHAR NOT NULL,
    input_role VARCHAR NOT NULL,
    input_fact_version INTEGER NOT NULL,
    input_restatement_version VARCHAR NOT NULL,
    input_available_at VARCHAR NOT NULL,
    PRIMARY KEY (metric_result_id, input_role, input_fact_id)
);
"""


class MetricRepositoryError(ValueError):
    """Metric persistence or version-chain validation failed."""


def _result_payload(result: MetricResult) -> dict[str, Any]:
    data = asdict(result)
    data.pop("metric_result_id", None)
    data.pop("created_at", None)
    data["status"] = str(result.status)
    data["value"] = str(result.value) if result.value is not None else None
    data["input_fact_ids"] = list(result.input_fact_ids)
    return data


class MetricRepository:
    schema_version = METRIC_SCHEMA_VERSION

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._conn: duckdb.DuckDBPyConnection | None = None

    def connect(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def ensure_schema(self, *, applied_at: str) -> None:
        conn = self.connect()
        conn.execute(_SCHEMA_SQL)
        row = conn.execute(
            "SELECT schema_version FROM metric_schema_meta "
            "WHERE schema_name='metrics'"
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO metric_schema_meta VALUES ('metrics', ?, ?)",
                [METRIC_SCHEMA_VERSION, applied_at],
            )
        elif row[0] != METRIC_SCHEMA_VERSION:
            raise MetricRepositoryError(
                f"unsupported metric schema version: {row[0]}"
            )

    @contextlib.contextmanager
    def transaction(self):
        conn = self.connect()
        conn.execute("BEGIN TRANSACTION")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    def store_definitions(
        self,
        definitions: list[MetricDefinition],
        *,
        conn=None,
    ) -> None:
        conn = conn or self.connect()
        for definition in definitions:
            incoming = (
                definition.display_name_zh,
                definition.formula,
                json.dumps(definition.input_concept_ids),
                json.dumps(definition.input_roles),
                definition.unit,
            )
            existing = conn.execute(
                """SELECT display_name_zh, formula, input_concept_ids,
                          input_roles, unit
                   FROM metric_definitions WHERE metric_id=? AND version=?""",
                [definition.metric_id, definition.version],
            ).fetchone()
            if existing is not None and tuple(existing) != incoming:
                raise MetricRepositoryError(
                    f"metric definition conflict: {definition.metric_id}"
                )
            if existing is None:
                conn.execute(
                    "INSERT INTO metric_definitions VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        definition.metric_id,
                        definition.version,
                        *incoming,
                    ],
                )

    def store_run(
        self,
        run_id: str,
        *,
        status: str,
        started_at: str,
        completed_at: str = "",
        result_count: int = 0,
        conn=None,
    ) -> None:
        conn = conn or self.connect()
        existing = conn.execute(
            "SELECT status, started_at, completed_at, result_count "
            "FROM metric_runs WHERE run_id=?",
            [run_id],
        ).fetchone()
        incoming = (status, started_at, completed_at, result_count)
        if existing is not None and tuple(existing) != incoming:
            raise MetricRepositoryError(f"metric run conflict: {run_id}")
        if existing is None:
            conn.execute(
                "INSERT INTO metric_runs VALUES (?, ?, ?, ?, ?, '')",
                [run_id, *incoming],
            )

    def _load_result(self, result_id: str, conn) -> dict[str, Any] | None:
        row = conn.execute(
            "SELECT * FROM metric_results WHERE metric_result_id=?",
            [result_id],
        ).fetchone()
        if row is None:
            return None
        columns = [item[0] for item in conn.description]
        result = dict(zip(columns, row, strict=True))
        result["input_fact_ids"] = json.loads(result["input_fact_ids"])
        result["value"] = (
            str(result["value"]) if result["value"] is not None else None
        )
        return result

    def _validate_chain(
        self,
        result: MetricResult,
        batch: dict[str, MetricResult],
        conn,
    ) -> None:
        predecessor_id = result.supersedes_metric_result_id
        if result.result_version == 1:
            if predecessor_id:
                raise MetricRepositoryError("metric result v1 cannot supersede")
            return
        predecessor = batch.get(predecessor_id)
        old = (
            _result_payload(predecessor)
            if predecessor is not None
            else self._load_result(predecessor_id, conn)
        )
        if old is None:
            raise MetricRepositoryError("metric predecessor does not exist")
        if result.result_version != int(old["result_version"]) + 1:
            raise MetricRepositoryError("metric version must increment by 1")
        current = _result_payload(result)
        for field in (
            "metric_id",
            "metric_definition_version",
            "symbol",
            "fiscal_year",
            "period_end",
        ):
            if current[field] != old[field]:
                raise MetricRepositoryError(
                    f"metric version changes stable field: {field}"
                )
        if result.available_at < str(old["available_at"]):
            raise MetricRepositoryError("metric available_at moved backwards")
        seen = {result.metric_result_id}
        cursor = predecessor_id
        while cursor:
            if cursor in seen:
                raise MetricRepositoryError("metric version-chain cycle")
            seen.add(cursor)
            candidate = batch.get(cursor)
            if candidate is not None:
                cursor = candidate.supersedes_metric_result_id
            else:
                stored = self._load_result(cursor, conn)
                cursor = (
                    str(stored["supersedes_metric_result_id"])
                    if stored is not None else ""
                )

    def store_results(
        self,
        results: list[MetricResult],
        lineage: list[MetricLineage],
        *,
        conn=None,
    ) -> tuple[int, int]:
        conn = conn or self.connect()
        batch = {result.metric_result_id: result for result in results}
        if len(batch) != len(results):
            raise MetricRepositoryError("duplicate metric result in batch")
        for result in results:
            validate_canonical_metric_result_id(result)
            self._validate_chain(result, batch, conn)
            existing = self._load_result(result.metric_result_id, conn)
            if existing is not None:
                incoming = _result_payload(result)
                existing.pop("metric_result_id", None)
                existing.pop("created_at", None)
                if existing != incoming:
                    raise MetricRepositoryError(
                        f"metric semantic conflict: {result.metric_result_id}"
                    )
        result_ids = set(batch)
        for row in lineage:
            if row.metric_result_id not in result_ids and self._load_result(
                row.metric_result_id, conn,
            ) is None:
                raise MetricRepositoryError("lineage result does not exist")
            result = batch.get(row.metric_result_id)
            if result is not None and row.input_fact_id not in result.input_fact_ids:
                raise MetricRepositoryError("lineage input is not bound to result")

        inserted = 0
        for result in results:
            if self._load_result(result.metric_result_id, conn) is not None:
                continue
            conn.execute(
                """INSERT INTO metric_results VALUES
                   (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    result.metric_result_id,
                    result.metric_id,
                    result.metric_definition_version,
                    result.symbol,
                    result.fiscal_year,
                    result.period_end,
                    result.result_version,
                    result.supersedes_metric_result_id,
                    str(result.status),
                    result.value,
                    result.unit,
                    result.formula,
                    result.available_at,
                    json.dumps(result.input_fact_ids),
                    result.missing_input_description,
                    result.revision_review_status,
                    result.created_at,
                ],
            )
            inserted += 1
        lineage_inserted = 0
        for row in lineage:
            existing = conn.execute(
                """SELECT 1 FROM metric_lineage
                   WHERE metric_result_id=? AND input_role=? AND input_fact_id=?""",
                [row.metric_result_id, row.input_role, row.input_fact_id],
            ).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO metric_lineage VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        row.metric_result_id,
                        row.input_fact_id,
                        row.input_role,
                        row.input_fact_version,
                        row.input_restatement_version,
                        row.input_available_at,
                    ],
                )
                lineage_inserted += 1
        return inserted, lineage_inserted

    def all_results(self) -> list[dict[str, Any]]:
        rows = self.connect().execute(
            "SELECT * FROM metric_results "
            "ORDER BY fiscal_year, metric_id, result_version"
        ).fetchall()
        columns = [item[0] for item in self.connect().description]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def latest_results(self, as_of_date: str) -> list[dict[str, Any]]:
        rows = self.connect().execute(
            """SELECT * EXCLUDE (rn) FROM (
                 SELECT *, ROW_NUMBER() OVER (
                   PARTITION BY symbol, fiscal_year, metric_id,
                                metric_definition_version
                   ORDER BY result_version DESC, available_at DESC
                 ) rn
                 FROM metric_results WHERE available_at <= ?
               ) WHERE rn=1 ORDER BY fiscal_year, metric_id""",
            [as_of_date],
        ).fetchall()
        columns = [item[0] for item in self.connect().description]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def lineage_rows(self) -> list[dict[str, Any]]:
        rows = self.connect().execute(
            "SELECT * FROM metric_lineage "
            "ORDER BY metric_result_id, input_role"
        ).fetchall()
        columns = [item[0] for item in self.connect().description]
        return [dict(zip(columns, row, strict=True)) for row in rows]
