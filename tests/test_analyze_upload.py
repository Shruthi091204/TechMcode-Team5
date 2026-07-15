from __future__ import annotations

from rca.pipeline import (
    _telemetry_points,
    build_incident_from_data,
    build_live_incident,
    load_alerts,
    load_changes,
    load_logs,
    load_telemetry_frame,
    load_topology,
)

TRUE_CAUSE = "db-01"
TRUE_PATH = ["db-01", "app-03", "web-02"]
SYMPTOM = "web-02"


def _uploaded_incident():
    return build_incident_from_data(
        load_topology(),
        _telemetry_points(load_telemetry_frame()),
        load_logs(),
        load_alerts(),
        load_changes(),
    )


def test_uploaded_data_reproduces_golden_ranking() -> None:
    incident = _uploaded_incident()
    assert incident.hypotheses[0].root_cause_component == TRUE_CAUSE
    assert incident.hypotheses[0].topology_path == TRUE_PATH
    assert incident.symptom_component == SYMPTOM


def test_uploaded_path_matches_fixture_path() -> None:
    uploaded = _uploaded_incident()
    fixture = build_live_incident()
    assert [h.root_cause_component for h in uploaded.hypotheses] == [
        h.root_cause_component for h in fixture.hypotheses
    ]


def test_uploaded_incident_id_is_contract_valid() -> None:
    incident = build_incident_from_data(
        load_topology(),
        _telemetry_points(load_telemetry_frame()),
        load_logs(),
        load_alerts(),
        load_changes(),
        incident_id="INC-90210",
    )
    assert incident.incident_id == "INC-90210"
    assert _uploaded_incident().incident_id.startswith("INC-")
