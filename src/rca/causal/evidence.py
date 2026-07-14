from __future__ import annotations

from datetime import datetime

import pandas as pd

from contracts.schemas import (
    AlertRecord,
    ConfigChange,
    EvidenceItem,
    LogRecord,
)
from rca.causal.temporal import nearest_preceding_alert, nearest_preceding_change
from rca.graph.twin import TopologyTwin

CEILING_SIGNAL = "connection_count"


def _lead_seconds(later: datetime, earlier: datetime) -> float:
    return (later - earlier).total_seconds()


def _confirmed_config(component_id: str, onset: datetime, changes: list[ConfigChange]) -> EvidenceItem | None:
    change, _ = nearest_preceding_change(component_id, onset, changes)
    if change is None:
        return None
    lead = _lead_seconds(onset, change.ts)
    delta = ", ".join(
        f"{key} {change.before.get(key)!r}->{change.after.get(key)!r}"
        for key in change.after
        if change.before.get(key) != change.after.get(key)
    )
    return EvidenceItem(
        kind="confirmed",
        source="config",
        statement=f"Config change {change.change_id} on {component_id} ({delta}) landed {lead:.0f}s before onset",
        ref=change.change_id,
    )


def matched_ceiling(component_id: str, change: ConfigChange, telemetry: pd.DataFrame) -> int | None:
    ceilings = {value for value in change.after.values() if isinstance(value, int)}
    if not ceilings:
        return None
    series = telemetry[telemetry["component_id"] == component_id]
    if CEILING_SIGNAL not in series.columns:
        return None
    tail = series[CEILING_SIGNAL].tolist()[len(series) // 2 :]
    observed = {int(value) for value in tail}
    matched = ceilings & observed
    if not matched:
        return None
    return sorted(matched)[0]


def _confirmed_ceiling(
    component_id: str,
    onset: datetime,
    changes: list[ConfigChange],
    telemetry: pd.DataFrame,
) -> EvidenceItem | None:
    change, _ = nearest_preceding_change(component_id, onset, changes)
    if change is None:
        return None
    ceiling = matched_ceiling(component_id, change, telemetry)
    if ceiling is None:
        return None
    return EvidenceItem(
        kind="confirmed",
        source="metric",
        statement=f"{component_id} {CEILING_SIGNAL} pinned flat at exactly {ceiling}, matching the configured ceiling",
        ref=f"{component_id}/{CEILING_SIGNAL}",
    )


def _alert_on_component(component_id: str, onset: datetime, alerts: list[AlertRecord]) -> EvidenceItem | None:
    alert = nearest_preceding_alert(component_id, onset, alerts)
    if alert is None:
        return None
    return EvidenceItem(
        kind="confirmed",
        source="alert",
        statement=(
            f"Alert {alert.alert_id} fired on {component_id}: "
            f"{alert.metric} {alert.observed} crossed {alert.threshold}"
        ),
        ref=alert.alert_id,
    )


def _downstream_alert(path: list[str], alerts: list[AlertRecord]) -> EvidenceItem | None:
    if len(path) < 3:
        return None
    intermediate = path[1]
    for alert in alerts:
        if alert.component_id != intermediate:
            continue
        return EvidenceItem(
            kind="correlated",
            source="alert",
            statement=(
                f"{intermediate} raised {alert.alert_id} ({alert.metric} {alert.observed}) "
                f"immediately downstream of the cause on the path to {path[-1]}"
            ),
            ref=alert.alert_id,
        )
    return None


def _error_log(component_id: str, logs: list[LogRecord]) -> EvidenceItem | None:
    for log in logs:
        if log.component_id != component_id:
            continue
        if log.severity.value not in {"ERROR", "CRITICAL"}:
            continue
        return EvidenceItem(
            kind="correlated",
            source="log",
            statement=f"{component_id} logged {log.severity.value}: {log.template[:120]}",
            ref=f"log:{component_id}@{log.ts.isoformat()}",
        )
    return None


def confirmed_evidence(
    candidate_id: str,
    path: list[str],
    onset: datetime,
    twin: TopologyTwin,
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
    logs: list[LogRecord],
    telemetry: pd.DataFrame,
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for builder in (
        _confirmed_config(candidate_id, onset, changes),
        _confirmed_ceiling(candidate_id, onset, changes, telemetry),
        _alert_on_component(candidate_id, onset, alerts),
        _downstream_alert(path, alerts),
        _error_log(candidate_id, logs),
    ):
        if builder is not None:
            items.append(builder)
    items.append(
        EvidenceItem(
            kind="confirmed",
            source="topology",
            statement=f"Dependency path confirms impact route: {' -> '.join(path)}",
            ref=f"topology:{candidate_id}->{path[-1]}",
        )
    )
    items.append(
        EvidenceItem(
            kind="missing",
            source="topology",
            statement=(
                "No SNMP interface error/discard counters ingested for the data-tier switch; "
                "a concurrent network-layer contribution cannot be fully ruled out"
            ),
        )
    )
    return items


def decoy_evidence(
    decoy_id: str,
    symptom_id: str,
    onset: datetime,
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    change, _ = nearest_preceding_change(decoy_id, onset, changes)
    if change is not None:
        lead = _lead_seconds(onset, change.ts)
        items.append(
            EvidenceItem(
                kind="correlated",
                source="config",
                statement=(
                    f"Config change {change.change_id} on {decoy_id} landed only {lead:.0f}s before onset, "
                    f"closer in time than the true cause"
                ),
                ref=change.change_id,
            )
        )
    alert = nearest_preceding_alert(decoy_id, onset, alerts)
    if alert is not None:
        items.append(
            EvidenceItem(
                kind="correlated",
                source="alert",
                statement=f"Alert {alert.alert_id} recorded {alert.metric} {alert.observed} on {decoy_id} before onset",
                ref=alert.alert_id,
            )
        )
    items.append(
        EvidenceItem(
            kind="missing",
            source="topology",
            statement=(
                f"Topology twin finds no dependency path from {decoy_id} to symptom {symptom_id}; "
                f"temporal proximity is coincidental and the candidate is rejected as non-causal"
            ),
        )
    )
    return items
