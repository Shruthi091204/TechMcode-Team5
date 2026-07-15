from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import median_abs_deviation


@dataclass(frozen=True)
class MadBaseline:
    """Robust baseline statistics for one (component, metric) time series.

    Attributes:
        median: centre of the signal in original units.
                Maps directly to Anomaly.baseline_value.
        mad:    Median Absolute Deviation computed with scale=1.0 (raw MAD
                units, not sigma-normalised). Zero when all observations
                cluster at the median.
        scores: per-observation non-negative deviation scores, shape (n,).
                Maps directly to Anomaly.severity_score.
                When mad > 0: scores are in MAD units (|x - median| / MAD).
                When mad == 0: no MAD-unit scale exists; scores fall back to
                raw absolute deviation from the median (|x - median|) in the
                original metric's units. All values are guaranteed finite.
    """

    median: float
    mad: float
    scores: np.ndarray


def compute_mad_scores(signal: Sequence[float] | np.ndarray) -> MadBaseline:
    """Compute a robust MAD baseline and per-observation anomaly scores.

    Network traffic distributions are heavy-tailed, making mean and standard
    deviation unreliable estimators. The Median Absolute Deviation (MAD) is
    the robust alternative: it summarises dispersion around the median and is
    resistant to outliers by construction.

    Score formula (when MAD > 0):
        score[i] = |x[i] - median(x)| / MAD(x)

    The absolute value preserves anomaly magnitude for both high-side
    (e.g. latency spike) and low-side (e.g. throughput collapse) deviations,
    and satisfies the NonNegative constraint of Anomaly.severity_score.

    Zero-MAD policy:
        When MAD = 0, no within-series scale exists (≥50 % of the signal lies
        exactly at the median). Dividing by MAD would produce inf or nan, both
        of which break downstream numerical change-point detection (ruptures
        PELT cost matrix produces nan via inf − inf) and RFC 8259 JSON
        serialisation (Infinity is not valid JSON).

        Instead, scores fall back to the raw absolute deviation from the
        median: score[i] = |x[i] − median|. This is finite, unambiguous, and
        feeds directly into PELT without corruption. The unit difference (raw
        metric units rather than MAD units) applies only in this degenerate
        case and is documented in MadBaseline.scores.

    Scale choice:
        scale=1.0 (scipy default) returns raw MAD units, consistent with
        Anomaly.severity_score description: "Deviation from baseline in
        median-absolute-deviation units." The scale='normal' variant (×1.4826)
        would produce sigma-equivalent units, which is explicitly not what the
        contract specifies.

    Args:
        signal: one-dimensional sequence of finite numeric observations,
                representing one (component, metric) time series.

    Returns:
        MadBaseline with median, mad, and per-observation scores.

    Raises:
        ValueError: if signal is empty, not one-dimensional, or contains
                    NaN or infinite values.
    """
    values = np.asarray(signal, dtype=float)

    if values.ndim != 1:
        raise ValueError(
            f"signal must be one-dimensional, got shape {values.shape}"
        )
    if values.size == 0:
        raise ValueError("signal must contain at least one observation")
    if not np.isfinite(values).all():
        raise ValueError(
            "signal must not contain NaN or infinite values; "
            "clean the input before computing the baseline"
        )

    centre = float(np.median(values))
    mad = float(median_abs_deviation(values, scale=1.0))

    per_observation_scores = np.abs(values - centre) if mad == 0.0 else np.abs(values - centre) / mad

    return MadBaseline(median=centre, mad=mad, scores=per_observation_scores)
