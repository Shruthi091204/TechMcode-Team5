import json
from typing import Any
from pydantic import BaseModel, Field
from contracts.schemas import EvidenceKind, Hypothesis
from rca.agents.client import MODEL_NAME, OUTPUT_CONFIG, THINKING_CONFIG, get_anthropic_client


class RemediationPlan(BaseModel):
    diagnostic_steps: list[str] = Field(min_length=1)


def build_remediation_system_prompt() -> str:
    return (
        "You are a Senior Network Incident Commander. "
        "Your task is to provide concrete, actionable diagnostic and remediation steps for a network incident. "
        "CRITICAL CONSTRAINT: You must ground your recommended diagnostic steps strictly in the provided list of 'missing evidence'. "
        "Do not invent diagnostic checks for components or layers not mentioned in the missing evidence or root-cause path. "
        "Convert each missing evidence statement into a specific operational command or verification step."
    )


def extract_remediation_plan(runner_result: Any) -> RemediationPlan:
    for message_item in reversed(runner_result.messages):
        if message_item.role != "assistant":
            continue
        for content_block in message_item.content:
            if content_block.type == "tool_use" and content_block.name == "RemediationPlan":
                return RemediationPlan.model_validate(content_block.input)
            if hasattr(content_block, "text") and "{" in content_block.text:
                try:
                    raw_json = json.loads(content_block.text)
                    return RemediationPlan.model_validate(raw_json)
                except (json.JSONDecodeError, ValueError):
                    continue
    raise ValueError("remediation generation failed to produce structured RemediationPlan")


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

    anthropic_client = get_anthropic_client()
    user_prompt = (
        f"Root Cause Component: {leading_hypothesis.root_cause_component}\n"
        f"Fault Type: {leading_hypothesis.fault_type.value}\n"
        f"Impact Path: {' -> '.join(leading_hypothesis.topology_path)}\n\n"
        f"Missing Evidence Ledger (Must Ground Recommendations Here):\n{json.dumps(missing_evidence, indent=2)}\n\n"
        "Generate exact operational diagnostic steps to verify this missing evidence and mitigate the fault."
    )

    try:
        runner_result = anthropic_client.beta.messages.tool_runner(
            model=MODEL_NAME,
            max_tokens=1024,
            system=build_remediation_system_prompt(),
            thinking=THINKING_CONFIG,
            output_config={
                "effort": OUTPUT_CONFIG["effort"],
                "format": RemediationPlan.model_json_schema(),
            },
            tools=[],
            messages=[{"role": "user", "content": user_prompt}],
        )
        plan = extract_remediation_plan(runner_result)
        return plan.diagnostic_steps
    except Exception:
        return generate_fallback_steps(leading_hypothesis)