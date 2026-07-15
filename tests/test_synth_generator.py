from __future__ import annotations

from contracts.schemas import FaultType
from rca.pipeline import build_incident_from_data, load_topology
from rca.synth.generator import generate_incident


def _recovers(root: str, fault: FaultType) -> bool:
    topology = load_topology()
    incident = generate_incident(topology, root, fault, seed=1)
    assert incident is not None
    report = build_incident_from_data(
        topology,
        incident.telemetry,
        incident.logs,
        incident.alerts,
        incident.config_changes,
    )
    return report.hypotheses[0].root_cause_component == root


def test_generator_recovers_config_pool_exhaustion() -> None:
    assert _recovers("db-01", FaultType.CONFIG_POOL_EXHAUSTION)


def test_generator_recovers_capacity_exhaustion() -> None:
    assert _recovers("cache-01", FaultType.CAPACITY_EXHAUSTION)


def test_generator_recovers_bad_config_push() -> None:
    assert _recovers("app-03", FaultType.BAD_CONFIG_PUSH)


def test_generated_incident_is_well_formed() -> None:
    topology = load_topology()
    incident = generate_incident(topology, "db-01", FaultType.CONFIG_POOL_EXHAUSTION, seed=0)
    assert incident is not None
    assert incident.path[0] == "db-01"
    assert incident.path[-1] == incident.symptom
    assert incident.symptom.startswith("web")
    assert len(incident.telemetry) == 30 * 32


def test_generator_is_deterministic() -> None:
    topology = load_topology()
    first = generate_incident(topology, "app-03", FaultType.BAD_CONFIG_PUSH, seed=3)
    second = generate_incident(topology, "app-03", FaultType.BAD_CONFIG_PUSH, seed=3)
    assert first is not None and second is not None
    assert [point.model_dump() for point in first.telemetry] == [point.model_dump() for point in second.telemetry]
