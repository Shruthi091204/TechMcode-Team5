from fastapi import APIRouter
from pydantic import BaseModel

from rca.audit.chain import DEFAULT_AUDIT_LOG_PATH, ensure_audit_directory
from rca.stats.store import read_usage_stats

router = APIRouter()


class UsageStats(BaseModel):
    incidents_analyzed: int
    nodes_analyzed: int
    audit_events: int


def _audit_event_count() -> int:
    ensure_audit_directory(DEFAULT_AUDIT_LOG_PATH)
    content = DEFAULT_AUDIT_LOG_PATH.read_text(encoding="utf-8").strip()
    if not content:
        return 0
    return len(content.splitlines())


@router.get("/stats", response_model=UsageStats)
def get_usage_stats() -> UsageStats:
    stats = read_usage_stats()
    return UsageStats(
        incidents_analyzed=stats["incidents_analyzed"],
        nodes_analyzed=stats["nodes_analyzed"],
        audit_events=_audit_event_count(),
    )
