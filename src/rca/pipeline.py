from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel
from scipy.stats import median_abs_deviation

from contracts.schemas import (
    AlertRecord,
    Anomaly,
    ConfigChange,
    Hypothesis,
    LogRecord,
    Topology,
)
from rca.causal.candidate_set import candidate_causes, decoy_components
from rca.causal.model import attribute_causes
from rca.causal.ranker import rank_hypotheses
from rca.graph.twin import TopologyTwin

FIXTURES = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
ANOMALY_METRICS = ("latency_ms", "connection_count", "error_rate", "packet_loss_pct")
SEVERITY_THRESHOLD = 4.0
BASELINE_FRACTION = 0.35
MIN_BASELINE_WINDOWS = 5


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _ground_truth_symptom() -> str:
    payload = json.loads((FIXTURES / "ground_truth.json").read_text())
    return payload["symptom_component"]


def load_topology() -> Topology:
    return Topology.model_validate(json.loads((FIXTURES / "topology.json").read_text()))


def load_telemetry_frame() -> pd.DataFrame:
    frame = pd.read_csv(FIXTURES / "telemetry.csv")
    frame["window_start"] = frame["window_start"].map(_parse_ts)
    return frame


def _load_jsonl(name: str) -> list[dict]:
    lines = (FIXTURES / name).read_text().splitlines()
    return [json.loads(line) for line in lines if line]


def load_changes() -> list[ConfigChange]:
    return [ConfigChange.model_validate(record) for record in _load_jsonl("config_changes.jsonl")]


def load_alerts() -> list[AlertRecord]:
    return [AlertRecord.model_validate(record) for record in _load_jsonl("alerts.jsonl")]


def load_logs() -> list[LogRecord]:
    return [LogRecord.model_validate(record) for record in _load_jsonl("logs.jsonl")]


def _baseline_split(size: int) -> int:
    return max(MIN_BASELINE_WINDOWS, int(size * BASELINE_FRACTION))


def _baseline_scale(baseline: np.ndarray, centre: float) -> float:
    robust = float(median_abs_deviation(baseline, scale="normal"))
    if robust > 0.0:
        return robust
    return max(abs(centre) * 0.05, 0.5)


def _onset_index(deviations: np.ndarray, split: int) -> int:
    for index in range(split, deviations.size):
        if deviations[index] >= SEVERITY_THRESHOLD:
            return index
    return int(deviations.argmax())


def derive_anomalies(topology: Topology, telemetry: pd.DataFrame) -> list[Anomaly]:
    anomalies: list[Anomaly] = []
    for component_id in sorted(telemetry["component_id"].unique()):
        component_frame = telemetry[telemetry["component_id"] == component_id].sort_values("window_start")
        stamps = component_frame["window_start"].tolist()
        for metric in ANOMALY_METRICS:
            values = component_frame[metric].to_numpy(dtype=float)
            if values.size == 0:
                continue
            split = _baseline_split(values.size)
            baseline = values[:split]
            centre = float(np.median(baseline))
            scale = _baseline_scale(baseline, centre)
            deviations = np.abs(values - centre) / scale
            test_region = deviations[split:]
            if test_region.size == 0 or float(test_region.max()) < SEVERITY_THRESHOLD:
                continue
            peak_index = split + int(test_region.argmax())
            onset_index = _onset_index(deviations, split)
            anomalies.append(
                Anomaly(
                    component_id=component_id,
                    metric=metric,
                    onset_ts=stamps[onset_index],
                    severity_score=round(float(deviations[peak_index]), 3),
                    window_start=stamps[0],
                    window_end=stamps[-1],
                    baseline_value=round(centre, 3),
                    observed_value=round(float(values[peak_index]), 3),
                )
            )
    return anomalies


def _select_symptom(anomalies: list[Anomaly], topology: Topology, alerts: list[AlertRecord]) -> str:
    edge_tiers = {c.component_id for c in topology.components if c.tier.value in {"web", "edge"}}
    anomalous_edge = {a.component_id for a in anomalies if a.component_id in edge_tiers}
    critical = [a for a in alerts if a.severity.value == "CRITICAL" and a.component_id in anomalous_edge]
    if critical:
        return min(critical, key=lambda a: a.ts).component_id
    pool = [a for a in anomalies if a.component_id in anomalous_edge] or anomalies
    return max(pool, key=lambda a: a.severity_score).component_id


def analyse_incident(
    topology: Topology,
    telemetry: pd.DataFrame,
    anomalies: list[Anomaly],
    changes: list[ConfigChange],
    alerts: list[AlertRecord],
    logs: list[LogRecord],
    symptom_id: str | None = None,
) -> list[Hypothesis]:
    twin = TopologyTwin(topology)
    resolved_symptom = symptom_id or _select_symptom(anomalies, topology, alerts)
    onsets = [a.onset_ts for a in anomalies if a.component_id == resolved_symptom]
    symptom_onset = min(onsets) if onsets else max(a.onset_ts for a in anomalies)
    candidates = candidate_causes(twin, resolved_symptom, anomalies)
    decoys = decoy_components(twin, resolved_symptom, anomalies, symptom_onset, changes, alerts)
    causal_scores = attribute_causes(twin, candidates, resolved_symptom, telemetry)
    return rank_hypotheses(
        twin,
        resolved_symptom,
        symptom_onset,
        candidates,
        decoys,
        causal_scores,
        anomalies,
        changes,
        alerts,
        logs,
        telemetry,
    )


class LiveIncident(BaseModel):
    incident_id: str
    detected_at: datetime
    symptom: str
    symptom_component: str
    hypotheses: list[Hypothesis]


def _incident_id() -> str:
    payload = json.loads((FIXTURES / "ground_truth.json").read_text())
    return payload["incident_id"]


def _detection_time(symptom_id: str, alerts: list[AlertRecord], anomalies: list[Anomaly]) -> datetime:
    critical = [a for a in alerts if a.component_id == symptom_id and a.severity.value == "CRITICAL"]
    if critical:
        return min(alert.ts for alert in critical)
    onsets = [a.onset_ts for a in anomalies if a.component_id == symptom_id]
    if onsets:
        return min(onsets)
    return max(a.onset_ts for a in anomalies)


def _symptom_statement(symptom_id: str, anomalies: list[Anomaly], alerts: list[AlertRecord]) -> str:
    latency = [a for a in anomalies if a.component_id == symptom_id and a.metric == "latency_ms"]
    if not latency:
        component_anomalies = [a for a in anomalies if a.component_id == symptom_id]
        worst = max(component_anomalies, key=lambda a: a.severity_score, default=None)
        if worst is None:
            return f"{symptom_id} degraded beyond baseline"
        return f"{symptom_id} {worst.metric} reached {worst.observed_value:.2f} (baseline {worst.baseline_value:.2f})"
    peak = max(latency, key=lambda a: a.observed_value)
    deviation = (peak.observed_value - peak.baseline_value) / peak.baseline_value * 100 if peak.baseline_value else 0.0
    alert = next((a for a in alerts if a.component_id == symptom_id and a.metric == "latency_ms"), None)
    threshold = f" against a {alert.threshold:.0f}ms threshold" if alert else ""
    return (
        f"{symptom_id} latency reached {peak.observed_value:.1f}ms{threshold}, "
        f"a +{deviation:.0f}% deviation from the {peak.baseline_value:.1f}ms baseline"
    )


def build_live_incident(symptom_id: str | None = None) -> LiveIncident:
    topology = load_topology()
    telemetry = load_telemetry_frame()
    anomalies = derive_anomalies(topology, telemetry)
    alerts = load_alerts()
    changes = load_changes()
    logs = load_logs()
    resolved_symptom = symptom_id or _select_symptom(anomalies, topology, alerts)
    hypotheses = analyse_incident(topology, telemetry, anomalies, changes, alerts, logs, symptom_id=resolved_symptom)
    return LiveIncident(
        incident_id=_incident_id(),
        detected_at=_detection_time(resolved_symptom, alerts, anomalies),
        symptom=_symptom_statement(resolved_symptom, anomalies, alerts),
        symptom_component=resolved_symptom,
        hypotheses=hypotheses,
    )


def run_reference() -> list[Hypothesis]:
    topology = load_topology()
    telemetry = load_telemetry_frame()
    anomalies = derive_anomalies(topology, telemetry)
    return analyse_incident(
        topology, telemetry, anomalies, load_changes(), load_alerts(), load_logs(), symptom_id=_ground_truth_symptom()
    )


if __name__ == "__main__":
    for hypothesis in run_reference():
        print(
            f"#{hypothesis.rank}  {hypothesis.root_cause_component:10s}  "
            f"conf={hypothesis.confidence:.3f}  path={hypothesis.topology_path}"
        )
