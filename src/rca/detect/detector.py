from __future__ import annotations

import math

import numpy as np

from contracts.schemas import Anomaly
from src.rca.detect.baseline import compute_mad_scores
from src.rca.detect.changepoint import find_changepoint
from src.rca.detect.window import MetricWindow


def detect_anomalies(
    windows: list[MetricWindow],
    min_severity: float = 0.0,
) -> list[Anomaly]:
    """Orchestrate P2 detection: MetricWindow list → Anomaly list.

    For each MetricWindow this function:
      1. Runs PELT change-point detection via find_changepoint.
      2. Splits the signal at the detected onset into a pre-onset (normal)
         segment and a post-onset (fault) segment.
      3. Derives the MAD baseline exclusively from the pre-onset segment —
         never from the full signal — so that a post-fault plateau cannot
         contaminate or invert the baseline estimate.
      4. Computes severity as the deviation of the post-onset mean from the
         pre-onset median, expressed in MAD units (or raw units when MAD is
         zero, consistent with baseline.py's zero-MAD policy).
      5. Constructs a frozen Anomaly contract object when severity is at or
         above the min_severity threshold.

    Why pre-onset baseline:
        When a step-change fault dominates the second half of a window the
        full-signal median may land inside the fault plateau.  For the
        fixture db-01/connection_count this makes the full-signal MAD zero
        and the whole-signal median equal to the fault level — completely
        inverting which values look anomalous.  Using only the pre-onset
        segment avoids this contamination.

    Severity formula (when pre-onset MAD > 0):
        severity = |post_mean - pre_median| / pre_MAD

    Zero-MAD fallback (pre-onset MAD == 0):
        severity = |post_mean - pre_median|
        (raw metric units, consistent with MadBaseline zero-MAD policy)

    Ordering:
        Output Anomaly objects appear in the same order as the input windows
        that produced them.  Windows with no change-point or insufficient
        pre-onset data are silently skipped.

    Args:
        windows:      Ordered list of MetricWindow objects, typically the
                      direct output of build_metric_windows.
        min_severity: Non-negative finite lower bound.  Windows whose
                      severity is strictly below this value are suppressed.
                      The default (0.0) emits every detected change-point.
                      Equality is retained: severity == min_severity passes.

    Returns:
        list[Anomaly] — one entry per window that produced a statistically
        significant change-point with severity >= min_severity.

    Raises:
        ValueError: if min_severity is negative, NaN, or infinite.
    """
    if not math.isfinite(min_severity) or min_severity < 0.0:
        raise ValueError(
            f"min_severity must be a finite non-negative float, got {min_severity!r}"
        )

    anomalies: list[Anomaly] = []

    for window in windows:
        cp = find_changepoint(window)

        if cp.onset_ts is None or cp.breakpoint_index is None:
            continue

        bp = cp.breakpoint_index

        pre = window.values[:bp]
        post = window.values[bp:]

        if pre.size == 0 or post.size == 0:
            continue

        bl = compute_mad_scores(pre)

        observed_value = float(np.mean(post))

        if bl.mad > 0.0:
            severity = abs(observed_value - bl.median) / bl.mad
        else:
            severity = abs(observed_value - bl.median)

        if severity < min_severity:
            continue

        anomalies.append(
            Anomaly(
                component_id=window.component_id,
                metric=window.metric,
                onset_ts=cp.onset_ts,
                severity_score=severity,
                window_start=window.timestamps[0],
                window_end=window.timestamps[-1],
                baseline_value=bl.median,
                observed_value=observed_value,
            )
        )

    return anomalies
