from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from services.metrics_service import (
    get_latest_metrics,
    get_metrics_history,
)


app = FastAPI(
    title="DBA AI Agent",
    version="0.2.0-stage1",
)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "fastapi",
        "version": "0.2.0-stage1",
    }


@app.get("/api")
def api_root():
    return {
        "ok": True,
        "service": "DBA AI Agent",
        "version": "0.2.0-stage1",
    }


@app.get("/api/metrics/latest")
def metrics_latest():
    result = get_latest_metrics()

    if not result["ok"]:
        return JSONResponse(
            status_code=404,
            content=result,
        )

    return result


@app.get("/api/metrics/history")
def metrics_history(
    limit: int = Query(default=200, ge=1, le=1000)
):
    return get_metrics_history(limit) 