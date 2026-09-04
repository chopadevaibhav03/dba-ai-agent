from services.linux_health_service import get_linux_health
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.tool_registry import execute_tool, list_tools
from services.metrics_service import (
    get_latest_metrics,
    get_metrics_history,
)


app = FastAPI(
    title="DBA AI Agent",
    version="0.2.0-stage1",
)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


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


@app.get("/api/tools")
def tools():
    return {
        "ok": True,
        "tools": list_tools(),
    }

@app.get("/api/linux/health")
def linux_health():
    return get_linux_health()


@app.get("/api/tools/{tool_name:path}")
def run_tool(tool_name: str):
    try:
        return execute_tool(tool_name)

    except ValueError as exc:
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "error": str(exc),
            },
        )

    except PermissionError as exc:
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "error": str(exc),
            },
        )


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
