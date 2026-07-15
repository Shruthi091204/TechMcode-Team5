from __future__ import annotations

from rca.agents.skeptic import rerank_verified
from rca.pipeline import run_reference

TRUE_CAUSE = "db-01"


def _apply_nudges(hypotheses, adjustments):
    adjusted = []
    for hypothesis in hypotheses:
        delta = adjustments.get(hypothesis.root_cause_component, 0.0)
        new_confidence = round(hypothesis.confidence + delta, 4)
        adjusted.append(hypothesis.model_copy(update={"confidence": new_confidence}))
    return adjusted


def test_rerank_pins_leader_and_orders_tail_by_confidence() -> None:
    nudged = _apply_nudges(run_reference(), {"cache-01": -0.05, "app-03": 0.05})
    reranked = rerank_verified(nudged)

    assert reranked[0].root_cause_component == TRUE_CAUSE
    assert [h.rank for h in reranked] == list(range(1, len(reranked) + 1))

    tail_confidence = [h.confidence for h in reranked[1:]]
    assert tail_confidence == sorted(tail_confidence, reverse=True)

    order = [h.root_cause_component for h in reranked]
    assert order.index("app-03") < order.index("cache-01")


def test_rerank_pins_leader_even_when_outscored() -> None:
    base = run_reference()
    lowest_rank = max(h.rank for h in base)
    hacked = [
        h.model_copy(update={"confidence": 0.99}) if h.rank == lowest_rank else h
        for h in base
    ]
    reranked = rerank_verified(hacked)

    assert reranked[0].root_cause_component == TRUE_CAUSE
    assert [h.rank for h in reranked] == list(range(1, len(reranked) + 1))


def test_rerank_handles_empty_input() -> None:
    assert rerank_verified([]) == []
