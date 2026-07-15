from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import duckdb

from contracts.schemas import TelemetryPoint

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS telemetry (
    component_id     VARCHAR   NOT NULL,
    window_start     TIMESTAMP NOT NULL,
    latency_ms       DOUBLE    NOT NULL,
    jitter_ms        DOUBLE    NOT NULL,
    packet_loss_pct  DOUBLE    NOT NULL,
    throughput_mbps  DOUBLE    NOT NULL,
    error_rate       DOUBLE    NOT NULL,
    connection_count INTEGER   NOT NULL,
    cpu_pct          DOUBLE    NOT NULL,
    mem_pct          DOUBLE    NOT NULL
)
"""

_INSERT_ROW = """
INSERT INTO telemetry VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_COLUMNS = (
    "component_id",
    "window_start",
    "latency_ms",
    "jitter_ms",
    "packet_loss_pct",
    "throughput_mbps",
    "error_rate",
    "connection_count",
    "cpu_pct",
    "mem_pct",
)


def _to_naive_utc(ts: datetime) -> datetime:
    """Convert any aware datetime to a naive UTC datetime for DuckDB TIMESTAMP storage."""
    if ts.tzinfo is not None:
        ts = ts.astimezone(UTC).replace(tzinfo=None)
    return ts


def _point_to_row(point: TelemetryPoint) -> tuple:
    return (
        point.component_id,
        _to_naive_utc(point.window_start),
        point.latency_ms,
        point.jitter_ms,
        point.packet_loss_pct,
        point.throughput_mbps,
        point.error_rate,
        int(point.connection_count),
        point.cpu_pct,
        point.mem_pct,
    )


def _row_to_point(row: tuple) -> TelemetryPoint:
    mapping = dict(zip(_COLUMNS, row, strict=False))
    ts = mapping["window_start"]
    # TIMESTAMP columns return naive datetimes; re-attach UTC since all stored
    # values were converted to naive UTC on insert.
    if isinstance(ts, datetime) and ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    mapping["window_start"] = ts
    return TelemetryPoint.model_validate(mapping)


class TelemetryStore:
    """DuckDB-backed persistent store for TelemetryPoint time-series data.

    Wraps an embedded DuckDB connection and manages the telemetry table
    lifecycle.  Use ':memory:' (the default) for in-process testing without
    any disk I/O.  Pass a file path for durable on-disk persistence across
    process restarts.

    The store is an append-only writer: duplicate (component_id, window_start)
    pairs are accepted without error because the ingestion pipeline does not
    guarantee idempotency by itself.  Deduplication is the caller's
    responsibility.

    Usage::

        with TelemetryStore() as store:
            store.write_telemetry(points)
            result = store.read_telemetry(component_id="db-01")

    Args:
        db_path: DuckDB connection target.  ':memory:' (default) creates an
                 in-process database that disappears when closed.  Any str or
                 Path value is treated as the on-disk database file path.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        target = ":memory:" if db_path == ":memory:" else str(db_path)
        self._conn = duckdb.connect(target)
        self._conn.execute(_CREATE_TABLE)

    def write_telemetry(self, points: list[TelemetryPoint]) -> int:
        """Bulk-insert TelemetryPoint records into the telemetry table.

        Args:
            points: Validated TelemetryPoint objects to persist.

        Returns:
            Number of rows inserted (0 when *points* is empty).
        """
        if not points:
            return 0
        rows = [_point_to_row(p) for p in points]
        self._conn.executemany(_INSERT_ROW, rows)
        return len(rows)

    def read_telemetry(
        self,
        component_id: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[TelemetryPoint]:
        """Query stored TelemetryPoint records with optional filters.

        All three filter parameters are independent and combinable.

        Args:
            component_id: When provided, return only rows for this component.
            since:        When provided, return only rows where
                          window_start >= since.
            until:        When provided, return only rows where
                          window_start <= until.

        Returns:
            List of TelemetryPoint objects, ordered by (component_id,
            window_start) ascending.
        """
        query = "SELECT * FROM telemetry"
        conditions: list[str] = []
        params: list[object] = []

        if component_id is not None:
            conditions.append("component_id = ?")
            params.append(component_id)
        if since is not None:
            conditions.append("window_start >= ?")
            params.append(_to_naive_utc(since))
        if until is not None:
            conditions.append("window_start <= ?")
            params.append(_to_naive_utc(until))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY component_id, window_start"

        rows = self._conn.execute(query, params).fetchall()
        return [_row_to_point(row) for row in rows]

    def row_count(self) -> int:
        """Return the total number of rows currently stored in the table."""
        result = self._conn.execute("SELECT COUNT(*) FROM telemetry").fetchone()
        return int(result[0])

    def close(self) -> None:
        """Close the DuckDB connection and release all resources."""
        self._conn.close()

    def __enter__(self) -> TelemetryStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
