import json

from pydantic import BaseModel, Field

from contracts.schemas import EvidenceKind, Hypothesis
from rca.agents.runner import run_agent_loop
from rca.agents.tools import RETRIEVAL_TOOL_SCHEMAS, execute_tool

REMEDIATION_MAX_TOKENS = 1500


class RemediationPlan(BaseModel):
    diagnostic_steps: list[str] = Field(min_length=1)


def build_remediation_system_prompt() -> str:
    return (
        "You are a Senior Network Incident Commander. "
        "Your task is to provide concrete, actionable diagnostic and remediation steps for a network incident. "
        "CRITICAL CONSTRAINT: You must ground your recommended diagnostic steps "
        "strictly in the provided list of 'missing evidence'. "
        "Do not invent diagnostic checks for components or layers "
        "not mentioned in the missing evidence or root-cause path. "
        "Convert each missing evidence statement into a specific operational command or verification step. "
        "Call the retrieve_runbook tool with the fault type and symptom to pull the relevant NOC playbook, "
        "align each step with that playbook, and cite the runbook id in the step text "
        "(for example 'per RB-DB-POOL-01'). "
        "Optionally call retrieve_similar_incidents to reuse a proven past resolution."
    )


def generate_fallback_steps(leading_hypothesis: Hypothesis) -> list[str]:
    missing_items = [
        f"Verify missing telemetry: {item.statement}"
        for item in leading_hypothesis.evidence
        if item.kind == EvidenceKind.MISSING
    ]
    if missing_items:
        return missing_items
    return [
        f"Isolate component {leading_hypothesis.root_cause_component} and review recent configuration pushes.",
        f"Inspect interfaces along impact path: {' -> '.join(leading_hypothesis.topology_path)}.",
    ]


def generate_remediation_steps(leading_hypothesis: Hypothesis) -> list[str]:
    missing_evidence = [
        item.statement for item in leading_hypothesis.evidence if item.kind == EvidenceKind.MISSING
    ]
    if not missing_evidence:
        return generate_fallback_steps(leading_hypothesis)

    user_prompt = (
        f"Root Cause Component: {leading_hypothesis.root_cause_component}\n"
        f"Fault Type: {leading_hypothesis.fault_type.value}\n"
        f"Impact Path: {' -> '.join(leading_hypothesis.topology_path)}\n\n"
        f"Missing Evidence Ledger (Must Ground Recommendations Here):\n{json.dumps(missing_evidence, indent=2)}\n\n"
        "Generate exact operational diagnostic steps to verify this missing evidence and mitigate the fault."
    )

    try:
        plan = run_agent_loop(
            system_prompt=build_remediation_system_prompt(),
            user_prompt=user_prompt,
            tool_schemas=RETRIEVAL_TOOL_SCHEMAS,
            execute=execute_tool,
            response_model=RemediationPlan,
            max_tokens=REMEDIATION_MAX_TOKENS,
        )
        return plan.diagnostic_steps
    except Exception:
        return generate_fallback_steps(leading_hypothesis)
