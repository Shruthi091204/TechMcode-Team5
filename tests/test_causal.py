from __future__ import annotations

from contracts.schemas import Hypothesis
from rca.causal.candidate_set import candidate_causes
from rca.graph.twin import TopologyTwin
from rca.pipeline import (
    derive_anomalies,
    load_telemetry_frame,
    load_topology,
    run_reference,
)

SYMPTOM = "web-02"
TRUE_CAUSE = "db-01"
TRUE_PATH = ["db-01", "app-03", "web-02"]
DECOYS = {"web-05", "cache-02"}


def _twin() -> TopologyTwin:
    return TopologyTwin(load_topology())


def test_impact_path_matches_ground_truth() -> None:
    assert _twin().impact_path(TRUE_CAUSE, SYMPTOM) == TRUE_PATH


def test_impact_path_is_deterministic() -> None:
    twin = _twin()
    walks = {tuple(twin.impact_path(TRUE_CAUSE, SYMPTOM) or []) for _ in range(30)}
    assert len(walks) == 1


def test_decoys_have_no_path() -> None:
    twin = _twin()
    for decoy in DECOYS:
        assert twin.impact_path(decoy, SYMPTOM) is None


def test_candidate_filter_admits_cause_rejects_decoys() -> None:
    twin = _twin()
    telemetry = load_telemetry_frame()
    anomalies = derive_anomalies(load_topology(), telemetry)
    candidates = candidate_causes(twin, SYMPTOM, anomalies)
    assert TRUE_CAUSE in candidates
    assert DECOYS.isdisjoint(candidates)


def test_pipeline_ranks_true_cause_first() -> None:
    hypotheses = run_reference()
    assert hypotheses[0].root_cause_component == TRUE_CAUSE
    assert hypotheses[0].topology_path == TRUE_PATH
    assert hypotheses[0].counterfactual is not None


def test_pipeline_surfaces_decoys_as_rejected() -> None:
    hypotheses = run_reference()
    named = {h.root_cause_component for h in hypotheses}
    assert DECOYS.issubset(named)
    for hypothesis in hypotheses:
        if hypothesis.root_cause_component in DECOYS:
            missing = [e for e in hypothesis.evidence if e.kind.value == "missing"]
            assert any("no dependency path" in e.statement.lower() for e in missing)


def test_every_hypothesis_satisfies_contract() -> None:
    for hypothesis in run_reference():
        Hypothesis.model_validate(hypothesis.model_dump())


def test_confirmed_evidence_is_cited() -> None:
    for hypothesis in run_reference():
        for item in hypothesis.evidence:
            if item.kind.value in {"confirmed", "correlated"}:
                assert item.ref is not None
