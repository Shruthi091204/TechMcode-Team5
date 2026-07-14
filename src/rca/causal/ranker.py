from __future__ import annotations

from datetime import datetime

import pandas as pd

from contracts.schemas import (
    AlertRecord,
    Anomaly,
    ConfigChange,
    FaultType,
    Hypothesis,
    LogRecord,
)
from rca.causal.counterfactual import counterfactual_statement
from rca.causal.evidence import confirmed_evidence, decoy_evidence, matched_ceiling
from rca.causal.temporal import nearest_preceding_alert, nearest_preceding_change, precedence_score
from rca.graph.twin import TopologyTwin

WEIGHT_CAUSAL = 0.3
WEIGHT_PRECEDENCE = 0.1
WEIGHT_CONFIG = 0.25
WEIGHT_ROOTNESS = 0.1
WEIGHT_EVIDENCE = 0.2
WEIGHT_SEVERITY = 0.05
DECOY_CONFIDENCE_CEILING = 0.1
MAX_DECOYS = 3


def _onset_of(component_id: str, anomalies: list[Anomaly], fallback: datetime) -> datetime:
    onsets = [anomaly.onset_ts for anomaly in anomalies if anomaly.component_id == component_id]
    return min(onsets) if onsets else fallback


def _severity_of(component_id: str, anomalies: list[Anomaly]) -> float:
    scores = [anomaly.severity_score for anomaly in anomalies if anomaly.component_id == component_id]
    return max(scores) if scores else 0.0


def _fault_type_for(component_id: str, onset: datetime, changes: list[ConfigChange]) -> FaultType:
    change, _ = nearest_preceding_change(component_id, onset, changes)
    if change is None:
        return FaultType.CAPACITY_EXHAUSTION
    if "max_connections" in change.after:
        return FaultType.CONFIG_POOL_EXHAUSTION
    return FaultType.BAD_CONFIG_PUSH


def _decoy_fault_type(component_id: str, onset: datetime, changes: list[ConfigChange]) -> FaultType:
    change, _ = nearest_preceding_change(component_id, onset, changes)
    if change is not None:
        return FaultType.BAD_CONFIG_PUSH
    return FaultType.CAPACITY_EXHAUSTION


def _rootness(twin: TopologyTwin, candidate_id: str, candidates: list[str]) -> float:
    others = set(candidates) - {candidate_id}
    if not others:
        return 1.0
    return len(set(twin.blast_radius(candidate_id)) & others) / len(others)


def _evidence_strength(
    candidate_id: str,
    onset: datetime,
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
    telemetry: pd.DataFrame,
) -> float:
    change, _ = nearest_preceding_change(candidate_id, onset, changes)
    strength = 0.0
    if change is not None:
        strength += 0.5
        if matched_ceiling(candidate_id, change, telemetry) is not None:
            strength += 0.3
    if nearest_preceding_alert(candidate_id, onset, alerts) is not None:
        strength += 0.2
    return min(1.0, strength)


def _candidate_confidence(
    twin: TopologyTwin,
    candidate_id: str,
    symptom_id: str,
    symptom_onset: datetime,
    causal_score: float,
    candidates: list[str],
    anomalies: list[Anomaly],
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
    telemetry: pd.DataFrame,
    max_severity: float,
) -> float:
    onset = _onset_of(candidate_id, anomalies, symptom_onset)
    precedence = precedence_score(onset, symptom_onset)
    _, config_proximity = nearest_preceding_change(candidate_id, onset, changes)
    severity = _severity_of(candidate_id, anomalies) / max_severity if max_severity > 0 else 0.0
    return (
        WEIGHT_CAUSAL * causal_score
        + WEIGHT_PRECEDENCE * precedence
        + WEIGHT_CONFIG * config_proximity
        + WEIGHT_ROOTNESS * _rootness(twin, candidate_id, candidates)
        + WEIGHT_EVIDENCE * _evidence_strength(candidate_id, onset, changes, alerts, telemetry)
        + WEIGHT_SEVERITY * severity
    )


def rank_hypotheses(
    twin: TopologyTwin,
    symptom_id: str,
    symptom_onset: datetime,
    candidates: list[str],
    decoys: list[str],
    causal_scores: dict[str, float],
    anomalies: list[Anomaly],
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
    logs: list[LogRecord],
    telemetry: pd.DataFrame,
) -> list[Hypothesis]:
    max_severity = max((anomaly.severity_score for anomaly in anomalies), default=1.0)

    scored: list[tuple[str, float]] = []
    for candidate in candidates:
        confidence = _candidate_confidence(
            twin,
            candidate,
            symptom_id,
            symptom_onset,
            causal_scores.get(candidate, 0.0),
            candidates,
            anomalies,
            changes,
            alerts,
            telemetry,
            max_severity,
        )
        scored.append((candidate, confidence))
    scored.sort(key=lambda pair: (-pair[1], pair[0]))

    hypotheses: list[Hypothesis] = []
    rank = 1
    for candidate, confidence in scored:
        path = twin.impact_path(candidate, symptom_id) or [candidate]
        onset = _onset_of(candidate, anomalies, symptom_onset)
        hypotheses.append(
            Hypothesis(
                rank=rank,
                root_cause_component=candidate,
                fault_type=_fault_type_for(candidate, onset, changes),
                confidence=round(min(0.99, max(DECOY_CONFIDENCE_CEILING + 0.01, confidence)), 3),
                causal_score=round(causal_scores.get(candidate, 0.0), 3),
                topology_path=path,
                evidence=confirmed_evidence(candidate, path, onset, twin, changes, alerts, logs, telemetry),
                counterfactual=counterfactual_statement(candidate, symptom_id, onset, telemetry, changes),
            )
        )
        rank += 1

    for offset, decoy in enumerate(_ordered_decoys(decoys, symptom_onset, anomalies, changes, alerts)):
        onset = _onset_of(decoy, anomalies, symptom_onset)
        hypotheses.append(
            Hypothesis(
                rank=rank,
                root_cause_component=decoy,
                fault_type=_decoy_fault_type(decoy, onset, changes),
                confidence=round(DECOY_CONFIDENCE_CEILING - 0.01 - 0.01 * offset, 3),
                causal_score=0.0,
                topology_path=[decoy],
                evidence=decoy_evidence(decoy, symptom_id, onset, changes, alerts),
            )
        )
        rank += 1

    return hypotheses


def _decoy_suspicion(
    decoy_id: str,
    symptom_onset: datetime,
    anomalies: list[Anomaly],
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
) -> tuple[int, float]:
    onset = _onset_of(decoy_id, anomalies, symptom_onset)
    change, proximity = nearest_preceding_change(decoy_id, onset, changes)
    has_config = 1 if change is not None else 0
    return has_config, proximity + _severity_of(decoy_id, anomalies) / 100.0


def _ordered_decoys(
    decoys: list[str],
    symptom_onset: datetime,
    anomalies: list[Anomaly],
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
) -> list[str]:
    ranked = sorted(
        decoys,
        key=lambda decoy: (*_decoy_suspicion(decoy, symptom_onset, anomalies, changes, alerts), decoy),
        reverse=True,
    )
    return ranked[:MAX_DECOYS]
