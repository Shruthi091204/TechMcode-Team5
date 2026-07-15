from __future__ import annotations

import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

import pytest

from contracts.schemas import TelemetryPoint
from src.rca.detect.window import build_metric_windows
from src.rca.ingest.flow_to_kpi import FlowRecord, aggregate_flows, load_flow_csv

_UTC = timezone.utc

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

IP_MAP: dict[str, str] = {
    "10.0.0.1": "db-01",
    "10.0.0.2": "app-01",
    "10.0.0.3": "web-01",
}

_BASE_EPOCH = 1_000_000.0  # arbitrary stable Unix epoch (2001-09-08)
_WINDOW = 30               # seconds


def _rec(
    time_epoch: float = _BASE_EPOCH,
    src_ip: str = "10.0.0.1",
    dst_ip: str = "10.0.0.2",
    src_port: int = 12345,
    dst_port: int = 5432,
    frame_len: int = 500,
) -> FlowRecord:
    return FlowRecord(
        time_epoch=time_epoch,
        src_ip=src_ip,
        dst_ip=dst_ip,
        src_port=src_port,
        dst_port=dst_port,
        frame_len=frame_len,
    )


def _window_start(epoch: float) -> datetime:
    """Mirror the _floor_to_window logic for test assertions."""
    boundary = int(epoch) // _WINDOW * _WINDOW
    return datetime.fromtimestamp(boundary, tz=_UTC)


# ---------------------------------------------------------------------------
# aggregate_flows — invalid window_seconds
# ---------------------------------------------------------------------------


def test_zero_window_seconds_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        aggregate_flows([], IP_MAP, window_seconds=0)


def test_negative_window_seconds_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        aggregate_flows([], IP_MAP, window_seconds=-5)


# ---------------------------------------------------------------------------
# aggregate_flows — empty input
# ---------------------------------------------------------------------------


def test_empty_records_returns_empty_list():
    assert aggregate_flows([], IP_MAP) == []


def test_empty_records_is_list():
    assert isinstance(aggregate_flows([], IP_MAP), list)


# ---------------------------------------------------------------------------
# aggregate_flows — no matching IPs
# ---------------------------------------------------------------------------


def test_no_matching_ip_returns_empty():
    records = [_rec(src_ip="99.99.99.99", dst_ip="88.88.88.88")]
    assert aggregate_flows(records, IP_MAP) == []


def test_empty_ip_map_returns_empty():
    records = [_rec()]
    assert aggregate_flows(records, {}) == []


# ---------------------------------------------------------------------------
# aggregate_flows — basic output shape
# ---------------------------------------------------------------------------


def test_single_record_produces_telemetry_point():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) >= 1


def test_output_items_are_telemetry_points():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert all(isinstance(tp, TelemetryPoint) for tp in result)


def test_single_record_both_known_ips_produces_two_points():
    """Packet between two known components contributes to both."""
    records = [_rec(src_ip="10.0.0.1", dst_ip="10.0.0.2")]
    result = aggregate_flows(records, IP_MAP)
    component_ids = {tp.component_id for tp in result}
    assert "db-01" in component_ids
    assert "app-01" in component_ids


# ---------------------------------------------------------------------------
# aggregate_flows — component_id mapping
# ---------------------------------------------------------------------------


def test_component_id_from_src_ip():
    records = [_rec(src_ip="10.0.0.1", dst_ip="99.99.99.99")]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    assert result[0].component_id == "db-01"


def test_component_id_from_dst_ip():
    records = [_rec(src_ip="99.99.99.99", dst_ip="10.0.0.2")]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    assert result[0].component_id == "app-01"


# ---------------------------------------------------------------------------
# aggregate_flows — window_start
# ---------------------------------------------------------------------------


def test_window_start_is_utc_aware():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    for tp in result:
        assert tp.window_start.tzinfo is not None


def test_window_start_floored_to_boundary():
    epoch = _BASE_EPOCH + 14.9  # within first 30-second window
    records = [_rec(time_epoch=epoch, dst_ip="99.99.99.99")]  # only src known
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    expected_ws = _window_start(epoch)
    assert result[0].window_start == expected_ws


def test_two_packets_in_different_windows_produce_separate_points():
    r1 = _rec(time_epoch=_BASE_EPOCH, dst_ip="99.99.99.99")
    r2 = _rec(time_epoch=_BASE_EPOCH + _WINDOW, dst_ip="99.99.99.99")  # next window
    result = aggregate_flows([r1, r2], IP_MAP)
    assert len(result) == 2
    windows = {tp.window_start for tp in result}
    assert len(windows) == 2


def test_two_packets_in_same_window_produce_one_point():
    # _BASE_EPOCH (1_000_000) is 10 s into its 30-second window (boundary 999_990).
    # Adding 5 s keeps both packets inside that same window.
    r1 = _rec(time_epoch=_BASE_EPOCH, dst_ip="99.99.99.99")
    r2 = _rec(time_epoch=_BASE_EPOCH + 5.0, dst_ip="99.99.99.99")
    result = aggregate_flows([r1, r2], IP_MAP)
    assert len(result) == 1


# ---------------------------------------------------------------------------
# aggregate_flows — throughput_mbps
# ---------------------------------------------------------------------------


def test_throughput_calculation():
    """throughput_mbps = sum(frame_len bytes) × 8 / (window_seconds × 1_000_000)."""
    frame_len = 1250  # bytes
    records = [_rec(frame_len=frame_len, dst_ip="99.99.99.99")]
    result = aggregate_flows(records, IP_MAP, window_seconds=_WINDOW)
    assert len(result) == 1
    expected = frame_len * 8.0 / (_WINDOW * 1_000_000.0)
    assert math.isclose(result[0].throughput_mbps, expected, rel_tol=1e-9)


def test_throughput_sums_all_packets_in_window():
    records = [
        _rec(frame_len=1000, dst_ip="99.99.99.99"),
        _rec(frame_len=2000, time_epoch=_BASE_EPOCH + 5.0, dst_ip="99.99.99.99"),
    ]
    result = aggregate_flows(records, IP_MAP, window_seconds=_WINDOW)
    assert len(result) == 1
    expected = 3000 * 8.0 / (_WINDOW * 1_000_000.0)
    assert math.isclose(result[0].throughput_mbps, expected, rel_tol=1e-9)


def test_throughput_is_non_negative():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.throughput_mbps >= 0.0 for tp in result)


# ---------------------------------------------------------------------------
# aggregate_flows — connection_count
# ---------------------------------------------------------------------------


def test_connection_count_unique_4_tuples():
    """Three records with the same 4-tuple → one unique connection."""
    records = [
        _rec(time_epoch=_BASE_EPOCH + i, dst_ip="99.99.99.99")
        for i in range(3)
    ]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    assert result[0].connection_count == 1


def test_connection_count_different_src_ports():
    """Three distinct src_ports → three unique connections."""
    records = [
        _rec(time_epoch=_BASE_EPOCH + i, src_port=10000 + i, dst_ip="99.99.99.99")
        for i in range(3)
    ]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    assert result[0].connection_count == 3


def test_connection_count_is_non_negative():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.connection_count >= 0 for tp in result)


# ---------------------------------------------------------------------------
# aggregate_flows — jitter_ms and latency_ms
# ---------------------------------------------------------------------------


def test_single_packet_jitter_is_zero():
    records = [_rec(dst_ip="99.99.99.99")]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    assert result[0].jitter_ms == 0.0


def test_single_packet_latency_is_zero():
    records = [_rec(dst_ip="99.99.99.99")]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    assert result[0].latency_ms == 0.0


def test_two_packets_jitter_is_zero_one_gap():
    """Two packets produce one inter-arrival gap — stdev requires 2+ gaps."""
    records = [
        _rec(time_epoch=_BASE_EPOCH, dst_ip="99.99.99.99"),
        _rec(time_epoch=_BASE_EPOCH + 0.1, dst_ip="99.99.99.99"),
    ]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    assert result[0].jitter_ms == 0.0


def test_two_packets_latency_half_mean_gap():
    gap_seconds = 0.1
    records = [
        _rec(time_epoch=_BASE_EPOCH, dst_ip="99.99.99.99"),
        _rec(time_epoch=_BASE_EPOCH + gap_seconds, dst_ip="99.99.99.99"),
    ]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    expected_latency = gap_seconds * 1_000.0 / 2.0
    assert math.isclose(result[0].latency_ms, expected_latency, rel_tol=1e-9)


def test_three_packets_jitter_stdev_of_gaps():
    records = [
        _rec(time_epoch=_BASE_EPOCH + 0.0, dst_ip="99.99.99.99"),
        _rec(time_epoch=_BASE_EPOCH + 0.1, dst_ip="99.99.99.99"),
        _rec(time_epoch=_BASE_EPOCH + 0.3, dst_ip="99.99.99.99"),
    ]
    result = aggregate_flows(records, IP_MAP)
    assert len(result) == 1
    gaps_ms = [100.0, 200.0]
    expected_jitter = statistics.stdev(gaps_ms)
    assert math.isclose(result[0].jitter_ms, expected_jitter, rel_tol=1e-9)


def test_jitter_is_non_negative():
    records = [_rec(time_epoch=_BASE_EPOCH + i * 0.05, dst_ip="99.99.99.99") for i in range(5)]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.jitter_ms >= 0.0 for tp in result)


def test_latency_is_non_negative():
    records = [_rec(time_epoch=_BASE_EPOCH + i * 0.05, dst_ip="99.99.99.99") for i in range(5)]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.latency_ms >= 0.0 for tp in result)


# ---------------------------------------------------------------------------
# aggregate_flows — defaulted fields
# ---------------------------------------------------------------------------


def test_packet_loss_pct_defaults_to_zero():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.packet_loss_pct == 0.0 for tp in result)


def test_error_rate_defaults_to_zero():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.error_rate == 0.0 for tp in result)


def test_cpu_pct_defaults_to_zero():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.cpu_pct == 0.0 for tp in result)


def test_mem_pct_defaults_to_zero():
    records = [_rec()]
    result = aggregate_flows(records, IP_MAP)
    assert all(tp.mem_pct == 0.0 for tp in result)


# ---------------------------------------------------------------------------
# aggregate_flows — multiple components
# ---------------------------------------------------------------------------


def test_multiple_components_produce_separate_telemetry_points():
    records = [
        _rec(src_ip="10.0.0.1", dst_ip="99.99.99.99"),  # db-01
        _rec(src_ip="10.0.0.2", dst_ip="99.99.99.99"),  # app-01
    ]
    result = aggregate_flows(records, IP_MAP)
    component_ids = {tp.component_id for tp in result}
    assert "db-01" in component_ids
    assert "app-01" in component_ids


def test_multiple_components_independent_windows():
    """Components in the same window are separate TelemetryPoints."""
    records = [
        _rec(src_ip="10.0.0.1", dst_ip="99.99.99.99", frame_len=100),
        _rec(src_ip="10.0.0.2", dst_ip="99.99.99.99", frame_len=200),
    ]
    result = aggregate_flows(records, IP_MAP)
    db01 = next(tp for tp in result if tp.component_id == "db-01")
    app01 = next(tp for tp in result if tp.component_id == "app-01")
    expected_db = 100 * 8.0 / (_WINDOW * 1_000_000.0)
    expected_app = 200 * 8.0 / (_WINDOW * 1_000_000.0)
    assert math.isclose(db01.throughput_mbps, expected_db, rel_tol=1e-9)
    assert math.isclose(app01.throughput_mbps, expected_app, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# aggregate_flows — deterministic ordering
# ---------------------------------------------------------------------------


def test_output_sorted_by_component_then_window_start():
    records = [
        _rec(src_ip="10.0.0.3", dst_ip="99.99.99.99"),  # web-01
        _rec(src_ip="10.0.0.1", dst_ip="99.99.99.99"),  # db-01
    ]
    result = aggregate_flows(records, IP_MAP)
    ids = [tp.component_id for tp in result]
    assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# aggregate_flows — TelemetryPoint contract validity
# ---------------------------------------------------------------------------


def test_all_outputs_satisfy_telemetry_point_contract():
    """Pydantic re-validation must pass for all outputs."""
    records = [
        _rec(src_ip="10.0.0.1", dst_ip="99.99.99.99"),
        _rec(src_ip="10.0.0.2", dst_ip="99.99.99.99"),
        _rec(time_epoch=_BASE_EPOCH + _WINDOW, src_ip="10.0.0.1", dst_ip="99.99.99.99"),
    ]
    result = aggregate_flows(records, IP_MAP)
    for tp in result:
        TelemetryPoint.model_validate(tp.model_dump())


# ---------------------------------------------------------------------------
# aggregate_flows — downstream pipeline compatibility
# ---------------------------------------------------------------------------


def test_output_compatible_with_build_metric_windows():
    """aggregate_flows output must feed directly into build_metric_windows."""
    records = [
        _rec(
            time_epoch=_BASE_EPOCH + i * _WINDOW,
            src_ip="10.0.0.1",
            dst_ip="99.99.99.99",
        )
        for i in range(5)
    ]
    telemetry = aggregate_flows(records, IP_MAP)
    windows = build_metric_windows(telemetry)
    assert len(windows) >= 1
    db01_windows = [w for w in windows if w.component_id == "db-01"]
    assert len(db01_windows) > 0


# ---------------------------------------------------------------------------
# load_flow_csv — file errors
# ---------------------------------------------------------------------------


def test_missing_csv_raises_file_not_found(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="flow CSV not found"):
        load_flow_csv(tmp_path / "nonexistent.csv", IP_MAP)


# ---------------------------------------------------------------------------
# load_flow_csv — valid CSV
# ---------------------------------------------------------------------------


def test_load_flow_csv_empty_data_rows(tmp_path: Path):
    csv_file = tmp_path / "flows.csv"
    csv_file.write_text("frame.time_epoch,ip.src,ip.dst,tcp.srcport,tcp.dstport,frame.len\n")
    result = load_flow_csv(csv_file, IP_MAP)
    assert result == []


def test_load_flow_csv_single_row(tmp_path: Path):
    csv_file = tmp_path / "flows.csv"
    csv_file.write_text(
        "frame.time_epoch,ip.src,ip.dst,tcp.srcport,tcp.dstport,frame.len\n"
        f"{_BASE_EPOCH},10.0.0.1,99.99.99.99,12345,5432,1000\n"
    )
    result = load_flow_csv(csv_file, IP_MAP)
    assert len(result) == 1
    assert result[0].component_id == "db-01"


def test_load_flow_csv_non_tcp_packet_uses_zero_ports(tmp_path: Path):
    """Rows with empty tcp.srcport / tcp.dstport (ICMP, etc.) must not crash."""
    csv_file = tmp_path / "flows.csv"
    csv_file.write_text(
        "frame.time_epoch,ip.src,ip.dst,tcp.srcport,tcp.dstport,frame.len\n"
        f"{_BASE_EPOCH},10.0.0.1,99.99.99.99,,,512\n"
    )
    result = load_flow_csv(csv_file, IP_MAP)
    assert len(result) == 1
    assert result[0].connection_count == 1


def test_load_flow_csv_malformed_row_skipped(tmp_path: Path):
    csv_file = tmp_path / "flows.csv"
    csv_file.write_text(
        "frame.time_epoch,ip.src,ip.dst,tcp.srcport,tcp.dstport,frame.len\n"
        f"{_BASE_EPOCH},10.0.0.1,99.99.99.99,12345,5432,1000\n"
        "not_a_float,bad,bad,bad,bad,bad\n"   # malformed — must be skipped
    )
    result = load_flow_csv(csv_file, IP_MAP)
    assert len(result) == 1


def test_load_flow_csv_multiple_rows(tmp_path: Path):
    csv_file = tmp_path / "flows.csv"
    rows = "\n".join(
        f"{_BASE_EPOCH + i},10.0.0.1,99.99.99.99,12345,5432,500"
        for i in range(4)
    )
    csv_file.write_text(
        "frame.time_epoch,ip.src,ip.dst,tcp.srcport,tcp.dstport,frame.len\n" + rows + "\n"
    )
    result = load_flow_csv(csv_file, IP_MAP)
    assert len(result) == 1  # all in same 30-second window
    expected_throughput = (4 * 500) * 8.0 / (_WINDOW * 1_000_000.0)
    assert math.isclose(result[0].throughput_mbps, expected_throughput, rel_tol=1e-9)


def test_load_flow_csv_window_seconds_forwarded(tmp_path: Path):
    """window_seconds parameter must be passed through to aggregate_flows.

    Use epochs that are exactly aligned to a 60-second boundary (999_960)
    so that the 30-second offset lands in:
      - a different 30-second window (999_960 vs 999_990), but
      - the same 60-second window (both ≥ 999_960, < 1_000_020).
    """
    epoch1 = 999_960.0   # 60-second boundary: 60 × 16_666
    epoch2 = 999_990.0   # 30 s later — new 30s window, same 60s window
    csv_file = tmp_path / "flows.csv"
    csv_file.write_text(
        "frame.time_epoch,ip.src,ip.dst,tcp.srcport,tcp.dstport,frame.len\n"
        f"{epoch1},10.0.0.1,99.99.99.99,12345,5432,1000\n"
        f"{epoch2},10.0.0.1,99.99.99.99,12345,5432,1000\n"
    )
    result_30s = load_flow_csv(csv_file, IP_MAP, window_seconds=30)
    result_60s = load_flow_csv(csv_file, IP_MAP, window_seconds=60)
    assert len(result_30s) == 2
    assert len(result_60s) == 1
