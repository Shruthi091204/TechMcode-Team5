import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from rca.audit.chain import DEFAULT_AUDIT_LOG_PATH
from rca.audit.verify import AuditVerificationResult, verify_audit_chain

router = APIRouter()


class AuditLogRecord(BaseModel):
    timestamp: str
    event_type: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str


class IncidentAuditTrail(BaseModel):
    incident_id: str = Field(min_length=1)
    total_records: int
    records: list[AuditLogRecord]


def read_audit_entries(file_path: Path = DEFAULT_AUDIT_LOG_PATH) -> list[AuditLogRecord]:
    if not file_path.exists():
        return []
    raw_lines = file_path.read_text(encoding="utf-8").strip().splitlines()
    records = []
    for line in raw_lines:
        if not line.strip():
            continue
        try:
            records.append(AuditLogRecord.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError):
            continue
    return records


@router.get("/audit/verify", response_model=AuditVerificationResult)
def verify_entire_audit_trail() -> AuditVerificationResult:
    return verify_audit_chain()


@router.get("/audit/{incident_id}", response_model=IncidentAuditTrail)
def get_incident_audit_trail(incident_id: str) -> IncidentAuditTrail:
    all_records = read_audit_entries()
    matching_records = [
        record for record in all_records
        if str(record.payload.get("incident_id", "")) == incident_id
    ]
    if not matching_records and all_records:
        matching_records = all_records

    return IncidentAuditTrail(
        incident_id=incident_id,
        total_records=len(matching_records),
        records=matching_records,
    )


@router.get("/audit/{incident_id}/verify", response_model=AuditVerificationResult)
def verify_incident_audit_trail(incident_id: str) -> AuditVerificationResult:
    return verify_audit_chain()