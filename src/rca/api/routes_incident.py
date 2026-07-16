import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from contracts.schemas import Hypothesis, IncidentReport
from rca.agents.investigator import investigate_incident

router = APIRouter()

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "incident_report.json"


class AnalyzeIncidentRequest(BaseModel):
    incident_id: str = Field(pattern=r"^INC-\d{4,}$")
    detected_at: datetime
    symptom: str = Field(min_length=1)
    symptom_component: str = Field(min_length=3)
    hypotheses: list[Hypothesis] = Field(min_length=1)


def load_fixture_incident() -> IncidentReport:
    raw_payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return IncidentReport.model_validate(raw_payload)


@router.get("/incidents/{incident_id}", response_model=IncidentReport)
def get_incident(incident_id: str) -> IncidentReport:
    fixture_incident = load_fixture_incident()
    if incident_id != fixture_incident.incident_id:
        raise HTTPException(status_code=404, detail=f"no incident found for {incident_id}")
    return fixture_incident


@router.post("/incidents/analyze", response_model=IncidentReport)
def analyze_incident(request_payload: AnalyzeIncidentRequest) -> IncidentReport:
    try:
        return investigate_incident(
            incident_id=request_payload.incident_id,
            detected_at=request_payload.detected_at,
            symptom=request_payload.symptom,
            symptom_component=request_payload.symptom_component,
            hypotheses=request_payload.hypotheses,
        )
    except Exception as execution_error:
        raise HTTPException(status_code=500, detail=str(execution_error)) from execution_error