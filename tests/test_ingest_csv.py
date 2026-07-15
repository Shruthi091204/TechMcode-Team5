from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.schemas import TelemetryPoint
from src.rca.ingest.csv_adapter import load_telemetry_csv

FIXTURES = Path(__file__).resolve().parents[1] / "contracts" / "fixtures"
TELEMETRY_CSV = FIXTURES / "telemetry.csv"

_HEADER = (
    "component_id,window_start,latency_ms,jitter_ms,packet_loss_pct,"
    "throughput_mbps,error_rate,connection_count,cpu_pct,mem_pct\n"
)
_VALID_ROW = "db-01,2026-07-14T14:25:00Z,5.6,0.49,0.0,93.9,0.0009,121,41.9,59.5\n"


def test_fixture_loads_without_error() -> None:
    points = load_telemetry_csv(TELEMETRY_CSV)
    assert len(points) == 930


def test_accepts_string_path() -> None:
    points = load_telemetry_csv(str(TELEMETRY_CSV))
    assert len(points) == 930


def test_every_returned_item_is_telemetry_point() -> None:
    for point in load_telemetry_csv(TELEMETRY_CSV):
        assert isinstance(point, TelemetryPoint)


def test_window_start_is_timezone_aware() -> None:
    for point in load_telemetry_csv(TELEMETRY_CSV):
        assert point.window_start.tzinfo is not None


def test_missing_file_raises_file_not_found_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="telemetry CSV not found"):
        load_telemetry_csv(tmp_path / "nonexistent.csv")


def test_invalid_timestamp_raises_validation_error(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad_ts.csv"
    bad_csv.write_text(
        _HEADER + "db-01,NOT-A-TIMESTAMP,5.6,0.49,0.0,93.9,0.0009,121,41.9,59.5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_telemetry_csv(bad_csv)


def test_timezone_naive_timestamp_raises_validation_error(tmp_path: Path) -> None:
    bad_csv = tmp_path / "naive_ts.csv"
    bad_csv.write_text(
        _HEADER + "db-01,2026-07-14T14:25:00,5.6,0.49,0.0,93.9,0.0009,121,41.9,59.5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_telemetry_csv(bad_csv)


def test_negative_latency_raises_validation_error(tmp_path: Path) -> None:
    bad_csv = tmp_path / "neg_latency.csv"
    bad_csv.write_text(
        _HEADER + "db-01,2026-07-14T14:25:00Z,-1.0,0.49,0.0,93.9,0.0009,121,41.9,59.5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_telemetry_csv(bad_csv)


def test_packet_loss_above_100_raises_validation_error(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad_loss.csv"
    bad_csv.write_text(
        _HEADER + "db-01,2026-07-14T14:25:00Z,5.6,0.49,200.0,93.9,0.0009,121,41.9,59.5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_telemetry_csv(bad_csv)


def test_error_rate_above_1_raises_validation_error(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad_error_rate.csv"
    bad_csv.write_text(
        _HEADER + "db-01,2026-07-14T14:25:00Z,5.6,0.49,0.0,93.9,1.5,121,41.9,59.5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        load_telemetry_csv(bad_csv)


def test_single_valid_row_returns_correct_values(tmp_path: Path) -> None:
    single_csv = tmp_path / "single.csv"
    single_csv.write_text(_HEADER + _VALID_ROW, encoding="utf-8")
    points = load_telemetry_csv(single_csv)
    assert len(points) == 1
    point = points[0]
    assert point.component_id == "db-01"
    assert point.latency_ms == pytest.approx(5.6)
    assert point.connection_count == 121
    assert point.packet_loss_pct == pytest.approx(0.0)
