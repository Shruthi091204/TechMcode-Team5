import json
from pathlib import Path

from pydantic import BaseModel

from rca.audit.chain import DEFAULT_AUDIT_LOG_PATH, GENESIS_HASH, compute_entry_hash


class AuditVerificationResult(BaseModel):
    is_valid: bool
    total_events: int
    failed_at_index: int | None
    failure_reason: str | None


def verify_audit_chain(file_path: Path = DEFAULT_AUDIT_LOG_PATH) -> AuditVerificationResult:
    if not file_path.exists():
        return AuditVerificationResult(
            is_valid=True,
            total_events=0,
            failed_at_index=None,
            failure_reason="Audit log file does not exist yet",
        )

    raw_lines = file_path.read_text(encoding="utf-8").strip().splitlines()
    if not raw_lines:
        return AuditVerificationResult(
            is_valid=True,
            total_events=0,
            failed_at_index=None,
            failure_reason=None,
        )

    expected_prev_hash = GENESIS_HASH
    for index, line in enumerate(raw_lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return AuditVerificationResult(
                is_valid=False,
                total_events=len(raw_lines),
                failed_at_index=index,
                failure_reason=f"Corrupted JSON formatting at line {index + 1}",
            )

        recorded_prev_hash = str(record.get("prev_hash", ""))
        recorded_hash = str(record.get("hash", ""))
        timestamp_iso = str(record.get("timestamp", ""))
        event_type = str(record.get("event_type", ""))
        payload_json = json.dumps(record.get("payload", {}), sort_keys=True)

        if recorded_prev_hash != expected_prev_hash:
            return AuditVerificationResult(
                is_valid=False,
                total_events=len(raw_lines),
                failed_at_index=index,
                failure_reason=(
                    f"Chain broken at line {index + 1}: "
                    f"expected prev_hash {expected_prev_hash}, found {recorded_prev_hash}"
                ),
            )

        recomputed_hash = compute_entry_hash(recorded_prev_hash, timestamp_iso, event_type, payload_json)
        if recorded_hash != recomputed_hash:
            return AuditVerificationResult(
                is_valid=False,
                total_events=len(raw_lines),
                failed_at_index=index,
                failure_reason=f"Tamper detected at line {index + 1}: hash mismatch",
            )

        expected_prev_hash = recorded_hash

    return AuditVerificationResult(
        is_valid=True,
        total_events=len(raw_lines),
        failed_at_index=None,
        failure_reason=None,
    )