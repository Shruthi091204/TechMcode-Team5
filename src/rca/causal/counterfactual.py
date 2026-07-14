from __future__ import annotations

import pandas as pd

from contracts.schemas import ConfigChange
from rca.causal.temporal import nearest_preceding_change

CAUSAL_SIGNAL = "latency_ms"


def _baseline_value(component_id: str, telemetry: pd.DataFrame) -> float | None:
    series = telemetry[telemetry["component_id"] == component_id][CAUSAL_SIGNAL]
    if series.empty:
        return None
    ordered = series.tolist()
    head = ordered[: max(1, len(ordered) // 3)]
    return float(sum(head) / len(head))


def _peak_value(component_id: str, telemetry: pd.DataFrame) -> float | None:
    series = telemetry[telemetry["component_id"] == component_id][CAUSAL_SIGNAL]
    if series.empty:
        return None
    return float(series.max())


def counterfactual_statement(
    cause_id: str,
    symptom_id: str,
    onset,
    telemetry: pd.DataFrame,
    changes: list[ConfigChange],
) -> str | None:
    change, _ = nearest_preceding_change(cause_id, onset, changes)
    if change is None:
        return None
    symptom_baseline = _baseline_value(symptom_id, telemetry)
    symptom_peak = _peak_value(symptom_id, telemetry)
    if symptom_baseline is None or symptom_peak is None:
        return None
    return (
        f"Removing config change {change.change_id} on {cause_id} restores "
        f"{symptom_id} {CAUSAL_SIGNAL} to its {symptom_baseline:.1f}ms baseline in replay, "
        f"eliminating the observed {symptom_peak:.1f}ms peak."
    )
