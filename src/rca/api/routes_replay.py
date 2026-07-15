import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from contracts.schemas import Hypothesis, IncidentReport
from rca.agents.investigator import investigate_incident
from rca.agents.remediation import generate_remediation_steps
from rca.agents.skeptic import run_storm_verification
from rca.audit.chain import append_audit_event
from rca.audit.verify import AuditVerificationResult, verify_audit_chain

router = APIRouter()

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
INCIDENTS_DIR = Path(__file__).resolve().parents[3] / "incidents"

IncidentInputs = tuple[str, datetime, str, str, list[Hypothesis], str]


def load_scenario_incident(scenario: str) -> IncidentReport:
    recorded_path = INCIDENTS_DIR / f"{scenario}.json"
    if recorded_path.exists():
        raw_payload = json.loads(recorded_path.read_text(encoding="utf-8"))
        return IncidentReport.model_validate(raw_payload)

    fixture_path = FIXTURES_DIR / "incident_report.json"
    if fixture_path.exists():
        raw_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return IncidentReport.model_validate(raw_payload)

    raise HTTPException(status_code=404, detail=f"Scenario '{scenario}' not found on disk")


def _live_incident_inputs() -> IncidentInputs | None:
    try:
        from rca.pipeline import build_live_incident
    except ImportError:
        return None
    live = build_live_incident()
    return (
        live.incident_id,
        live.detected_at,
        live.symptom,
        live.symptom_component,
        live.hypotheses,
        "live_causal_engine",
    )


def _static_incident_inputs(scenario: str) -> IncidentInputs:
    base_incident = load_scenario_incident(scenario)
    return (
        base_incident.incident_id,
        base_incident.detected_at,
        base_incident.symptom,
        base_incident.symptom_component,
        base_incident.hypotheses,
        "static_fixture",
    )


def resolve_incident_inputs(scenario: str) -> IncidentInputs:
    live_inputs = _live_incident_inputs()
    if live_inputs is not None:
        return live_inputs
    return _static_incident_inputs(scenario)


@router.post("/replay/{scenario}", response_model=IncidentReport)
def replay_incident_scenario(scenario: str) -> IncidentReport:
    try:
        incident_id, detected_at, symptom, symptom_component, hypotheses, source = resolve_incident_inputs(scenario)

        append_audit_event(
            event_type="REPLAY_TRIGGERED",
            payload={"scenario": scenario, "incident_id": incident_id, "hypothesis_source": source},
        )

        append_audit_event(
            event_type="CAUSAL_HYPOTHESES_INGESTED",
            payload={"count": len(hypotheses), "source": source, "top_cause": hypotheses[0].root_cause_component},
        )

        verified_hypotheses, transcripts = run_storm_verification(hypotheses=hypotheses, symptom=symptom)
        append_audit_event(
            event_type="STORM_VERIFICATION_COMPLETED",
            payload={"transcripts": transcripts, "top_cause": verified_hypotheses[0].root_cause_component},
        )

        grounded_steps = generate_remediation_steps(leading_hypothesis=verified_hypotheses[0])
        append_audit_event(
            event_type="REMEDIATION_PLAN_GENERATED",
            payload={"steps_count": len(grounded_steps)},
        )

        investigated_report = investigate_incident(
            incident_id=incident_id,
            detected_at=detected_at,
            symptom=symptom,
            symptom_component=symptom_component,
            hypotheses=verified_hypotheses,
        )

        final_hash = append_audit_event(
            event_type="INCIDENT_REPORT_FINALIZED",
            payload={"incident_id": incident_id, "top_confidence": verified_hypotheses[0].confidence},
        )

        return IncidentReport(
            incident_id=investigated_report.incident_id,
            detected_at=investigated_report.detected_at,
            symptom=investigated_report.symptom,
            symptom_component=investigated_report.symptom_component,
            hypotheses=verified_hypotheses,
            timeline=investigated_report.timeline,
            narrative=investigated_report.narrative,
            recommended_steps=grounded_steps,
            audit_hash=final_hash,
        )
    except HTTPException as http_err:
        raise http_err
    except Exception as execution_error:
        append_audit_event(
            event_type="REPLAY_FAILED",
            payload={"scenario": scenario, "error": str(execution_error)},
        )
        raise HTTPException(status_code=500, detail=str(execution_error)) from execution_error


@router.get("/audit/verify", response_model=AuditVerificationResult)
def verify_audit_trail() -> AuditVerificationResult:
    return verify_audit_chain()