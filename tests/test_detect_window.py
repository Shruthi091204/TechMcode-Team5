from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pytest

from contracts.schemas import TelemetryPoint
from src.rca.detect.baseline import compute_mad_scores
from src.rca.detect.window import METRIC_FIELDS, MetricWindow, build_metric_windows
from src.rca.ingest.csv_adapter import load_telemetry_csv

FIXTURES = Path(__file__).resolve().parents[1] / "contracts" / "fixtures"

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
_NEXT_TS = datetime(2026, 1, 1, 0, 0, 30, tzinfo=timezone.utc)
_LAST_TS = datetime(2026, 1, 1, 0, 1, 0, tzinfo=timezone.utc)


def _make_point(component_id: str, ts: datetime, **overrides: object) -> TelemetryPoint:
    defaults: dict[str, object] = {
        "component_id": component_id,
        "window_start": ts,
        "latency_ms": 10.0,
        "jitter_ms": 0.5,
        "packet_loss_pct": 0.0,
        "throughput_mbps": 100.0,
        "error_rate": 0.001,
        "connection_count": 50,
        "cpu_pct": 30.0,
        "mem_pct": 40.0,
    }
    defaults.update(overrides)
    return TelemetryPoint.model_validate(defaults)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------

def test_empty_input_returns_empty_list() -> None:
    assert build_metric_windows([]) == []


# ---------------------------------------------------------------------------
# Single TelemetryPoint
# ---------------------------------------------------------------------------

def test_single_point_produces_eight_windows() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS)])
    assert len(windows) == 8


def test_single_point_all_windows_have_one_observation() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS)])
    for window in windows:
        assert len(window.values) == 1
        assert len(window.timestamps) == 1


def test_single_point_component_id_propagated() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS)])
    assert all(w.component_id == "db-01" for w in windows)


# ---------------------------------------------------------------------------
# Multiple components — separation and count
# ---------------------------------------------------------------------------

def test_two_components_produce_sixteen_windows() -> None:
    points = [
        _make_point("comp-01", _BASE_TS),
        _make_point("comp-02", _BASE_TS),
    ]
    windows = build_metric_windows(points)
    assert len(windows) == 16


def test_components_are_separated() -> None:
    points = [
        _make_point("comp-01", _BASE_TS, latency_ms=11.0),
        _make_point("comp-02", _BASE_TS, latency_ms=99.0),
    ]
    windows = build_metric_windows(points)
    lat_01 = next(w for w in windows if w.component_id == "comp-01" and w.metric == "latency_ms")
    lat_02 = next(w for w in windows if w.component_id == "comp-02" and w.metric == "latency_ms")
    assert lat_01.values[0] == pytest.approx(11.0)
    assert lat_02.values[0] == pytest.approx(99.0)


# ---------------------------------------------------------------------------
# Metric fields — names and completeness
# ---------------------------------------------------------------------------

def test_all_eight_metric_fields_present() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS)])
    metric_names = {w.metric for w in windows}
    assert metric_names == set(METRIC_FIELDS)


def test_metric_field_names_match_telemetry_point_contract() -> None:
    model_field_names = set(TelemetryPoint.model_fields.keys())
    for field in METRIC_FIELDS:
        assert field in model_field_names, f"{field!r} not in TelemetryPoint.model_fields"


def test_metric_fields_excludes_component_id_and_window_start() -> None:
    assert "component_id" not in METRIC_FIELDS
    assert "window_start" not in METRIC_FIELDS


def test_metric_field_count_is_eight() -> None:
    assert len(METRIC_FIELDS) == 8


# ---------------------------------------------------------------------------
# Timestamp ordering — sort even when input is shuffled
# ---------------------------------------------------------------------------

def test_timestamps_sorted_ascending_when_input_is_shuffled() -> None:
    # Provide two points in reverse chronological order
    point_later = _make_point("db-01", _NEXT_TS)
    point_earlier = _make_point("db-01", _BASE_TS)
    windows = build_metric_windows([point_later, point_earlier])
    for window in windows:
        assert window.timestamps[0] == _BASE_TS
        assert window.timestamps[1] == _NEXT_TS


def test_values_aligned_with_sorted_timestamps_after_shuffle() -> None:
    # later point has latency 99.0; earlier point has latency 11.0
    point_later = _make_point("db-01", _NEXT_TS, latency_ms=99.0)
    point_earlier = _make_point("db-01", _BASE_TS, latency_ms=11.0)
    windows = build_metric_windows([point_later, point_earlier])
    lat = next(w for w in windows if w.metric == "latency_ms")
    # after sorting: _BASE_TS first → latency 11.0; _NEXT_TS second → 99.0
    assert lat.values[0] == pytest.approx(11.0)
    assert lat.values[1] == pytest.approx(99.0)


def test_three_points_shuffled_timestamps_are_strictly_ascending() -> None:
    ts_a = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    ts_b = datetime(2026, 1, 1, 0, 0, 30, tzinfo=timezone.utc)
    ts_c = datetime(2026, 1, 1, 0, 1, 0, tzinfo=timezone.utc)
    points = [
        _make_point("a-01", ts_c),
        _make_point("a-01", ts_a),
        _make_point("a-01", ts_b),
    ]
    for window in build_metric_windows(points):
        ts_list = list(window.timestamps)
        assert ts_list == sorted(ts_list)


# ---------------------------------------------------------------------------
# Array properties
# ---------------------------------------------------------------------------

def test_values_is_one_dimensional_numpy_array() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS)])
    for window in windows:
        assert isinstance(window.values, np.ndarray)
        assert window.values.ndim == 1


def test_values_are_finite() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS)])
    for window in windows:
        assert np.all(np.isfinite(window.values))


def test_values_length_matches_timestamps_length() -> None:
    points = [_make_point("db-01", _BASE_TS), _make_point("db-01", _NEXT_TS)]
    for window in build_metric_windows(points):
        assert len(window.values) == len(window.timestamps)


def test_connection_count_stored_as_float() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS, connection_count=42)])
    cc = next(w for w in windows if w.metric == "connection_count")
    assert cc.values.dtype == np.float64
    assert cc.values[0] == pytest.approx(42.0)


# ---------------------------------------------------------------------------
# MetricWindow is a frozen dataclass
# ---------------------------------------------------------------------------

def test_metric_window_is_frozen() -> None:
    windows = build_metric_windows([_make_point("db-01", _BASE_TS)])
    window = windows[0]
    with pytest.raises((AttributeError, TypeError)):
        window.component_id = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Duplicate timestamp — must raise clearly
# ---------------------------------------------------------------------------

def test_duplicate_timestamp_same_component_raises_value_error() -> None:
    point_a = _make_point("db-01", _BASE_TS, latency_ms=10.0)
    point_b = _make_point("db-01", _BASE_TS, latency_ms=99.0)
    with pytest.raises(ValueError, match="duplicate window_start"):
        build_metric_windows([point_a, point_b])


def test_duplicate_timestamp_different_components_does_not_raise() -> None:
    point_a = _make_point("comp-01", _BASE_TS)
    point_b = _make_point("comp-02", _BASE_TS)
    windows = build_metric_windows([point_a, point_b])
    assert len(windows) == 16


# ---------------------------------------------------------------------------
# Fixture-based tests — grounded in verified counts and patterns
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def fixture_telemetry() -> list[TelemetryPoint]:
    return load_telemetry_csv(FIXTURES / "telemetry.csv")


@pytest.fixture(scope="module")
def fixture_windows(fixture_telemetry: list[TelemetryPoint]) -> list[MetricWindow]:
    return build_metric_windows(fixture_telemetry)


def test_fixture_produces_240_windows(fixture_windows: list[MetricWindow]) -> None:
    # 30 components × 8 metrics = 240
    assert len(fixture_windows) == 240


def test_fixture_each_window_has_31_observations(fixture_windows: list[MetricWindow]) -> None:
    for window in fixture_windows:
        assert len(window.values) == 31
        assert len(window.timestamps) == 31


def test_fixture_db01_connection_count_has_31_values(fixture_windows: list[MetricWindow]) -> None:
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    assert len(db01_cc.values) == 31


def test_fixture_db01_connection_count_saturates_at_150(fixture_windows: list[MetricWindow]) -> None:
    # Verified from fixture: values[13:] are all 150 (post-fault ceiling)
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    assert np.all(db01_cc.values[13:] == 150.0)


def test_fixture_db01_prefault_connection_count_below_150(fixture_windows: list[MetricWindow]) -> None:
    # First 13 observations are pre-fault (varying, all below the ceiling)
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    assert np.all(db01_cc.values[:13] < 150.0)


def test_fixture_all_window_values_finite(fixture_windows: list[MetricWindow]) -> None:
    for window in fixture_windows:
        assert np.all(np.isfinite(window.values))


def test_fixture_all_metric_field_names_appear(fixture_windows: list[MetricWindow]) -> None:
    observed_metrics = {w.metric for w in fixture_windows}
    assert observed_metrics == set(METRIC_FIELDS)


def test_fixture_all_component_ids_appear(fixture_windows: list[MetricWindow]) -> None:
    # 30 components confirmed from fixture
    observed_components = {w.component_id for w in fixture_windows}
    assert len(observed_components) == 30


# ---------------------------------------------------------------------------
# Integration — window.values directly consumable by compute_mad_scores
# ---------------------------------------------------------------------------

def test_window_values_accepted_by_compute_mad_scores(fixture_windows: list[MetricWindow]) -> None:
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = compute_mad_scores(db01_cc.values)
    assert result.median > 0.0
    assert np.all(np.isfinite(result.scores))


def test_all_fixture_windows_accepted_by_compute_mad_scores(fixture_windows: list[MetricWindow]) -> None:
    for window in fixture_windows:
        result = compute_mad_scores(window.values)
        assert np.all(np.isfinite(result.scores))
