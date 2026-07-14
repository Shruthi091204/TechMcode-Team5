import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, HTTPException
from contracts.schemas import IncidentReport
from rca.agents.investigator import investigate_incident
from rca.agents.remediation import generate_remediation_steps
from rca.agents.skeptic import run_storm_verification
from rca.audit.chain import append_audit_event
from rca.audit.verify import AuditVerificationResult, verify_audit_chain

router = APIRouter()

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"
INCIDENTS_DIR = Path(__file__).resolve().parents[3] / "incidents"


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


@router.post("/replay/{scenario}", response_model=IncidentReport)
def replay_incident_scenario(scenario: str) -> IncidentReport:
    try:
        base_incident = load_scenario_incident(scenario)
        
        append_audit_event(
            event_type="REPLAY_TRIGGERED",
            payload={"scenario": scenario, "incident_id": base_incident.incident_id},
        )

        append_audit_event(
            event_type="CAUSAL_HYPOTHESES_INGESTED",
            payload={"count": len(base_incident.hypotheses)},
        )

        verified_hypotheses, transcripts = run_storm_verification(
            hypotheses=base_incident.hypotheses,
            symptom=base_incident.symptom,
        )
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
            incident_id=base_incident.incident_id,
            detected_at=base_incident.detected_at,
            symptom=base_incident.symptom,
            symptom_component=base_incident.symptom_component,
            hypotheses=verified_hypotheses,
        )

        final_hash = append_audit_event(
            event_type="INCIDENT_REPORT_FINALIZED",
            payload={"incident_id": base_incident.incident_id, "top_confidence": verified_hypotheses[0].confidence},
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