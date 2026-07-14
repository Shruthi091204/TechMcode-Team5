from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)
from pydantic.json_schema import models_json_schema

SCHEMA_VERSION = "1.0.0"

ComponentId = Annotated[str, Field(min_length=3, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]
Percentage = Annotated[float, Field(ge=0.0, le=100.0)]
NonNegative = Annotated[float, Field(ge=0.0)]


class ComponentType(StrEnum):
    CORE_SWITCH = "core_switch"
    TOR_SWITCH = "tor_switch"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    WEB_SERVER = "web_server"
    APP_SERVER = "app_server"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    DNS_SERVER = "dns_server"


class Tier(StrEnum):
    EDGE = "edge"
    NETWORK = "network"
    WEB = "web"
    APP = "app"
    DATA = "data"


class RelationKind(StrEnum):
    CONNECTED_TO = "CONNECTED_TO"
    ROUTES_VIA = "ROUTES_VIA"
    DEPENDS_ON = "DEPENDS_ON"


class Severity(StrEnum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class FaultType(StrEnum):
    CONFIG_POOL_EXHAUSTION = "config_pool_exhaustion"
    BAD_CONFIG_PUSH = "bad_config_push"
    LINK_DEGRADATION = "link_degradation"
    NIC_FAILURE = "nic_failure"
    CAPACITY_EXHAUSTION = "capacity_exhaustion"
    DDOS_FLOOD = "ddos_flood"
    PORT_SCAN = "port_scan"


class EvidenceKind(StrEnum):
    CONFIRMED = "confirmed"
    CORRELATED = "correlated"
    MISSING = "missing"


class EvidenceSource(StrEnum):
    METRIC = "metric"
    LOG = "log"
    ALERT = "alert"
    CONFIG = "config"
    TOPOLOGY = "topology"
    COUNTERFACTUAL = "counterfactual"


class TimelineKind(StrEnum):
    CONFIG = "config"
    ALERT = "alert"
    ANOMALY = "anomaly"
    LOG = "log"
    PROPAGATION = "propagation"


class TrapKind(StrEnum):
    TEMPORAL_PROXIMITY = "temporal_proximity"
    CORRELATED_SIGNAL = "correlated_signal"


class Contract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)


class Component(Contract):
    component_id: ComponentId
    component_type: ComponentType
    tier: Tier
    rack: str = Field(min_length=1, max_length=32)
    capacity_mbps: NonNegative


class Dependency(Contract):
    source_id: ComponentId
    target_id: ComponentId
    relation: RelationKind

    @model_validator(mode="after")
    def reject_self_reference(self) -> Self:
        if self.source_id != self.target_id:
            return self
        raise ValueError(f"dependency is self-referential: {self.source_id}")


class Topology(Contract):
    schema_version: str = SCHEMA_VERSION
    components: list[Component] = Field(min_length=1)
    dependencies: list[Dependency] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_components(self) -> Self:
        identifiers = [component.component_id for component in self.components]
        duplicates = sorted({name for name in identifiers if identifiers.count(name) > 1})
        if not duplicates:
            return self
        raise ValueError(f"duplicate component_id: {duplicates}")

    @model_validator(mode="after")
    def reject_dangling_endpoints(self) -> Self:
        declared = {component.component_id for component in self.components}
        referenced = {edge.source_id for edge in self.dependencies}
        referenced |= {edge.target_id for edge in self.dependencies}
        dangling = sorted(referenced - declared)
        if not dangling:
            return self
        raise ValueError(f"dependencies reference undeclared components: {dangling}")


class TelemetryPoint(Contract):
    component_id: ComponentId
    window_start: AwareDatetime
    latency_ms: NonNegative
    jitter_ms: NonNegative
    packet_loss_pct: Percentage
    throughput_mbps: NonNegative
    error_rate: Probability
    connection_count: int = Field(ge=0)
    cpu_pct: Percentage
    mem_pct: Percentage


class LogRecord(Contract):
    component_id: ComponentId
    ts: AwareDatetime
    severity: Severity
    template: str = Field(min_length=1, max_length=512)


class AlertRecord(Contract):
    alert_id: str = Field(pattern=r"^ALT-\d{4,}$")
    component_id: ComponentId
    ts: AwareDatetime
    severity: Severity
    rule: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    threshold: float
    observed: float


class ConfigChange(Contract):
    change_id: str = Field(pattern=r"^CHG-\d{4,}$")
    component_id: ComponentId
    ts: AwareDatetime
    author: str = Field(min_length=1)
    change_type: str = Field(min_length=1)
    before: dict[str, JsonValue]
    after: dict[str, JsonValue]
    ticket_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def reject_empty_diff(self) -> Self:
        if self.before != self.after:
            return self
        raise ValueError(f"config change {self.change_id} has an identical before and after state")


class Anomaly(Contract):
    component_id: ComponentId
    metric: str = Field(min_length=1)
    onset_ts: AwareDatetime = Field(description="Change-point onset, not a threshold crossing")
    severity_score: NonNegative = Field(description="Deviation from baseline in median-absolute-deviation units")
    window_start: AwareDatetime
    window_end: AwareDatetime
    baseline_value: float
    observed_value: float

    @model_validator(mode="after")
    def reject_inverted_window(self) -> Self:
        if self.window_end > self.window_start:
            return self
        raise ValueError(f"anomaly window ends at or before it starts: {self.component_id}/{self.metric}")

    @model_validator(mode="after")
    def reject_onset_outside_window(self) -> Self:
        if self.window_start <= self.onset_ts <= self.window_end:
            return self
        raise ValueError(f"onset_ts falls outside the analysis window: {self.component_id}/{self.metric}")


class EvidenceItem(Contract):
    kind: EvidenceKind
    statement: str = Field(min_length=1, max_length=512)
    source: EvidenceSource
    ref: str | None = Field(default=None, description="Identifier of the raw record backing this statement")

    @model_validator(mode="after")
    def require_citation_for_observations(self) -> Self:
        if self.kind is EvidenceKind.MISSING or self.ref is not None:
            return self
        raise ValueError("confirmed and correlated evidence must cite a source record via `ref`")


class Hypothesis(Contract):
    rank: int = Field(ge=1)
    root_cause_component: ComponentId
    fault_type: FaultType
    confidence: Probability = Field(description="Deterministic score from the causal engine, never a model estimate")
    causal_score: Probability = Field(description="Attribution weight from the topology-constrained causal model")
    topology_path: list[ComponentId] = Field(min_length=1, description="Propagation path, cause first, symptom last")
    evidence: list[EvidenceItem] = Field(min_length=1)
    counterfactual: str | None = None
    skeptic_verdict: str | None = None

    @model_validator(mode="after")
    def require_path_rooted_at_cause(self) -> Self:
        if self.topology_path[0] == self.root_cause_component:
            return self
        raise ValueError(f"topology_path must begin at {self.root_cause_component}, begins at {self.topology_path[0]}")

    @model_validator(mode="after")
    def reject_cyclic_path(self) -> Self:
        if len(self.topology_path) == len(set(self.topology_path)):
            return self
        raise ValueError(f"topology_path revisits a component: {self.topology_path}")


class TimelineEvent(Contract):
    ts: AwareDatetime
    component_id: ComponentId
    description: str = Field(min_length=1, max_length=512)
    kind: TimelineKind


class IncidentReport(Contract):
    schema_version: str = SCHEMA_VERSION
    incident_id: str = Field(pattern=r"^INC-\d{4,}$")
    detected_at: AwareDatetime
    symptom: str = Field(min_length=1)
    symptom_component: ComponentId
    hypotheses: list[Hypothesis] = Field(min_length=1)
    timeline: list[TimelineEvent] = Field(min_length=1)
    narrative: str = Field(min_length=1)
    recommended_steps: list[str] = Field(min_length=1)
    audit_hash: str = Field(pattern=r"^[0-9a-f]{64}$", description="Head of the SHA-256 incident audit chain")

    @model_validator(mode="after")
    def require_contiguous_ranks(self) -> Self:
        ranks = [hypothesis.rank for hypothesis in self.hypotheses]
        if ranks == list(range(1, len(ranks) + 1)):
            return self
        raise ValueError(f"hypotheses must be ranked 1..N contiguously, received {ranks}")

    @model_validator(mode="after")
    def require_chronological_timeline(self) -> Self:
        stamps = [event.ts for event in self.timeline]
        if stamps == sorted(stamps):
            return self
        raise ValueError("timeline events must be ordered chronologically")

    @model_validator(mode="after")
    def require_symptom_terminates_leading_path(self) -> Self:
        if self.hypotheses[0].topology_path[-1] == self.symptom_component:
            return self
        raise ValueError("the leading hypothesis must terminate at the symptom component")


class Decoy(Contract):
    component_id: ComponentId
    trap_kind: TrapKind
    reason: str = Field(min_length=1, max_length=512)


class GroundTruth(Contract):
    schema_version: str = SCHEMA_VERSION
    incident_id: str = Field(pattern=r"^INC-\d{4,}$")
    scenario: str = Field(min_length=1)
    root_cause_component: ComponentId
    fault_type: FaultType
    injected_at: AwareDatetime
    onset_at: AwareDatetime
    symptom_component: ComponentId
    propagation_path: list[ComponentId] = Field(min_length=2)
    injection_command: str = Field(min_length=1, description="The exact command that produced the fault")
    decoys: list[Decoy] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_injection_precedes_onset(self) -> Self:
        if self.onset_at > self.injected_at:
            return self
        raise ValueError("onset_at must be strictly after injected_at")

    @model_validator(mode="after")
    def require_path_spans_cause_to_symptom(self) -> Self:
        starts_at_cause = self.propagation_path[0] == self.root_cause_component
        ends_at_symptom = self.propagation_path[-1] == self.symptom_component
        if starts_at_cause and ends_at_symptom:
            return self
        raise ValueError("propagation_path must run from root_cause_component to symptom_component")


CONTRACT_MODELS: tuple[type[Contract], ...] = (
    Topology,
    TelemetryPoint,
    LogRecord,
    AlertRecord,
    ConfigChange,
    Anomaly,
    EvidenceItem,
    Hypothesis,
    TimelineEvent,
    IncidentReport,
    GroundTruth,
)


def build_json_schema() -> dict[str, JsonValue]:
    _, bundled = models_json_schema(
        [(model, "validation") for model in CONTRACT_MODELS],
        title="Network Anomaly Root-Cause Assistant — Contract Schemas",
        ref_template="#/$defs/{model}",
    )
    bundled["version"] = SCHEMA_VERSION
    return bundled


def export_json_schema(destination: Path) -> Path:
    destination.write_text(json.dumps(build_json_schema(), indent=2) + "\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    written = export_json_schema(Path(__file__).parent / "schemas.json")
    print(f"exported {written}")
