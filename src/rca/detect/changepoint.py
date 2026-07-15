from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
import ruptures as rpt

from src.rca.detect.window import MetricWindow


@dataclass(frozen=True)
class ChangepointResult:
    """Outcome of PELT change-point detection for one (component, metric) window.

    This is an internal P2 structural type — it is NOT a frozen contract.
    It is produced by find_changepoint and consumed by detect/detector.py,
    which combines it with MadBaseline to construct Anomaly objects.

    Attributes:
        onset_ts:         The timestamp of the first observation in the new
                          regime — i.e. the earliest detected onset. None when
                          no statistically significant change-point is found.
                          Timezone-aware; maps directly to Anomaly.onset_ts.
        breakpoint_index: The 0-based index into MetricWindow.timestamps that
                          produced onset_ts. None when onset_ts is None.
                          detector.py may use this to slice the post-onset
                          segment when computing Anomaly.observed_value.
    """

    onset_ts: datetime | None
    breakpoint_index: int | None


def find_changepoint(
    window: MetricWindow,
    penalty: float | None = None,
    model: str = "rbf",
    min_size: int = 2,
) -> ChangepointResult:
    """Detect the earliest structural change-point in a MetricWindow signal.

    Uses ruptures PELT (Pruned Exact Linear Time) to find the optimal
    segmentation of the time series. PELT is an exact algorithm: it guarantees
    the globally optimal set of change-points under the chosen cost model and
    penalty.

    Why PELT over a threshold:
        A threshold crossing tells you *that* a metric is anomalous; a
        change-point tells you *when the generating distribution changed*.
        Onset time is required for causal inference (Layer 3) because
        causation demands temporal precedence.

    Why rbf cost model:
        The radial-basis-function kernel is non-parametric — it makes no
        distributional assumption. Network traffic is heavy-tailed and
        non-Gaussian, so parametric models (Normal, AR) give a poor fit.
        rbf detects changes in both mean and variance.

    Normalisation:
        Values are z-score normalised (subtract mean, divide by std) before
        PELT. This makes the penalty scale-invariant across all eight metric
        types: connection_count lives in the hundreds while error_rate lives
        near zero. Without normalisation, a fixed penalty would need per-metric
        tuning. The normalisation is applied to the PELT input only; it does
        not affect window.values or any downstream module.

    Penalty default (length-aware heuristic):
        When penalty is None, the effective penalty is log(n), where n is the
        number of observations in the supplied MetricWindow. This is a standard
        heuristic from the change-point literature (analogous to the Bayesian
        Information Criterion penalty) that adapts to the analysis window length.
        For the 15-minute fixture (n=31) it evaluates to ≈3.43; for a 5-minute
        slice (n=10) it evaluates to ≈2.30.

        This heuristic does NOT guarantee that every change-point will be
        detected. Detection depends on the signal-to-noise ratio, the cost
        model, and the magnitude of the regime shift. Callers may supply an
        explicit penalty to override this default for specific analysis scales
        or signal types.

    Precision and resolution:
        Detected onset timestamps are constrained to the observed sampling grid
        — with 30-second TelemetryPoint cadence, onset_ts can only be one of
        the n observed timestamps. No sub-interval precision is possible
        regardless of algorithm or penalty. The actual detection error within
        this grid depends on the signal characteristics, cost model, and penalty;
        it is not bounded to any fixed number of samples.

    Multiple breakpoints:
        PELT may return more than one change-point. Only the first (earliest)
        is returned as onset_ts. Later breakpoints represent recovery or
        secondary shifts and are detector.py's concern.

    Multi-scale windows (30s / 5m / 15m):
        find_changepoint operates on whatever signal the caller supplies.
        Slicing the MetricWindow to implement multi-scale analysis is the
        caller's responsibility (detector.py), not this module's. Passing
        shorter slices automatically adjusts the log(n) default penalty.

    Args:
        window:    MetricWindow containing ordered timestamps and finite values.
        penalty:   PELT penalty term. Higher values suppress false positives at
                   the cost of missing weaker changes. When None (the default),
                   log(n) is used as a length-aware heuristic. Callers may
                   pass an explicit float to override this for a specific scale.
        model:     ruptures cost model. "rbf" is recommended for non-Gaussian
                   network metrics. "l2" is faster but more prone to over-
                   segmentation at the same penalty.
        min_size:  Minimum number of observations in any segment. Must be ≥ 1.

    Returns:
        ChangepointResult with the onset timestamp and its index, or
        ChangepointResult(None, None) when no change-point is found.

    Raises:
        Nothing — all degenerate inputs (n < 2, flat signal) are handled
        gracefully by returning None onset.
    """
    n = len(window.values)

    if n < 2:
        return ChangepointResult(onset_ts=None, breakpoint_index=None)

    std = float(np.std(window.values, ddof=0))
    if std == 0.0:
        return ChangepointResult(onset_ts=None, breakpoint_index=None)

    effective_penalty = float(penalty) if penalty is not None else float(np.log(n))

    normalized = (window.values - np.mean(window.values)) / std

    detector = rpt.Pelt(model=model, min_size=min_size).fit(normalized)
    breakpoints = detector.predict(pen=effective_penalty)

    if breakpoints == [n]:
        return ChangepointResult(onset_ts=None, breakpoint_index=None)

    onset_index = breakpoints[0]
    return ChangepointResult(
        onset_ts=window.timestamps[onset_index],
        breakpoint_index=onset_index,
    )
