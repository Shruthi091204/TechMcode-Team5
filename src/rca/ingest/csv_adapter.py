from __future__ import annotations

import csv
from pathlib import Path

from contracts.schemas import TelemetryPoint


def load_telemetry_csv(csv_path: str | Path) -> list[TelemetryPoint]:
    """Read a canonical telemetry CSV and return one validated TelemetryPoint per row.

    The CSV must carry exactly the columns defined by TelemetryPoint:
        component_id, window_start, latency_ms, jitter_ms, packet_loss_pct,
        throughput_mbps, error_rate, connection_count, cpu_pct, mem_pct

    Pydantic coerces each CSV string value to the correct Python type.
    Any row that violates a contract constraint raises ValidationError immediately.

    Raises:
        FileNotFoundError: if csv_path does not exist on disk.
        pydantic.ValidationError: if any row fails the TelemetryPoint contract.
    """
    resolved = Path(csv_path)
    if not resolved.exists():
        raise FileNotFoundError(f"telemetry CSV not found: {resolved}")

    with resolved.open(encoding="utf-8", newline="") as file_handle:
        reader = csv.DictReader(file_handle)
        return [TelemetryPoint.model_validate(row) for row in reader]
