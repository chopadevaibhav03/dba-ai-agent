from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(
    title="DBA AI Agent",
    description="Local AI-powered Linux and Oracle DBA automation platform",
    version="0.2.0-stage1",
)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "dba-ai-agent",
        "framework": "FastAPI",
        "stage": "stage-1-foundation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api")
def api_root():
    return {
        "ok": True,
        "service": "DBA AI Agent",
        "api": "FastAPI",
    }
