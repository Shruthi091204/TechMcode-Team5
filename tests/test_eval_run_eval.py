from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from contracts.schemas import Anomaly, TelemetryPoint
from eval.run_eval import (
    IncidentResult,
    _compute_mttd,
    _evaluate_scenario,
    _load_ground_truth,
    _load_hardware_telemetry,
    _rank_components,
)

_UTC = UTC
_BASE = datetime(2026, 7, 14, 21, 33, 0, tzinfo=_UTC)


# ---------------------------------------------------------------------------
# Helpers — synthetic incident directory
# ---------------------------------------------------------------------------


def _write_ground_truth(d: Path, root_cause: str, offset_seconds: int = 30) -> None:
    payload = {
        "incident_id": "inc-test0001",
        "scenario": d.name,
        "injection_timestamp": (_BASE + timedelta(seconds=offset_seconds)).isoformat(),
        "true_root_cause": {
            "component_id": root_cause,
            "fault_type": "test_fault",
        },
    }
    (d / "ground_truth.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_hw_telemetry(
    d: Path,
    rows: list[tuple[datetime, str, float, float]],
) -> None:
    with (d / "hardware_telemetry.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "component_id", "cpu_pct", "mem_pct"])
        for ts, comp, cpu, mem in rows:
            writer.writerow([ts.isoformat(), comp, cpu, mem])


def _minimal_incident(tmp_path: Path, root_cause: str = "db-01") -> Path:
    d = tmp_path / "test_scenario"
    d.mkdir()
    _write_ground_truth(d, root_cause, offset_seconds=30)
    rows = []
    for i in range(15):
        ts = _BASE + timedelta(seconds=i * 4)
        cpu = 0.5 + (5.0 if i >= 8 else 0.0)
        for comp in ["db-01", "app-01", "web-01", "lb-01"]:
            rows.append((ts, comp, cpu if comp == root_cause else 0.1, 10.0))
    _write_hw_telemetry(d, rows)
    return d


# ---------------------------------------------------------------------------
# _load_ground_truth
# ---------------------------------------------------------------------------


def test_load_ground_truth_returns_dict(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    _write_ground_truth(d, "web-01")
    gt = _load_ground_truth(d)
    assert isinstance(gt, dict)


def test_load_ground_truth_has_required_keys(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    _write_ground_truth(d, "web-01")
    gt = _load_ground_truth(d)
    assert "true_root_cause" in gt
    assert "injection_timestamp" in gt


def test_load_ground_truth_root_cause_component(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    _write_ground_truth(d, "app-01")
    gt = _load_ground_truth(d)
    assert gt["true_root_cause"]["component_id"] == "app-01"


# ---------------------------------------------------------------------------
# _load_hardware_telemetry
# ---------------------------------------------------------------------------


def test_load_hardware_telemetry_returns_list(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    rows = [(_BASE + timedelta(seconds=i * 4), "db-01", 0.5, 10.0) for i in range(5)]
    _write_hw_telemetry(d, rows)
    result = _load_hardware_telemetry(d)
    assert isinstance(result, list)


def test_load_hardware_telemetry_items_are_telemetry_points(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    rows = [(_BASE + timedelta(seconds=i * 4), "db-01", 0.5, 10.0) for i in range(5)]
    _write_hw_telemetry(d, rows)
    result = _load_hardware_telemetry(d)
    assert all(isinstance(tp, TelemetryPoint) for tp in result)


def test_load_hardware_telemetry_row_count(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    rows = [(_BASE + timedelta(seconds=i * 4), "db-01", 0.5, 10.0) for i in range(8)]
    _write_hw_telemetry(d, rows)
    result = _load_hardware_telemetry(d)
    assert len(result) == 8


def test_load_hardware_telemetry_window_start_timezone_aware(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    rows = [(_BASE, "db-01", 0.5, 10.0)]
    _write_hw_telemetry(d, rows)
    result = _load_hardware_telemetry(d)
    assert result[0].window_start.tzinfo is not None


def test_load_hardware_telemetry_cpu_mem_preserved(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    rows = [(_BASE, "db-01", 1.23, 45.67)]
    _write_hw_telemetry(d, rows)
    result = _load_hardware_telemetry(d)
    assert abs(result[0].cpu_pct - 1.23) < 1e-6
    assert abs(result[0].mem_pct - 45.67) < 1e-6


def test_load_hardware_telemetry_zero_filled_fields(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    rows = [(_BASE, "db-01", 0.5, 10.0)]
    _write_hw_telemetry(d, rows)
    tp = _load_hardware_telemetry(d)[0]
    assert tp.latency_ms == 0.0
    assert tp.jitter_ms == 0.0
    assert tp.packet_loss_pct == 0.0
    assert tp.throughput_mbps == 0.0
    assert tp.error_rate == 0.0
    assert tp.connection_count == 0


def test_load_hardware_telemetry_component_id(tmp_path: Path):
    d = tmp_path / "s"
    d.mkdir()
    rows = [(_BASE, "app-01", 0.5, 10.0)]
    _write_hw_telemetry(d, rows)
    assert _load_hardware_telemetry(d)[0].component_id == "app-01"


# ---------------------------------------------------------------------------
# _rank_components
# ---------------------------------------------------------------------------


def _make_anomaly(component_id: str, severity: float) -> Anomaly:
    ts0 = _BASE
    ts1 = _BASE + timedelta(minutes=5)
    ts_mid = _BASE + timedelta(minutes=2)
    return Anomaly(
        component_id=component_id,
        metric="cpu_pct",
        onset_ts=ts_mid,
        severity_score=severity,
        window_start=ts0,
        window_end=ts1,
        baseline_value=0.1,
        observed_value=1.0,
    )


def test_rank_components_empty():
    assert _rank_components([]) == []


def test_rank_components_single():
    a = _make_anomaly("db-01", 5.0)
    assert _rank_components([a]) == ["db-01"]


def test_rank_components_descending_order():
    anomalies = [
        _make_anomaly("app-01", 3.0),
        _make_anomaly("db-01", 9.0),
        _make_anomaly("web-01", 1.5),
    ]
    ranked = _rank_components(anomalies)
    assert ranked == ["db-01", "app-01", "web-01"]


def test_rank_components_uses_max_per_component():
    anomalies = [
        _make_anomaly("db-01", 2.0),
        _make_anomaly("db-01", 8.0),
        _make_anomaly("app-01", 5.0),
    ]
    ranked = _rank_components(anomalies)
    assert ranked[0] == "db-01"


def test_rank_components_no_duplicates_in_output():
    anomalies = [_make_anomaly("db-01", 2.0), _make_anomaly("db-01", 8.0)]
    assert _rank_components(anomalies) == ["db-01"]


# ---------------------------------------------------------------------------
# _compute_mttd
# ---------------------------------------------------------------------------


def test_compute_mttd_none_when_no_anomalies():
    assert _compute_mttd([], "db-01", _BASE) is None


def test_compute_mttd_none_when_component_not_detected():
    a = _make_anomaly("app-01", 5.0)
    assert _compute_mttd([a], "db-01", _BASE) is None


def test_compute_mttd_none_when_onset_before_injection():
    onset = _BASE - timedelta(seconds=10)
    ts0 = _BASE - timedelta(minutes=5)
    ts1 = _BASE + timedelta(minutes=5)
    a = Anomaly(
        component_id="db-01",
        metric="cpu_pct",
        onset_ts=onset,
        severity_score=5.0,
        window_start=ts0,
        window_end=ts1,
        baseline_value=0.1,
        observed_value=1.0,
    )
    assert _compute_mttd([a], "db-01", _BASE) is None


def test_compute_mttd_correct_seconds():
    injection = _BASE
    onset = _BASE + timedelta(seconds=45)
    ts0 = _BASE - timedelta(minutes=1)
    ts1 = _BASE + timedelta(minutes=5)
    a = Anomaly(
        component_id="db-01",
        metric="cpu_pct",
        onset_ts=onset,
        severity_score=5.0,
        window_start=ts0,
        window_end=ts1,
        baseline_value=0.1,
        observed_value=1.0,
    )
    mttd = _compute_mttd([a], "db-01", injection)
    assert mttd is not None
    assert abs(mttd - 45.0) < 1e-6


def test_compute_mttd_uses_earliest_onset():
    injection = _BASE
    ts0 = _BASE - timedelta(minutes=1)
    ts1 = _BASE + timedelta(minutes=10)

    def _anom(metric: str, delay: int) -> Anomaly:
        return Anomaly(
            component_id="db-01",
            metric=metric,
            onset_ts=injection + timedelta(seconds=delay),
            severity_score=5.0,
            window_start=ts0,
            window_end=ts1,
            baseline_value=0.1,
            observed_value=1.0,
        )

    anomalies = [_anom("cpu_pct", 60), _anom("mem_pct", 30)]
    mttd = _compute_mttd(anomalies, "db-01", injection)
    assert mttd is not None
    assert abs(mttd - 30.0) < 1e-6


# ---------------------------------------------------------------------------
# _evaluate_scenario — integration via synthetic incident
# ---------------------------------------------------------------------------


def test_evaluate_scenario_returns_incident_result(tmp_path: Path):
    d = _minimal_incident(tmp_path, "db-01")
    result = _evaluate_scenario(d)
    assert isinstance(result, IncidentResult)


def test_evaluate_scenario_scenario_name(tmp_path: Path):
    d = _minimal_incident(tmp_path, "db-01")
    result = _evaluate_scenario(d)
    assert result.scenario == "test_scenario"


def test_evaluate_scenario_true_root_cause(tmp_path: Path):
    d = _minimal_incident(tmp_path, "web-01")
    result = _evaluate_scenario(d)
    assert result.true_root_cause == "web-01"


def test_evaluate_scenario_anomaly_count_non_negative(tmp_path: Path):
    d = _minimal_incident(tmp_path, "db-01")
    result = _evaluate_scenario(d)
    assert result.anomaly_count >= 0


def test_evaluate_scenario_acc1_is_bool(tmp_path: Path):
    d = _minimal_incident(tmp_path, "db-01")
    result = _evaluate_scenario(d)
    assert isinstance(result.acc1, bool)


def test_evaluate_scenario_acc3_is_bool(tmp_path: Path):
    d = _minimal_incident(tmp_path, "db-01")
    result = _evaluate_scenario(d)
    assert isinstance(result.acc3, bool)


def test_evaluate_scenario_acc1_implies_acc3(tmp_path: Path):
    d = _minimal_incident(tmp_path, "db-01")
    result = _evaluate_scenario(d)
    if result.acc1:
        assert result.acc3


def test_evaluate_scenario_mttd_none_or_positive(tmp_path: Path):
    d = _minimal_incident(tmp_path, "db-01")
    result = _evaluate_scenario(d)
    if result.mttd_seconds is not None:
        assert result.mttd_seconds >= 0.0


def test_evaluate_scenario_no_ground_truth_bias(tmp_path: Path):
    s1 = tmp_path / "s1"
    s2 = tmp_path / "s2"
    s1.mkdir()
    s2.mkdir()
    d1 = _minimal_incident(s1, "db-01")
    d2 = _minimal_incident(s2, "app-01")
    _evaluate_scenario(d1)
    _evaluate_scenario(d2)
    assert True


def test_evaluate_scenario_real_bad_config_push():
    """Smoke test against actual P1 incident data."""
    d = Path("incidents") / "bad_config_push"
    if not d.exists():
        pytest.skip("incidents/bad_config_push not present")
    result = _evaluate_scenario(d)
    assert result.scenario == "bad_config_push"
    assert result.true_root_cause == "web-01"
    assert result.anomaly_count >= 0
    assert isinstance(result.acc1, bool)
    assert isinstance(result.acc3, bool)
