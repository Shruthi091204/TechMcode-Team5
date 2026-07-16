from fastapi.testclient import TestClient

from rca.api import routes_knowledge
from rca.api.main import app
from rca.knowledge import retrieval


def test_runbook_corpus_loads_with_required_fields():
    runbooks = retrieval.load_runbooks()
    assert len(runbooks) >= 15
    for entry in runbooks:
        assert entry["id"]
        assert entry["title"]
        assert entry["applies_to"]
        assert entry["diagnostic_steps"]
        assert entry["remediation"]


def test_past_incidents_corpus_loads_with_required_fields():
    incidents = retrieval.load_past_incidents()
    assert len(incidents) >= 5
    for entry in incidents:
        assert entry["id"]
        assert entry["root_cause"]
        assert entry["fault_type"]


def test_runbook_document_includes_title_keywords_and_steps():
    entry = {
        "title": "Pool exhaustion",
        "applies_to": ["database"],
        "diagnostic_steps": ["show processlist"],
        "remediation": ["roll back"],
    }
    document = retrieval._runbook_document(entry)
    assert "Pool exhaustion" in document
    assert "database" in document
    assert "show processlist" in document
    assert "roll back" in document


def test_incident_metadata_carries_root_cause_and_fault_type():
    entry = {
        "id": "PAST-1",
        "title": "T",
        "root_cause": "db-01",
        "fault_type": "config_pool_exhaustion",
        "impact_path": "db-01 -> web-02",
    }
    metadata = retrieval._incident_metadata(entry)
    assert metadata["root_cause"] == "db-01"
    assert metadata["fault_type"] == "config_pool_exhaustion"


def test_retrieve_runbooks_falls_back_to_empty_on_failure(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("embedder unavailable")

    monkeypatch.setattr(retrieval, "_embed", _boom)
    monkeypatch.setattr(retrieval, "_get_chroma_client", _boom)
    assert retrieval.retrieve_runbooks("database connection pool exhaustion") == []


def test_retrieve_similar_incidents_falls_back_to_empty_on_failure(monkeypatch):
    def _boom(*args, **kwargs):
        raise RuntimeError("chroma unavailable")

    monkeypatch.setattr(retrieval, "_get_chroma_client", _boom)
    assert retrieval.retrieve_similar_incidents("db pool exhausted on db-01") == []


def test_knowledge_endpoint_maps_retrieval_output(monkeypatch):
    monkeypatch.setattr(
        routes_knowledge,
        "retrieve_runbooks",
        lambda query, k=3: [{"id": "RB-DB-POOL-01", "title": "Pool", "snippet": "s", "score": 0.9}],
    )
    monkeypatch.setattr(routes_knowledge, "retrieve_similar_incidents", lambda query, k=2: [])
    response = TestClient(app).post("/knowledge/retrieve", json={"query": "db pool exhaustion", "k": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["runbooks"][0]["id"] == "RB-DB-POOL-01"
    assert body["similar_incidents"] == []
