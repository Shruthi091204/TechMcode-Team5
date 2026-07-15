import json
from typing import Any

from pydantic import BaseModel, Field

from contracts.schemas import Hypothesis
from rca.agents.client import MODEL_NAME, OUTPUT_CONFIG, THINKING_CONFIG, get_anthropic_client
from rca.agents.tools import query_changes, query_graph, query_logs, query_metrics

MAX_CONFIDENCE_NUDGE = 0.05


class SkepticEvaluation(BaseModel):
    verdict: str = Field(min_length=1)
    survived: bool
    confidence_adjustment: float = Field(ge=-0.5, le=0.2)
    transcript: str = Field(min_length=1)


def build_skeptic_system_prompt() -> str:
    return (
        "You are an adversarial Network Reliability Skeptic implementing STORM verification. "
        "Your sole job is to rigorously attack and try to disprove root-cause hypotheses. "
        "Use your tools to check for flaws: Is the config change on a different VLAN? Is there a valid routing path? "
        "Are interface error counters actually zero? "
        "If a hypothesis cannot be disproven and is supported by topology, "
        "mark it as survived with a positive confidence adjustment. "
        "If it relies on correlation without causal mechanism, mark it as failed with a negative adjustment."
    )


def extract_skeptic_evaluation(runner_result: Any) -> SkepticEvaluation:
    for message_item in reversed(runner_result.messages):
        if message_item.role != "assistant":
            continue
        for content_block in message_item.content:
            if content_block.type == "tool_use" and content_block.name == "SkepticEvaluation":
                return SkepticEvaluation.model_validate(content_block.input)
            if hasattr(content_block, "text") and "{" in content_block.text:
                try:
                    raw_json = json.loads(content_block.text)
                    return SkepticEvaluation.model_validate(raw_json)
                except (json.JSONDecodeError, ValueError):
                    continue
    raise ValueError("skeptic verification loop failed to produce structured SkepticEvaluation")


def clamp_confidence(current_confidence: float, adjustment: float) -> float:
    new_confidence = current_confidence + adjustment
    if new_confidence > 1.0:
        return 1.0
    if new_confidence < 0.0:
        return 0.0
    return round(new_confidence, 4)


def evaluate_single_hypothesis(hypothesis: Hypothesis, symptom: str) -> tuple[Hypothesis, str]:
    anthropic_client = get_anthropic_client()
    serialized_hypothesis = json.dumps(hypothesis.model_dump(mode="json"), indent=2)
    user_prompt = (
        f"Observed Symptom: {symptom}\n\n"
        f"Candidate Hypothesis to Attack:\n{serialized_hypothesis}\n\n"
        "Attempt to disprove this hypothesis using graph topology and metric queries. Return your verdict."
    )

    runner_result = anthropic_client.beta.messages.tool_runner(
        model=MODEL_NAME,
        max_tokens=2048,
        system=build_skeptic_system_prompt(),
        thinking=THINKING_CONFIG,
        output_config={
            "effort": OUTPUT_CONFIG["effort"],
            "format": {"type": "json_schema", "schema": SkepticEvaluation.model_json_schema()},
        },
        tools=[query_graph, query_metrics, query_logs, query_changes],
        messages=[{"role": "user", "content": user_prompt}],
    )

    evaluation = extract_skeptic_evaluation(runner_result)
    bounded_adjustment = max(-MAX_CONFIDENCE_NUDGE, min(MAX_CONFIDENCE_NUDGE, evaluation.confidence_adjustment))
    updated_confidence = clamp_confidence(hypothesis.confidence, bounded_adjustment)

    updated_hypothesis = Hypothesis(
        rank=hypothesis.rank,
        root_cause_component=hypothesis.root_cause_component,
        fault_type=hypothesis.fault_type,
        confidence=updated_confidence,
        causal_score=hypothesis.causal_score,
        topology_path=hypothesis.topology_path,
        evidence=hypothesis.evidence,
        counterfactual=hypothesis.counterfactual,
        skeptic_verdict=evaluation.verdict,
    )

    return updated_hypothesis, evaluation.transcript


def run_storm_verification(hypotheses: list[Hypothesis], symptom: str) -> tuple[list[Hypothesis], list[str]]:
    verified_hypotheses = []
    debate_transcripts = []
    for hypothesis in hypotheses:
        updated_hypothesis, transcript = evaluate_single_hypothesis(hypothesis, symptom)
        verified_hypotheses.append(updated_hypothesis)
        debate_transcripts.append(transcript)
    return verified_hypotheses, debate_transcripts