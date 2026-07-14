import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from contracts.schemas import IncidentReport

router = APIRouter()

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "incident_report.json"


@lru_cache(maxsize=1)
def load_fixture_incident() -> IncidentReport:
    raw_payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return IncidentReport.model_validate(raw_payload)


@router.get("/incidents/{incident_id}", response_model=IncidentReport)
def get_incident(incident_id: str) -> IncidentReport:
    fixture_incident = load_fixture_incident()
    if incident_id != fixture_incident.incident_id:
        raise HTTPException(status_code=404, detail=f"no incident found for {incident_id}")
    return fixture_incident
