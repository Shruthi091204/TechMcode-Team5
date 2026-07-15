import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from pydantic import BaseModel, Field

from contracts.schemas import Hypothesis
from rca.agents.runner import run_agent_loop
from rca.agents.tools import TOOL_SCHEMAS, execute_tool

MAX_CONFIDENCE_NUDGE = 0.05
SKEPTIC_MAX_TOKENS = 3000
MAX_SKEPTIC_WORKERS = 8


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


def clamp_confidence(current_confidence: float, adjustment: float) -> float:
    new_confidence = current_confidence + adjustment
    if new_confidence > 1.0:
        return 1.0
    if new_confidence < 0.0:
        return 0.0
    return round(new_confidence, 4)


def evaluate_single_hypothesis(hypothesis: Hypothesis, symptom: str) -> tuple[Hypothesis, str]:
    serialized_hypothesis = json.dumps(hypothesis.model_dump(mode="json"), indent=2)
    user_prompt = (
        f"Observed Symptom: {symptom}\n\n"
        f"Candidate Hypothesis to Attack:\n{serialized_hypothesis}\n\n"
        "Attempt to disprove this hypothesis using graph topology and metric queries. Return your verdict."
    )

    evaluation = run_agent_loop(
        system_prompt=build_skeptic_system_prompt(),
        user_prompt=user_prompt,
        tool_schemas=TOOL_SCHEMAS,
        execute=execute_tool,
        response_model=SkepticEvaluation,
        max_tokens=SKEPTIC_MAX_TOKENS,
    )

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


def rerank_verified(hypotheses: list[Hypothesis]) -> list[Hypothesis]:
    if not hypotheses:
        return []
    deterministic_leader = min(hypotheses, key=lambda item: item.rank)
    by_confidence = sorted(hypotheses, key=lambda item: (-item.confidence, item.rank))
    ordered = [deterministic_leader] + [item for item in by_confidence if item is not deterministic_leader]
    return [item.model_copy(update={"rank": position}) for position, item in enumerate(ordered, start=1)]


def run_storm_verification(hypotheses: list[Hypothesis], symptom: str) -> tuple[list[Hypothesis], list[str]]:
    if not hypotheses:
        return [], []
    evaluate = partial(evaluate_single_hypothesis, symptom=symptom)
    worker_count = min(len(hypotheses), MAX_SKEPTIC_WORKERS)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        outcomes = list(executor.map(evaluate, hypotheses))
    transcript_by_component = {hypothesis.root_cause_component: transcript for hypothesis, transcript in outcomes}
    verified_hypotheses = rerank_verified([hypothesis for hypothesis, _ in outcomes])
    debate_transcripts = [
        transcript_by_component[hypothesis.root_cause_component] for hypothesis in verified_hypotheses
    ]
    return verified_hypotheses, debate_transcripts
