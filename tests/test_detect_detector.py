from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from contracts.schemas import Anomaly
from src.rca.detect.baseline import compute_mad_scores
from src.rca.detect.changepoint import find_changepoint
from src.rca.detect.detector import detect_anomalies
from src.rca.detect.window import MetricWindow, build_metric_windows
from src.rca.ingest.csv_adapter import load_telemetry_csv

FIXTURES = Path(__file__).resolve().parents[1] / "contracts" / "fixtures"
_UTC = UTC


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_window(
    values: list[float],
    component_id: str = "test-01",
    metric: str = "latency_ms",
    base_ts: datetime | None = None,
    step_seconds: int = 30,
) -> MetricWindow:
    if base_ts is None:
        base_ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=_UTC)
    timestamps = tuple(
        base_ts + timedelta(seconds=i * step_seconds) for i in range(len(values))
    )
    return MetricWindow(
        component_id=component_id,
        metric=metric,
        timestamps=timestamps,
        values=np.array(values, dtype=float),
    )


def _clear_step(pre_level: float = 10.0, post_level: float = 100.0, n: int = 20) -> MetricWindow:
    """Window with an obvious step change at the midpoint."""
    half = n // 2
    return _make_window([pre_level] * half + [post_level] * half)


# ---------------------------------------------------------------------------
# min_severity validation
# ---------------------------------------------------------------------------


def test_min_severity_negative_raises():
    with pytest.raises(ValueError, match="min_severity"):
        detect_anomalies([], min_severity=-0.001)


def test_min_severity_nan_raises():
    with pytest.raises(ValueError, match="min_severity"):
        detect_anomalies([], min_severity=float("nan"))


def test_min_severity_positive_infinity_raises():
    with pytest.raises(ValueError, match="min_severity"):
        detect_anomalies([], min_severity=float("inf"))


def test_min_severity_negative_infinity_raises():
    with pytest.raises(ValueError, match="min_severity"):
        detect_anomalies([], min_severity=float("-inf"))


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


def test_empty_windows_returns_empty_list():
    result = detect_anomalies([])
    assert result == []


def test_empty_windows_is_a_list():
    assert isinstance(detect_anomalies([]), list)


# ---------------------------------------------------------------------------
# Flat / no-change signal
# ---------------------------------------------------------------------------


def test_flat_signal_produces_no_anomaly():
    window = _make_window([50.0] * 20)
    result = detect_anomalies([window])
    assert result == []


def test_single_observation_produces_no_anomaly():
    window = _make_window([42.0])
    result = detect_anomalies([window])
    assert result == []


# ---------------------------------------------------------------------------
# Clear step-change — basic emission
# ---------------------------------------------------------------------------


def test_clear_step_emits_anomaly():
    window = _clear_step()
    result = detect_anomalies([window])
    assert len(result) == 1


def test_output_items_are_anomaly_objects():
    window = _clear_step()
    result = detect_anomalies([window])
    assert all(isinstance(a, Anomaly) for a in result)


# ---------------------------------------------------------------------------
# Anomaly field correctness
# ---------------------------------------------------------------------------


def test_component_id_comes_from_window():
    window = _clear_step()
    result = detect_anomalies([window])
    assert len(result) == 1
    assert result[0].component_id == window.component_id


def test_metric_comes_from_window():
    window = _clear_step()
    result = detect_anomalies([window])
    assert len(result) == 1
    assert result[0].metric == window.metric


def test_onset_ts_is_timezone_aware():
    window = _clear_step()
    result = detect_anomalies([window])
    assert len(result) == 1
    assert result[0].onset_ts.tzinfo is not None


def test_window_start_equals_first_timestamp():
    window = _clear_step()
    result = detect_anomalies([window])
    assert len(result) == 1
    assert result[0].window_start == window.timestamps[0]


def test_window_end_equals_last_timestamp():
    window = _clear_step()
    result = detect_anomalies([window])
    assert len(result) == 1
    assert result[0].window_end == window.timestamps[-1]


def test_onset_ts_within_anomaly_window():
    window = _clear_step()
    result = detect_anomalies([window])
    assert len(result) == 1
    a = result[0]
    assert a.window_start <= a.onset_ts <= a.window_end


# ---------------------------------------------------------------------------
# baseline_value and observed_value
# ---------------------------------------------------------------------------


def test_baseline_value_is_pre_onset_median():
    """baseline_value must equal the median of the values BEFORE the onset."""
    window = _clear_step(pre_level=10.0, post_level=100.0, n=20)
    result = detect_anomalies([window])
    assert len(result) == 1
    a = result[0]
    bp = find_changepoint(window).breakpoint_index
    assert bp is not None
    pre_median = float(np.median(window.values[:bp]))
    assert math.isclose(a.baseline_value, pre_median, abs_tol=1e-9)


def test_observed_value_is_post_onset_mean():
    """observed_value must equal the mean of values AT and AFTER the onset."""
    window = _clear_step(pre_level=10.0, post_level=100.0, n=20)
    result = detect_anomalies([window])
    assert len(result) == 1
    a = result[0]
    bp = find_changepoint(window).breakpoint_index
    assert bp is not None
    post_mean = float(np.mean(window.values[bp:]))
    assert math.isclose(a.observed_value, post_mean, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# severity_score
# ---------------------------------------------------------------------------


def test_severity_score_is_non_negative():
    window = _clear_step()
    result = detect_anomalies([window])
    assert all(a.severity_score >= 0.0 for a in result)


def test_severity_score_is_finite():
    window = _clear_step()
    result = detect_anomalies([window])
    assert all(math.isfinite(a.severity_score) for a in result)


def test_severity_follows_pre_onset_mad_formula():
    """Verify severity = |post_mean - pre_median| / pre_MAD when MAD > 0."""
    window = _clear_step(pre_level=10.0, post_level=100.0, n=20)
    result = detect_anomalies([window])
    assert len(result) == 1
    a = result[0]
    bp = find_changepoint(window).breakpoint_index
    assert bp is not None
    pre = window.values[:bp]
    post = window.values[bp:]
    bl = compute_mad_scores(pre)
    observed = float(np.mean(post))
    expected_severity = abs(observed - bl.median) / bl.mad if bl.mad > 0.0 else abs(observed - bl.median)
    assert math.isclose(a.severity_score, expected_severity, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Zero-MAD fallback
# ---------------------------------------------------------------------------


def test_zero_mad_pre_segment_produces_finite_severity():
    """
    When the pre-onset segment is perfectly flat (MAD = 0), the fallback
    severity = |post_mean - pre_median| must be finite and non-negative.
    """
    # Pre: all identical → MAD = 0; Post: different level
    window = _make_window([5.0] * 6 + [50.0] * 14)
    result = detect_anomalies([window])
    if result:
        a = result[0]
        assert math.isfinite(a.severity_score)
        assert a.severity_score >= 0.0


def test_zero_mad_fallback_severity_equals_absolute_deviation():
    """When MAD == 0, severity equals |post_mean - pre_median|."""
    # Construct a case where PELT detects a clean step
    window = _make_window([5.0] * 6 + [50.0] * 14)
    result = detect_anomalies([window])
    if result:
        a = result[0]
        bp = find_changepoint(window).breakpoint_index
        assert bp is not None
        pre = window.values[:bp]
        post = window.values[bp:]
        pre_median = float(np.median(pre))
        pre_mad = float(np.median(np.abs(pre - pre_median)))
        post_mean = float(np.mean(post))
        if pre_mad == 0.0:
            expected = abs(post_mean - pre_median)
            assert math.isclose(a.severity_score, expected, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# min_severity filtering
# ---------------------------------------------------------------------------


def test_min_severity_zero_retains_all_anomalies():
    window = _clear_step()
    result = detect_anomalies([window], min_severity=0.0)
    assert len(result) >= 1


def test_min_severity_very_high_suppresses_all():
    window = _clear_step()
    result = detect_anomalies([window], min_severity=1e9)
    assert result == []


def test_min_severity_filters_below_threshold():
    window = _clear_step()
    result_all = detect_anomalies([window], min_severity=0.0)
    if result_all:
        observed_severity = result_all[0].severity_score
        # Just above the observed severity → should be suppressed
        result_filtered = detect_anomalies([window], min_severity=observed_severity + 1.0)
        assert result_filtered == []


def test_min_severity_equality_retains_anomaly():
    """severity == min_severity must be retained (filter is strict <, not <=)."""
    window = _clear_step()
    result_all = detect_anomalies([window], min_severity=0.0)
    if result_all:
        exact_severity = result_all[0].severity_score
        result_at_boundary = detect_anomalies([window], min_severity=exact_severity)
        assert len(result_at_boundary) == 1


# ---------------------------------------------------------------------------
# Multiple windows — ordering
# ---------------------------------------------------------------------------


def test_multiple_windows_deterministic_ordering():
    """Output order must match input window order for emitted anomalies."""
    w1 = _make_window([10.0] * 10 + [100.0] * 10, component_id="aaa-01", metric="latency_ms")
    w2 = _make_window([10.0] * 10 + [100.0] * 10, component_id="bbb-01", metric="latency_ms")
    result = detect_anomalies([w1, w2])
    # Both should produce anomalies; their order must match input
    assert len(result) == 2
    assert result[0].component_id == "aaa-01"
    assert result[1].component_id == "bbb-01"


def test_flat_windows_interleaved_with_step_windows():
    """Flat windows must be silently skipped; step windows must be emitted in order."""
    flat = _make_window([10.0] * 20, component_id="flat-01")
    step = _make_window([10.0] * 10 + [100.0] * 10, component_id="step-01")
    result = detect_anomalies([flat, step])
    assert len(result) == 1
    assert result[0].component_id == "step-01"


# ---------------------------------------------------------------------------
# Anomaly contract validators
# ---------------------------------------------------------------------------


def test_anomaly_window_end_strictly_after_start():
    window = _clear_step()
    result = detect_anomalies([window])
    assert all(a.window_end > a.window_start for a in result)


def test_anomaly_onset_within_window_bounds():
    window = _clear_step()
    result = detect_anomalies([window])
    for a in result:
        assert a.window_start <= a.onset_ts <= a.window_end


# ---------------------------------------------------------------------------
# Fixture integration — db-01 / connection_count
# ---------------------------------------------------------------------------


def test_fixture_db01_connection_count_produces_anomaly():
    telemetry = load_telemetry_csv(FIXTURES / "telemetry.csv")
    windows = build_metric_windows(telemetry)
    db01_cc = next(
        (w for w in windows if w.component_id == "db-01" and w.metric == "connection_count"),
        None,
    )
    assert db01_cc is not None, "db-01/connection_count window not found in fixture"
    result = detect_anomalies([db01_cc])
    assert len(result) == 1, "expected exactly one Anomaly for db-01/connection_count"


def test_fixture_db01_connection_count_anomaly_fields():
    telemetry = load_telemetry_csv(FIXTURES / "telemetry.csv")
    windows = build_metric_windows(telemetry)
    db01_cc = next(
        w for w in windows if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = detect_anomalies([db01_cc])
    assert len(result) == 1
    a = result[0]

    assert a.component_id == "db-01"
    assert a.metric == "connection_count"
    assert a.onset_ts.tzinfo is not None
    assert a.window_start == db01_cc.timestamps[0]
    assert a.window_end == db01_cc.timestamps[-1]
    assert a.window_start <= a.onset_ts <= a.window_end


def test_fixture_db01_connection_count_severity_finite_and_positive():
    telemetry = load_telemetry_csv(FIXTURES / "telemetry.csv")
    windows = build_metric_windows(telemetry)
    db01_cc = next(
        w for w in windows if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = detect_anomalies([db01_cc])
    assert len(result) == 1
    a = result[0]
    assert math.isfinite(a.severity_score)
    assert a.severity_score > 0.0


def test_fixture_db01_connection_count_severity_matches_pre_onset_formula():
    """
    Severity must equal the formula applied to the actual PELT-detected onset,
    not the illustrative 6.2 from IMPLEMENTATION.md documentation.
    """
    telemetry = load_telemetry_csv(FIXTURES / "telemetry.csv")
    windows = build_metric_windows(telemetry)
    db01_cc = next(
        w for w in windows if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = detect_anomalies([db01_cc])
    assert len(result) == 1
    a = result[0]

    cp = find_changepoint(db01_cc)
    assert cp.breakpoint_index is not None
    pre = db01_cc.values[: cp.breakpoint_index]
    post = db01_cc.values[cp.breakpoint_index :]
    bl = compute_mad_scores(pre)
    observed = float(np.mean(post))
    expected_severity = abs(observed - bl.median) / bl.mad if bl.mad > 0.0 else abs(observed - bl.median)

    assert math.isclose(a.severity_score, expected_severity, rel_tol=1e-9)


def test_fixture_db01_baseline_value_is_pre_onset_median():
    telemetry = load_telemetry_csv(FIXTURES / "telemetry.csv")
    windows = build_metric_windows(telemetry)
    db01_cc = next(
        w for w in windows if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = detect_anomalies([db01_cc])
    assert len(result) == 1
    a = result[0]

    cp = find_changepoint(db01_cc)
    assert cp.breakpoint_index is not None
    pre_median = float(np.median(db01_cc.values[: cp.breakpoint_index]))
    assert math.isclose(a.baseline_value, pre_median, abs_tol=1e-9)


def test_fixture_db01_observed_value_is_post_onset_mean():
    telemetry = load_telemetry_csv(FIXTURES / "telemetry.csv")
    windows = build_metric_windows(telemetry)
    db01_cc = next(
        w for w in windows if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = detect_anomalies([db01_cc])
    assert len(result) == 1
    a = result[0]

    cp = find_changepoint(db01_cc)
    assert cp.breakpoint_index is not None
    post_mean = float(np.mean(db01_cc.values[cp.breakpoint_index :]))
    assert math.isclose(a.observed_value, post_mean, abs_tol=1e-9)


def test_fixture_full_pipeline_produces_anomalies():
    """End-to-end: CSV → windows → detect_anomalies produces at least one Anomaly."""
    telemetry = load_telemetry_csv(FIXTURES / "telemetry.csv")
    windows = build_metric_windows(telemetry)
    result = detect_anomalies(windows)
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(isinstance(a, Anomaly) for a in result)
