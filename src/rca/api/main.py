import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rca.api.routes_analyze import router as analyze_router
from rca.api.routes_audit import router as audit_router
from rca.api.routes_incident import router as incident_router
from rca.api.routes_knowledge import router as knowledge_router
from rca.api.routes_replay import router as replay_router
from rca.api.routes_stats import router as stats_router
from rca.api.routes_topology import router as topology_router

load_dotenv()

app = FastAPI(title="Network Anomaly Root-Cause Assistant", version="1.0.0")

_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allowed_origins.strip() == "*" else [o.strip() for o in _allowed_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incident_router)
app.include_router(topology_router)
app.include_router(replay_router)
app.include_router(audit_router)
app.include_router(analyze_router)
app.include_router(stats_router)
app.include_router(knowledge_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}