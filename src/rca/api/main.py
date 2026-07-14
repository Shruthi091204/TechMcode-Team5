from fastapi import FastAPI

from rca.api.routes_incident import router as incident_router

app = FastAPI(title="Network Anomaly Root-Cause Assistant", version="1.0.0")
app.include_router(incident_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
