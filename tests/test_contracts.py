from __future__ import annotations

import csv
import json
from collections import defaultdict, deque
from pathlib import Path

import pytest
from pydantic import ValidationError

from contracts.schemas import (
    AlertRecord,
    ConfigChange,
    EvidenceItem,
    GroundTruth,
    Hypothesis,
    LogRecord,
    RelationKind,
    TelemetryPoint,
    Topology,
)

FIXTURES = Path(__file__).resolve().parents[1] / "contracts" / "fixtures"


def read_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def read_jsonl(name: str) -> list[dict]:
    lines = (FIXTURES / name).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def read_csv(name: str) -> list[dict]:
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="session")
def topology() -> Topology:
    return Topology.model_validate(read_json("topology.json"))


@pytest.fixture(scope="session")
def ground_truth() -> GroundTruth:
    return GroundTruth.model_validate(read_json("ground_truth.json"))


@pytest.fixture(scope="session")
def dependency_map(topology: Topology) -> dict[str, set[str]]:
    edges: dict[str, set[str]] = defaultdict(set)
    for edge in topology.dependencies:
        if edge.relation is RelationKind.DEPENDS_ON:
            edges[edge.source_id].add(edge.target_id)
    return edges


def impact_path(dependency_map: dict[str, set[str]], cause: str, symptom: str) -> list[str] | None:
    frontier: deque[list[str]] = deque([[symptom]])
    visited = {symptom}
    while frontier:
        trail = frontier.popleft()
        if trail[-1] == cause:
            return list(reversed(trail))
        for dependency in sorted(dependency_map[trail[-1]]):
            if dependency in visited:
                continue
            visited.add(dependency)
            frontier.append([*trail, dependency])
    return None


def test_topology_validates(topology: Topology) -> None:
    assert len(topology.components) == 30
    assert len(topology.dependencies) == 96


def test_every_telemetry_row_validates() -> None:
    rows = read_csv("telemetry.csv")
    assert len(rows) == 930
    for row in rows:
        TelemetryPoint.model_validate(row)


def test_every_log_validates() -> None:
    for record in read_jsonl("logs.jsonl"):
        LogRecord.model_validate(record)


def test_every_alert_validates() -> None:
    for record in read_jsonl("alerts.jsonl"):
        AlertRecord.model_validate(record)


def test_every_config_change_validates() -> None:
    for record in read_jsonl("config_changes.jsonl"):
        ConfigChange.model_validate(record)


def test_ground_truth_validates(ground_truth: GroundTruth) -> None:
    assert ground_truth.root_cause_component == "db-01"
    assert ground_truth.symptom_component == "web-02"


def test_connection_ceiling_matches_the_config_change() -> None:
    changes = {record["change_id"]: record for record in read_jsonl("config_changes.jsonl")}
    configured_ceiling = changes["CHG-4212"]["after"]["max_connections"]
    database_rows = [row for row in read_csv("telemetry.csv") if row["component_id"] == "db-01"]
    saturated = {int(row["connection_count"]) for row in database_rows[13:]}
    assert saturated == {configured_ceiling}


def test_network_tier_is_exonerated_by_zero_packet_loss() -> None:
    network = {"core-sw-01", "tor-sw-01", "tor-sw-02", "tor-sw-03", "fw-01"}
    losses = {float(row["packet_loss_pct"]) for row in read_csv("telemetry.csv") if row["component_id"] in network}
    assert losses == {0.0}


def test_root_cause_reaches_the_symptom(dependency_map, ground_truth: GroundTruth) -> None:
    path = impact_path(dependency_map, ground_truth.root_cause_component, ground_truth.symptom_component)
    assert path == ground_truth.propagation_path


@pytest.mark.parametrize("decoy_id", ["web-05", "cache-02"])
def test_decoys_have_no_impact_path(dependency_map, ground_truth: GroundTruth, decoy_id: str) -> None:
    assert impact_path(dependency_map, decoy_id, ground_truth.symptom_component) is None


def test_decoys_are_declared_in_ground_truth(ground_truth: GroundTruth) -> None:
    declared = {decoy.component_id for decoy in ground_truth.decoys}
    assert declared == {"web-05", "cache-02"}


def test_temporal_decoy_lands_closer_to_onset_than_the_true_cause(ground_truth: GroundTruth) -> None:
    records = read_jsonl("config_changes.jsonl")
    changes = {record["change_id"]: ConfigChange.model_validate(record) for record in records}
    true_cause_gap = (ground_truth.onset_at - changes["CHG-4212"].ts).total_seconds()
    decoy_gap = (ground_truth.onset_at - changes["CHG-4213"].ts).total_seconds()
    assert decoy_gap < true_cause_gap


def test_impact_path_is_deterministic(dependency_map, ground_truth: GroundTruth) -> None:
    walks = {
        tuple(impact_path(dependency_map, ground_truth.root_cause_component, ground_truth.symptom_component) or [])
        for _ in range(25)
    }
    assert len(walks) == 1


def test_uncited_observation_is_rejected() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(kind="confirmed", statement="the database caused it", source="metric")


def test_missing_evidence_needs_no_citation() -> None:
    item = EvidenceItem(kind="missing", statement="no slow-query log for db-01", source="log")
    assert item.ref is None


def test_hypothesis_path_must_start_at_the_named_cause() -> None:
    citation = EvidenceItem(kind="confirmed", statement="ceiling reached", source="metric", ref="CHG-4212")
    with pytest.raises(ValidationError):
        Hypothesis(
            rank=1,
            root_cause_component="db-01",
            fault_type="config_pool_exhaustion",
            confidence=0.9,
            causal_score=0.9,
            topology_path=["web-05", "web-02"],
            evidence=[citation],
        )
