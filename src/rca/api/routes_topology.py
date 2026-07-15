import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException

from contracts.schemas import Topology

router = APIRouter()

FIXTURE_PATH = Path(__file__).resolve().parents[3] / "contracts" / "fixtures" / "topology.json"


@lru_cache(maxsize=1)
def load_fixture_topology() -> Topology:
    if not FIXTURE_PATH.exists():
        raise HTTPException(status_code=404, detail="topology fixture file not found")
    raw_payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return Topology.model_validate(raw_payload)


@router.get("/topology", response_model=Topology)
def get_topology() -> Topology:
    return load_fixture_topology()