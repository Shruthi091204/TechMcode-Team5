import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field
from contracts.schemas import Hypothesis, IncidentReport, TimelineEvent
from rca.agents.client import MODEL_NAME, OUTPUT_CONFIG, THINKING_CONFIG, get_anthropic_client
from rca.agents.tools import query_changes, query_graph, query_logs, query_metrics


class InvestigatorOutput(BaseModel):
    timeline: list[TimelineEvent] = Field(min_length=1)
    narrative: str = Field(min_length=1)
    recommended_steps: list[str] = Field(min_length=1)


def build_system_prompt() -> str:
    return (
        "You are an expert Network Root-Cause Investigator for a Tier-1 NOC. "
        "You are provided with deterministic causal hypotheses derived from physical network topology. "
        "Your task is to verify the evidence using your investigation tools, construct a chronological timeline of events, "
        "write a clear, plain-English root-cause narrative, and recommend next diagnostic steps grounded strictly in missing evidence. "
        "Never invent metrics, logs, or components not returned by your tools."
    )


def format_hypotheses_payload(hypotheses: list[Hypothesis]) -> str:
    serialized_items = [hypothesis.model_dump(mode="json") for hypothesis in hypotheses]
    return json.dumps(serialized_items, indent=2)


def generate_fallback_audit_hash(narrative_text: str) -> str:
    return hashlib.sha256(narrative_text.encode("utf-8")).hexdigest()


def extract_investigator_output(runner_result: Any) -> InvestigatorOutput:
    for message_item in reversed(runner_result.messages):
        if message_item.role != "assistant":
            continue
        for content_block in message_item.content:
            if content_block.type == "tool_use" and content_block.name == "InvestigatorOutput":
                return InvestigatorOutput.model_validate(content_block.input)
            if hasattr(content_block, "text") and "{" in content_block.text:
                try:
                    raw_json = json.loads(content_block.text)
                    return InvestigatorOutput.model_validate(raw_json)
                except (json.JSONDecodeError, ValueError):
                    continue
    raise ValueError("investigator loop failed to produce structured InvestigatorOutput")


def investigate_incident(
    incident_id: str,
    detected_at: datetime,
    symptom: str,
    symptom_component: str,
    hypotheses: list[Hypothesis],
) -> IncidentReport:
    anthropic_client = get_anthropic_client()
    hypotheses_json = format_hypotheses_payload(hypotheses)

    user_prompt = (
        f"Incident ID: {incident_id}\n"
        f"Detected At: {detected_at.isoformat()}\n"
        f"Symptom: {symptom} on component {symptom_component}\n\n"
        f"Deterministic Causal Hypotheses:\n{hypotheses_json}\n\n"
        "Investigate by querying graph topology, metrics, logs, and config changes around the anomaly windows. "
        "Return the final timeline, narrative, and recommended steps."
    )

    runner_result = anthropic_client.beta.messages.tool_runner(
        model=MODEL_NAME,
        max_tokens=4096,
        system=build_system_prompt(),
        thinking=THINKING_CONFIG,
        output_config={
            "effort": OUTPUT_CONFIG["effort"],
            "format": InvestigatorOutput.model_json_schema(),
        },
        tools=[query_graph, query_metrics, query_logs, query_changes],
        messages=[{"role": "user", "content": user_prompt}],
    )

    structured_result = extract_investigator_output(runner_result)
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