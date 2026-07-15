from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

import numpy as np

from contracts.schemas import TelemetryPoint

METRIC_FIELDS: tuple[str, ...] = (
    "latency_ms",
    "jitter_ms",
    "packet_loss_pct",
    "throughput_mbps",
    "error_rate",
    "connection_count",
    "cpu_pct",
    "mem_pct",
)
"""The eight numeric TelemetryPoint fields that become anomaly-detection signals.

Hardcoded (not derived dynamically) so that any future additive field added
to TelemetryPoint (e.g. a non-numeric annotation) cannot silently enter the
detection pipeline. Must stay in sync with the frozen TelemetryPoint contract.
Each name maps directly to Anomaly.metric in the downstream pipeline.
"""


@dataclass(frozen=True)
class MetricWindow:
    """Ordered time series for one (component_id, metric) pair.

    This is an internal P2 structural type — it is NOT a frozen contract.
    It is produced by build_metric_windows and consumed by:
      - detect/baseline.py   (compute_mad_scores receives .values)
      - detect/changepoint.py (ruptures.Pelt receives .values, .timestamps maps
                               breakpoint indices back to onset_ts)
      - detect/detector.py   (constructs Anomaly objects from all three)

    Attributes:
        component_id: identifies the network device; maps to Anomaly.component_id.
        metric:       one of METRIC_FIELDS; maps directly to Anomaly.metric.
        timestamps:   timezone-aware datetimes, strictly ascending, length n.
        values:       one-dimensional float64 array, length n, all finite.
                      Directly consumable by compute_mad_scores and ruptures.Pelt.
    """

    component_id: str
    metric: str
    timestamps: tuple[datetime, ...]
    values: np.ndarray


def build_metric_windows(telemetry: list[TelemetryPoint]) -> list[MetricWindow]:
    """Organise a flat list of TelemetryPoints into per-(component, metric) signals.

    Each returned MetricWindow contains the complete time-ordered series of one
    metric for one component. The complete signal is preserved so that downstream
    detection and orchestration can apply the required multi-scale analysis
    (IMPLEMENTATION.md: 30s / 5m / 15m). Where that multi-scale logic lives and
    whether it means history-length slicing or physical resampling is not specified
    by the repository contracts and is left to the consuming modules to decide.

    Input order is not assumed to be sorted. Observations are sorted by
    window_start within each component group before building the arrays.

    Args:
        telemetry: flat list of validated TelemetryPoint objects from any source
                   (csv_adapter, parquet_adapter, arff_adapter, or flow_to_kpi).
                   May be empty, in which case an empty list is returned.

    Returns:
        One MetricWindow per (component_id, metric) combination, sorted
        lexicographically by component_id then by METRIC_FIELDS order.

    Raises:
        ValueError: if any (component_id, window_start) pair appears more than
                    once in the input. Duplicate timestamps within a component
                    are ambiguous — no aggregation policy is defined by the
                    repository contracts.
    """
    if not telemetry:
        return []

    grouped: dict[str, list[TelemetryPoint]] = defaultdict(list)
    for point in telemetry:
        grouped[point.component_id].append(point)

    windows: list[MetricWindow] = []

    for component_id, points in sorted(grouped.items()):
        sorted_points = sorted(points, key=lambda p: p.window_start)

        timestamps = tuple(p.window_start for p in sorted_points)
        seen_timestamps: set[datetime] = set()
        for ts in timestamps:
            if ts in seen_timestamps:
                raise ValueError(
                    f"duplicate window_start {ts.isoformat()!r} for component "
                    f"{component_id!r}; each (component_id, window_start) pair "
                    "must be unique — no aggregation policy is defined"
                )
            seen_timestamps.add(ts)

        for metric in METRIC_FIELDS:
            values = np.array(
                [float(getattr(point, metric)) for point in sorted_points],
                dtype=float,
            )
            windows.append(
                MetricWindow(
                    component_id=component_id,
                    metric=metric,
                    timestamps=timestamps,
                    values=values,
                )
            )

    return windows
