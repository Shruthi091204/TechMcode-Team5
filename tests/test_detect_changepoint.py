from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest

from src.rca.detect.baseline import compute_mad_scores
from src.rca.detect.changepoint import ChangepointResult, find_changepoint
from src.rca.detect.window import MetricWindow, build_metric_windows
from src.rca.ingest.csv_adapter import load_telemetry_csv

FIXTURES = Path(__file__).resolve().parents[1] / "contracts" / "fixtures"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UTC = UTC


def _make_window(
    values: list[float],
    component_id: str = "test-01",
    metric: str = "latency_ms",
    base_ts: datetime | None = None,
    step_seconds: int = 30,
) -> MetricWindow:
    """Build a MetricWindow from a plain value list."""
    if base_ts is None:
        base_ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=_UTC)
    from datetime import timedelta

    timestamps = tuple(
        base_ts + timedelta(seconds=i * step_seconds) for i in range(len(values))
    )
    return MetricWindow(
        component_id=component_id,
        metric=metric,
        timestamps=timestamps,
        values=np.array(values, dtype=float),
    )


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------


def test_returns_changepoint_result_instance() -> None:
    window = _make_window([1.0, 2.0, 3.0, 4.0, 5.0])
    result = find_changepoint(window)
    assert isinstance(result, ChangepointResult)


def test_changepoint_result_is_frozen() -> None:
    result = ChangepointResult(onset_ts=None, breakpoint_index=None)
    with pytest.raises((AttributeError, TypeError)):
        result.onset_ts = datetime(2026, 1, 1, tzinfo=_UTC)  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Minimum-length guard — no crash, graceful None
# ---------------------------------------------------------------------------


def test_single_observation_returns_none_no_crash() -> None:
    window = _make_window([42.0])
    result = find_changepoint(window)
    assert result.onset_ts is None
    assert result.breakpoint_index is None


def test_zero_observations_not_possible_but_guard_works() -> None:
    # MetricWindow with empty values is prevented by build_metric_windows,
    # but the guard should still be safe if called directly.
    datetime(2026, 1, 1, tzinfo=_UTC)
    window = MetricWindow(
        component_id="x-01",
        metric="latency_ms",
        timestamps=(),
        values=np.array([], dtype=float),
    )
    result = find_changepoint(window)
    assert result.onset_ts is None
    assert result.breakpoint_index is None


def test_two_observations_returns_no_crash() -> None:
    window = _make_window([1.0, 10.0])
    result = find_changepoint(window)
    assert isinstance(result, ChangepointResult)


# ---------------------------------------------------------------------------
# Flat signal — no change possible
# ---------------------------------------------------------------------------


def test_flat_signal_returns_none_onset() -> None:
    window = _make_window([5.0] * 20)
    result = find_changepoint(window)
    assert result.onset_ts is None
    assert result.breakpoint_index is None


def test_flat_signal_single_value_repeated() -> None:
    window = _make_window([100.0] * 31)
    result = find_changepoint(window)
    assert result.onset_ts is None


# ---------------------------------------------------------------------------
# Clear step change — correct detection
# ---------------------------------------------------------------------------


def test_clear_step_change_detects_onset() -> None:
    # 10 observations: first 5 at 0.0, next 5 at 10.0
    window = _make_window([0.0] * 5 + [10.0] * 5)
    result = find_changepoint(window)
    assert result.onset_ts is not None
    assert result.breakpoint_index is not None


def test_clear_step_onset_index_is_in_valid_range() -> None:
    window = _make_window([0.0] * 5 + [10.0] * 5)
    result = find_changepoint(window)
    if result.breakpoint_index is not None:
        assert 0 <= result.breakpoint_index < len(window.values)


def test_clear_step_onset_is_in_second_half() -> None:
    # change-point at index 5: the onset should be at or near index 5
    window = _make_window([0.0] * 5 + [10.0] * 5)
    result = find_changepoint(window)
    if result.breakpoint_index is not None:
        assert result.breakpoint_index >= 4


def test_clear_low_side_step_detects_onset() -> None:
    # Signal drops from 10.0 to 0.0 — low-side change-point.
    # Verified: n=10+10=20 at default penalty=3.0 reliably detects the step;
    # n=8+8=16 does not (cost savings < penalty for this short a signal).
    window = _make_window([10.0] * 10 + [0.0] * 10)
    result = find_changepoint(window)
    assert result.onset_ts is not None


# ---------------------------------------------------------------------------
# Timestamp correctness
# ---------------------------------------------------------------------------


def test_onset_ts_is_timezone_aware() -> None:
    window = _make_window([0.0] * 5 + [10.0] * 5)
    result = find_changepoint(window)
    if result.onset_ts is not None:
        assert result.onset_ts.tzinfo is not None


def test_onset_ts_matches_window_timestamp_at_breakpoint_index() -> None:
    window = _make_window([0.0] * 5 + [10.0] * 5)
    result = find_changepoint(window)
    if result.onset_ts is not None and result.breakpoint_index is not None:
        assert result.onset_ts == window.timestamps[result.breakpoint_index]


def test_onset_ts_within_window_bounds() -> None:
    # Anomaly contract: window_start <= onset_ts <= window_end
    window = _make_window([0.0] * 5 + [10.0] * 5)
    result = find_changepoint(window)
    if result.onset_ts is not None:
        assert window.timestamps[0] <= result.onset_ts <= window.timestamps[-1]


# ---------------------------------------------------------------------------
# Penalty sensitivity — explicit override and default length-aware heuristic
# ---------------------------------------------------------------------------


def test_explicit_penalty_overrides_default() -> None:
    # For n=16, log(16)≈2.77 (default) detects the step; explicit 3.0 does not.
    # This test verifies two things simultaneously:
    #   1. An explicit penalty value bypasses the log(n) default (override works).
    #   2. The default heuristic is more sensitive on short signals than 3.0.
    # Verified by live PELT run with rbf model on [0]*8+[10]*8 (n=16).
    window = _make_window([0.0] * 8 + [10.0] * 8)
    result_explicit = find_changepoint(window, penalty=3.0)
    result_default = find_changepoint(window)
    assert result_explicit.onset_ts is None, (
        "explicit penalty=3.0 should suppress the change-point for n=16 "
        "(penalty exceeds the rbf cost savings at this signal length)"
    )
    assert result_default.onset_ts is not None, (
        "default log(n=16)≈2.77 should detect the step that penalty=3.0 misses"
    )


def test_high_penalty_may_suppress_weak_signal() -> None:
    # Small-amplitude change; very high penalty should suppress it
    window = _make_window([1.0, 1.1, 1.0, 1.1, 1.0, 2.0, 2.1, 2.0, 2.1, 2.0])
    result_high = find_changepoint(window, penalty=50.0)
    # At penalty=50 even a real shift may be suppressed — just verify no crash
    assert isinstance(result_high, ChangepointResult)


def test_low_penalty_detects_step_change() -> None:
    window = _make_window([0.0] * 10 + [5.0] * 10)
    result = find_changepoint(window, penalty=1.0)
    assert result.onset_ts is not None


# ---------------------------------------------------------------------------
# model and min_size parameters
# ---------------------------------------------------------------------------


def test_l2_model_also_works() -> None:
    window = _make_window([0.0] * 8 + [10.0] * 8)
    result = find_changepoint(window, model="l2")
    assert isinstance(result, ChangepointResult)


def test_custom_min_size_is_accepted() -> None:
    window = _make_window([0.0] * 10 + [10.0] * 10)
    result = find_changepoint(window, min_size=3)
    assert isinstance(result, ChangepointResult)


# ---------------------------------------------------------------------------
# None consistency
# ---------------------------------------------------------------------------


def test_none_onset_means_none_index() -> None:
    window = _make_window([5.0] * 20)
    result = find_changepoint(window)
    assert result.onset_ts is None
    assert result.breakpoint_index is None


def test_nonnone_onset_means_nonnone_index() -> None:
    window = _make_window([0.0] * 8 + [10.0] * 8)
    result = find_changepoint(window)
    if result.onset_ts is not None:
        assert result.breakpoint_index is not None
    if result.breakpoint_index is not None:
        assert result.onset_ts is not None


# ---------------------------------------------------------------------------
# Fixture-based tests — verified from live PELT runs
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fixture_telemetry():
    return load_telemetry_csv(FIXTURES / "telemetry.csv")


@pytest.fixture(scope="module")
def fixture_windows(fixture_telemetry):
    return build_metric_windows(fixture_telemetry)


def test_fixture_db01_connection_count_onset_is_detected(fixture_windows) -> None:
    # db-01/connection_count has a clear saturation at 150 after index ~13.
    # Verified by live PELT run: onset detected at index 15 (14:32:30Z) with
    # both explicit penalty=3.0 and the default log(n=31)≈3.43 — identical result.
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = find_changepoint(db01_cc)
    assert result.onset_ts is not None, "expected a change-point in db-01/connection_count"
    assert result.breakpoint_index is not None


def test_fixture_db01_connection_count_onset_near_ground_truth(fixture_windows) -> None:
    # Ground truth onset_at = 2026-07-14T14:32:00Z (index 14)
    # PELT at penalty=3 detects index 15 (14:32:30Z) — within 1 position (30s)
    # Allow ±2 positions (±60s) to tolerate cost-model rounding
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = find_changepoint(db01_cc)
    if result.breakpoint_index is not None:
        assert abs(result.breakpoint_index - 14) <= 2, (
            f"onset index {result.breakpoint_index} is more than 2 positions from "
            f"ground-truth index 14 (onset_at=14:32:00Z)"
        )


def test_fixture_db01_connection_count_onset_ts_is_aware(fixture_windows) -> None:
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    result = find_changepoint(db01_cc)
    if result.onset_ts is not None:
        assert result.onset_ts.tzinfo is not None


def test_fixture_db01_latency_ms_onset_detected(fixture_windows) -> None:
    # db-01/latency_ms spikes from ~5ms to ~170ms during the fault — a real change-point
    # Verified by live run: onset at index 15 (14:32:30Z)
    db01_lat = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "latency_ms"
    )
    result = find_changepoint(db01_lat)
    assert result.onset_ts is not None, "expected a change-point in db-01/latency_ms"


def test_fixture_quiet_component_connection_count_no_change(fixture_windows) -> None:
    # tor-sw-01/connection_count shows normal noise (no fault involvement)
    # Verified by live run: PELT returns [31] (no change-point) at penalty=3
    tor_cc = next(
        w for w in fixture_windows
        if w.component_id == "tor-sw-01" and w.metric == "connection_count"
    )
    result = find_changepoint(tor_cc)
    assert result.onset_ts is None, (
        f"tor-sw-01/connection_count should not have a change-point, "
        f"but got onset at {result.onset_ts}"
    )


def test_fixture_onset_ts_within_window_bounds_for_all_windows(fixture_windows) -> None:
    # Anomaly.reject_onset_outside_window: window_start <= onset_ts <= window_end
    for window in fixture_windows:
        result = find_changepoint(window)
        if result.onset_ts is not None:
            assert window.timestamps[0] <= result.onset_ts <= window.timestamps[-1], (
                f"{window.component_id}/{window.metric}: onset_ts {result.onset_ts} "
                f"outside [{window.timestamps[0]}, {window.timestamps[-1]}]"
            )


# ---------------------------------------------------------------------------
# Integration — changepoint and MAD scores are independent and compatible
# ---------------------------------------------------------------------------


def test_find_changepoint_does_not_call_compute_mad_scores(fixture_windows) -> None:
    # Structural: changepoint.py must not import or call baseline.py
    # Verified by module inspection — this test ensures the separation
    import src.rca.detect.changepoint as cp_module
    assert not hasattr(cp_module, "compute_mad_scores")
    assert "baseline" not in dir(cp_module)


def test_find_changepoint_and_compute_mad_scores_are_independent(fixture_windows) -> None:
    # Both can be called on the same window without interference
    db01_cc = next(
        w for w in fixture_windows
        if w.component_id == "db-01" and w.metric == "connection_count"
    )
    cp_result = find_changepoint(db01_cc)
    mad_result = compute_mad_scores(db01_cc.values)
    # Both succeed and neither affects the other's output
    assert cp_result.onset_ts is not None
    assert mad_result.median > 0.0
    assert np.all(np.isfinite(mad_result.scores))
