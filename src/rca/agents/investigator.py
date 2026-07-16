import hashlib
import json
from datetime import datetime

from pydantic import BaseModel, Field

from contracts.schemas import Hypothesis, IncidentReport, TimelineEvent
from rca.agents.runner import run_agent_loop
from rca.agents.tools import TOOL_SCHEMAS, execute_tool

INVESTIGATOR_MAX_TOKENS = 6000


class InvestigatorOutput(BaseModel):
    timeline: list[TimelineEvent] = Field(min_length=1)
    narrative: str = Field(min_length=1)
    recommended_steps: list[str] = Field(min_length=1)


def build_system_prompt() -> str:
    return (
        "You are an expert Network Root-Cause Investigator for a Tier-1 NOC. "
        "You are provided with deterministic causal hypotheses derived from physical network topology. "
        "Your task is to verify the evidence using your investigation tools, "
        "construct a chronological timeline of events, "
        "write a clear, plain-English root-cause narrative, "
        "and recommend next diagnostic steps grounded strictly in missing evidence. "
        "Consult the retrieve_runbook and retrieve_similar_incidents tools to ground your narrative and steps in "
        "established NOC playbooks and past resolutions, and cite the runbook id when you rely on one. "
        "Never invent metrics, logs, or components not returned by your tools."
    )


def format_hypotheses_payload(hypotheses: list[Hypothesis]) -> str:
    serialized_items = [hypothesis.model_dump(mode="json") for hypothesis in hypotheses]
    return json.dumps(serialized_items, indent=2)


def generate_fallback_audit_hash(narrative_text: str) -> str:
    return hashlib.sha256(narrative_text.encode("utf-8")).hexdigest()


def investigate_incident(
    incident_id: str,
    detected_at: datetime,
    symptom: str,
    symptom_component: str,
    hypotheses: list[Hypothesis],
) -> IncidentReport:
    hypotheses_json = format_hypotheses_payload(hypotheses)

    user_prompt = (
        f"Incident ID: {incident_id}\n"
        f"Detected At: {detected_at.isoformat()}\n"
        f"Symptom: {symptom} on component {symptom_component}\n\n"
        f"Deterministic Causal Hypotheses:\n{hypotheses_json}\n\n"
        "Investigate by querying graph topology, metrics, logs, and config changes around the anomaly windows. "
        "Return the final timeline, narrative, and recommended steps."
    )

    structured_result = run_agent_loop(
        system_prompt=build_system_prompt(),
        user_prompt=user_prompt,
        tool_schemas=TOOL_SCHEMAS,
        execute=execute_tool,
        response_model=InvestigatorOutput,
        max_tokens=INVESTIGATOR_MAX_TOKENS,
    )

    audit_hash = generate_fallback_audit_hash(structured_result.narrative)

    return IncidentReport(
        incident_id=incident_id,
        detected_at=detected_at,
        symptom=symptom,
        symptom_component=symptom_component,
        hypotheses=hypotheses,
        timeline=structured_result.timeline,
        narrative=structured_result.narrative,
        recommended_steps=structured_result.recommended_steps,
        audit_hash=audit_hash,
    )
