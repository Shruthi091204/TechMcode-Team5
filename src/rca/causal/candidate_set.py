from __future__ import annotations

from datetime import datetime

from contracts.schemas import AlertRecord, Anomaly, ConfigChange
from rca.graph.twin import TopologyTwin

DECOY_PROXIMITY_SECONDS = 900.0


def anomalous_components(anomalies: list[Anomaly]) -> list[str]:
    return sorted({anomaly.component_id for anomaly in anomalies})


def candidate_causes(twin: TopologyTwin, symptom_id: str, anomalies: list[Anomaly]) -> list[str]:
    return [
        component_id
        for component_id in anomalous_components(anomalies)
        if component_id != symptom_id and twin.has_path(component_id, symptom_id)
    ]


def _has_recent_trigger(
    component_id: str,
    onset: datetime,
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
) -> bool:
    for change in changes:
        if change.component_id != component_id:
            continue
        gap = (onset - change.ts).total_seconds()
        if 0.0 <= gap <= DECOY_PROXIMITY_SECONDS:
            return True
    for alert in alerts:
        if alert.component_id != component_id:
            continue
        gap = (onset - alert.ts).total_seconds()
        if 0.0 <= gap <= DECOY_PROXIMITY_SECONDS:
            return True
    return False


def decoy_components(
    twin: TopologyTwin,
    symptom_id: str,
    anomalies: list[Anomaly],
    onset: datetime,
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
) -> list[str]:
    disconnected = [
        component_id
        for component_id in anomalous_components(anomalies)
        if component_id != symptom_id and not twin.has_path(component_id, symptom_id)
    ]
    return [
        component_id
        for component_id in disconnected
        if _has_recent_trigger(component_id, onset, changes, alerts)
    ]
