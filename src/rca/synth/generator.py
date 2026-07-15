from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from contracts.schemas import (
    AlertRecord,
    ConfigChange,
    FaultType,
    LogRecord,
    Severity,
    TelemetryPoint,
    Topology,
)
from rca.graph.twin import TopologyTwin

WINDOW_SECONDS = 30
WINDOW_COUNT = 32
INJECTION_INDEX = 16
BASE_TIME = datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)
PEAK_LATENCY_MS = 165.0

_BASELINE = {
    "latency_ms": 22.0,
    "jitter_ms": 2.0,
    "packet_loss_pct": 0.1,
    "throughput_mbps": 480.0,
    "error_rate": 0.001,
    "connection_count": 48.0,
    "cpu_pct": 32.0,
    "mem_pct": 44.0,
}

_FAULT_SIGNATURE: dict[FaultType, tuple[str, float, dict | None]] = {
    FaultType.CONFIG_POOL_EXHAUSTION: (
        "connection_count",
        150.0,
        {"change_type": "db_param_update", "before": {"max_connections": 500}, "after": {"max_connections": 150}},
    ),
    FaultType.BAD_CONFIG_PUSH: (
        "error_rate",
        0.09,
        {"change_type": "nginx_tune", "before": {"worker_connections": 1024}, "after": {"worker_connections": 256}},
    ),
    FaultType.CAPACITY_EXHAUSTION: ("cpu_pct", 97.0, None),
    FaultType.DDOS_FLOOD: ("connection_count", 820.0, None),
    FaultType.LINK_DEGRADATION: ("packet_loss_pct", 9.5, None),
    FaultType.NIC_FAILURE: ("packet_loss_pct", 13.0, None),
    FaultType.PORT_SCAN: ("connection_count", 610.0, None),
}


@dataclass(frozen=True)
class GeneratedIncident:
    incident_id: str
    root_cause: str
    symptom: str
    fault_type: FaultType
    injection_ts: datetime
    path: list[str]
    telemetry: list[TelemetryPoint]
    logs: list[LogRecord]
    alerts: list[AlertRecord]
    config_changes: list[ConfigChange]


def _window_start(index: int) -> datetime:
    return BASE_TIME + timedelta(seconds=index * WINDOW_SECONDS)


def pick_symptom(twin: TopologyTwin, topology: Topology, root: str) -> str | None:
    web_tier = {component.component_id for component in topology.components if component.tier.value == "web"}
    reachable = sorted(set(twin.blast_radius(root)) & web_tier)
    return reachable[0] if reachable else None


def _noisy(rng: random.Random, value: float) -> float:
    return round(max(0.0, value * (1.0 + rng.uniform(-0.01, 0.01))), 4)


def _component_baseline(rng: random.Random) -> dict[str, float]:
    return {key: _noisy(rng, value) for key, value in _BASELINE.items()}


def _telemetry_point(component_id: str, index: int, fields: dict[str, float]) -> TelemetryPoint:
    return TelemetryPoint(
        component_id=component_id,
        window_start=_window_start(index),
        latency_ms=fields["latency_ms"],
        jitter_ms=fields["jitter_ms"],
        packet_loss_pct=min(100.0, fields["packet_loss_pct"]),
        throughput_mbps=fields["throughput_mbps"],
        error_rate=min(1.0, fields["error_rate"]),
        connection_count=int(fields["connection_count"]),
        cpu_pct=min(100.0, fields["cpu_pct"]),
        mem_pct=min(100.0, fields["mem_pct"]),
    )


def _ramp(index: int, onset: int) -> float:
    return min(1.0, (index - onset + 1) / 4.0)


def _injected_latency(ramp: float, reach: float) -> float:
    return round(_BASELINE["latency_ms"] + ramp * (PEAK_LATENCY_MS - _BASELINE["latency_ms"]) * reach, 3)


def _telemetry(
    topology: Topology,
    root: str,
    symptom: str,
    path: list[str],
    fault_type: FaultType,
    rng: random.Random,
) -> list[TelemetryPoint]:
    metric_field, anomalous_value, _ = _FAULT_SIGNATURE[fault_type]
    onset_of = {component: INJECTION_INDEX + position for position, component in enumerate(path)}
    points: list[TelemetryPoint] = []
    for component in (item.component_id for item in topology.components):
        baseline = _component_baseline(rng)
        for index in range(WINDOW_COUNT):
            fields = dict(baseline)
            onset = onset_of.get(component)
            if onset is not None and index >= onset:
                ramp = _ramp(index, onset)
                reach = 1.0 if component == symptom else 0.7
                fields["latency_ms"] = _injected_latency(ramp, reach)
                fields["error_rate"] = round(min(0.9, _BASELINE["error_rate"] + ramp * 0.04), 4)
                if component == root:
                    fields[metric_field] = anomalous_value
                    fields["latency_ms"] = _injected_latency(ramp, 1.0)
            points.append(_telemetry_point(component, index, fields))
    return points


def generate_healthy(topology: Topology, seed: int = 0) -> list[TelemetryPoint]:
    rng = random.Random(seed)
    points: list[TelemetryPoint] = []
    for component in (item.component_id for item in topology.components):
        baseline = _component_baseline(rng)
        for index in range(WINDOW_COUNT):
            points.append(_telemetry_point(component, index, dict(baseline)))
    return points


def generate_incident(topology: Topology, root: str, fault_type: FaultType, seed: int = 0) -> GeneratedIncident | None:
    twin = TopologyTwin(topology)
    symptom = pick_symptom(twin, topology, root)
    if symptom is None:
        return None
    path = twin.impact_path(root, symptom)
    if not path or len(path) < 2:
        return None

    rng = random.Random(seed)
    metric_field, anomalous_value, config_spec = _FAULT_SIGNATURE[fault_type]
    injection_ts = _window_start(INJECTION_INDEX)
    telemetry = _telemetry(topology, root, symptom, path, fault_type, rng)

    config_changes: list[ConfigChange] = []
    if config_spec is not None:
        config_changes.append(
            ConfigChange(
                change_id=f"CHG-{7000 + seed}",
                component_id=root,
                ts=injection_ts - timedelta(seconds=90),
                author="auto.injector",
                change_type=config_spec["change_type"],
                before=config_spec["before"],
                after=config_spec["after"],
                ticket_id=f"SYN-{1000 + seed}",
            )
        )

    symptom_alert_ts = injection_ts + timedelta(seconds=len(path) * WINDOW_SECONDS)
    alerts = [
        AlertRecord(
            alert_id=f"ALT-{8000 + seed}",
            component_id=symptom,
            ts=symptom_alert_ts,
            severity=Severity.CRITICAL,
            rule="latency_p99_high",
            metric="latency_ms",
            threshold=100.0,
            observed=round(PEAK_LATENCY_MS, 1),
        ),
        AlertRecord(
            alert_id=f"ALT-{8500 + seed}",
            component_id=root,
            ts=injection_ts + timedelta(seconds=WINDOW_SECONDS),
            severity=Severity.ERROR,
            rule="resource_saturation",
            metric=metric_field,
            threshold=round(anomalous_value * 0.7, 3),
            observed=round(anomalous_value, 3),
        ),
    ]

    logs = [
        LogRecord(
            component_id=root,
            ts=injection_ts + timedelta(seconds=20),
            severity=Severity.ERROR,
            template=f"{fault_type.value} onset on {root}: {metric_field} reached {anomalous_value:g}",
        ),
        LogRecord(
            component_id=symptom,
            ts=symptom_alert_ts + timedelta(seconds=10),
            severity=Severity.CRITICAL,
            template=f"Upstream degradation propagated to {symptom} along {' -> '.join(path)}",
        ),
    ]

    return GeneratedIncident(
        incident_id=f"INC-{9000 + seed}",
        root_cause=root,
        symptom=symptom,
        fault_type=fault_type,
        injection_ts=injection_ts,
        path=path,
        telemetry=telemetry,
        logs=logs,
        alerts=alerts,
        config_changes=config_changes,
    )
