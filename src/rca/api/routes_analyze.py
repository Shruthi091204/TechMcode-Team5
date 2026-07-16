from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from contracts.schemas import (
    AlertRecord,
    ConfigChange,
    EvidenceKind,
    IncidentReport,
    LogRecord,
    TelemetryPoint,
    TimelineEvent,
    TimelineKind,
    Topology,
)
from rca.agents.investigator import investigate_incident
from rca.agents.remediation import generate_remediation_steps
from rca.agents.skeptic import run_storm_verification
from rca.audit.chain import append_audit_event
from rca.pipeline import ANOMALY_METRICS, LiveIncident, build_incident_from_data
from rca.stats.store import record_analysis

router = APIRouter()


class AnalyzeRequest(BaseModel):
    topology: Topology
    telemetry: list[TelemetryPoint] = Field(min_length=1)
    logs: list[LogRecord] = Field(default_factory=list)
    alerts: list[AlertRecord] = Field(default_factory=list)
    config_changes: list[ConfigChange] = Field(default_factory=list)
    symptom_component: str | None = None
    incident_id: str | None = None


class HealthyResult(BaseModel):
    status: str = "healthy"
    components_analyzed: int
    telemetry_windows: int
    metrics_evaluated: list[str]
    message: str


def _rank_incident(request: AnalyzeRequest) -> LiveIncident:
    return build_incident_from_data(
        topology=request.topology,
        telemetry_points=request.telemetry,
        logs=request.logs,
        alerts=request.alerts,
        changes=request.config_changes,
        symptom_id=request.symptom_component,
        incident_id=request.incident_id,
    )


def _build_timeline(request: AnalyzeRequest, incident: LiveIncident) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for change in request.config_changes:
        events.append(
            TimelineEvent(
                ts=change.ts,
                component_id=change.component_id,
                description=f"Config change {change.change_id} ({change.change_type})",
                kind=TimelineKind.CONFIG,
            )
        )
    for alert in request.alerts:
        events.append(
            TimelineEvent(
                ts=alert.ts,
                component_id=alert.component_id,
                description=f"{alert.severity.value} alert: {alert.metric} {alert.observed:g} vs {alert.threshold:g}",
                kind=TimelineKind.ALERT,
            )
        )
    for log in request.logs:
        events.append(
            TimelineEvent(
                ts=log.ts,
                component_id=log.component_id,
                description=log.template[:400],
                kind=TimelineKind.LOG,
            )
        )
    if not events:
        events.append(
            TimelineEvent(
                ts=incident.detected_at,
                component_id=incident.symptom_component,
                description=incident.symptom[:400],
                kind=TimelineKind.ANOMALY,
            )
        )
    events.sort(key=lambda event: event.ts)
    return events


def _build_narrative(incident: LiveIncident) -> str:
    leading = incident.hypotheses[0]
    path = " -> ".join(leading.topology_path)
    narrative = (
        f"{incident.symptom}. The topology-constrained causal engine ranks {leading.root_cause_component} "
        f"({leading.fault_type.value}) as the most likely root cause along the impact path {path}."
    )
    if leading.counterfactual:
        return f"{narrative} {leading.counterfactual}"
    return narrative


def _recommended_steps(incident: LiveIncident) -> list[str]:
    leading = incident.hypotheses[0]
    missing = [item.statement for item in leading.evidence if item.kind is EvidenceKind.MISSING]
    if missing:
        return missing
    return [f"Inspect {leading.root_cause_component} along the impact path {' -> '.join(leading.topology_path)}."]


def _deterministic_report(request: AnalyzeRequest, incident: LiveIncident) -> IncidentReport:
    audit_hash = append_audit_event(
        event_type="UPLOAD_ANALYZED_DETERMINISTIC",
        payload={"incident_id": incident.incident_id, "top_cause": incident.hypotheses[0].root_cause_component},
    )
    return IncidentReport(
        incident_id=incident.incident_id,
        detected_at=incident.detected_at,
        symptom=incident.symptom,
        symptom_component=incident.symptom_component,
        hypotheses=incident.hypotheses,
        timeline=_build_timeline(request, incident),
        narrative=_build_narrative(incident),
        recommended_steps=_recommended_steps(incident),
        audit_hash=audit_hash,
    )


def _enriched_report(incident: LiveIncident) -> IncidentReport:
    append_audit_event(
        event_type="UPLOAD_ANALYZED",
        payload={"incident_id": incident.incident_id, "top_cause": incident.hypotheses[0].root_cause_component},
    )
    verified_hypotheses, transcripts = run_storm_verification(hypotheses=incident.hypotheses, symptom=incident.symptom)
    append_audit_event(
        event_type="STORM_VERIFICATION_COMPLETED",
        payload={"transcripts": transcripts, "top_cause": verified_hypotheses[0].root_cause_component},
    )
    grounded_steps = generate_remediation_steps(leading_hypothesis=verified_hypotheses[0])
    investigated = investigate_incident(
        incident_id=incident.incident_id,
        detected_at=incident.detected_at,
        symptom=incident.symptom,
        symptom_component=incident.symptom_component,
        hypotheses=verified_hypotheses,
    )
    final_hash = append_audit_event(
        event_type="INCIDENT_REPORT_FINALIZED",
        payload={"incident_id": incident.incident_id, "top_confidence": verified_hypotheses[0].confidence},
    )
    return IncidentReport(
        incident_id=investigated.incident_id,
        detected_at=investigated.detected_at,
        symptom=investigated.symptom,
        symptom_component=investigated.symptom_component,
        hypotheses=verified_hypotheses,
        timeline=investigated.timeline,
        narrative=investigated.narrative,
        recommended_steps=grounded_steps,
        audit_hash=final_hash,
    )


@router.post("/analyze", response_model=None)
def analyze_uploaded_incident(request: AnalyzeRequest, fast: bool = False) -> IncidentReport | HealthyResult:
    node_count = len(request.topology.components)
    try:
        incident = _rank_incident(request)
    except ValueError as engine_error:
        if "no anomalies" in str(engine_error).lower():
            record_analysis(node_count)
            return HealthyResult(
                components_analyzed=node_count,
                telemetry_windows=len({point.window_start for point in request.telemetry}),
                metrics_evaluated=list(ANOMALY_METRICS),
                message="No anomalies detected — all monitored components are within baseline.",
            )
        raise HTTPException(status_code=422, detail=str(engine_error)) from engine_error

    record_analysis(node_count)
    if fast:
        return _deterministic_report(request, incident)
    try:
        return _enriched_report(incident)
    except Exception:
        return _deterministic_report(request, incident)
