from __future__ import annotations

from datetime import datetime

from contracts.schemas import AlertRecord, ConfigChange

PRECEDENCE_HALF_LIFE_SECONDS = 120.0
PROXIMITY_WINDOW_SECONDS = 300.0


def precedence_score(cause_onset: datetime, symptom_onset: datetime) -> float:
    lead_seconds = (symptom_onset - cause_onset).total_seconds()
    if lead_seconds < 0.0:
        return 0.0
    if lead_seconds == 0.0:
        return 0.5
    return min(1.0, lead_seconds / (lead_seconds + PRECEDENCE_HALF_LIFE_SECONDS) * 2.0)


def nearest_preceding_change(
    component_id: str,
    onset: datetime,
    changes: list[ConfigChange],
) -> tuple[ConfigChange | None, float]:
    best_change: ConfigChange | None = None
    best_gap = float("inf")
    for change in changes:
        if change.component_id != component_id:
            continue
        gap = (onset - change.ts).total_seconds()
        if gap < 0.0 or gap >= best_gap:
            continue
        best_change = change
        best_gap = gap
    if best_change is None:
        return None, 0.0
    proximity = max(0.0, 1.0 - best_gap / (PROXIMITY_WINDOW_SECONDS * 2.0))
    return best_change, proximity


def nearest_preceding_alert(
    component_id: str,
    onset: datetime,
    alerts: list[AlertRecord],
) -> AlertRecord | None:
    best_alert: AlertRecord | None = None
    best_gap = float("inf")
    for alert in alerts:
        if alert.component_id != component_id:
            continue
        gap = (onset - alert.ts).total_seconds()
        if gap < 0.0 or gap >= best_gap:
            continue
        best_alert = alert
        best_gap = gap
    return best_alert
