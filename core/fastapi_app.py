from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config

from core.tool_registry import execute_tool, list_tools
from core.ai_orchestrator import run_ai, ai_status

from services.metrics_service import get_latest_metrics, get_metrics_history
from services.linux_health_service import get_linux_health
from services.oracle_health_service import get_oracle_health
from services.system_health_service import get_system_health


app = FastAPI(
    title="DBA AI Agent",
    version="0.2.0-stage1",
)


# ---------------------------------------------------------------------------
# Static UI
# ---------------------------------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    minutes: int = Field(
        default=5,
        ge=1,
        le=1440,
    )


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=10000,
    )


class ServiceActionRequest(BaseModel):
    service: str = Field(
        min_length=1,
        max_length=128,
    )
    action: str = Field(
        pattern="^(start|stop|restart|status)$",
    )


class LegacyActionRequest(BaseModel):
    action_key: str = Field(
        min_length=1,
        max_length=128,
    )


class ScanRequest(BaseModel):
    profile: str | None = None


class FixPreviewRequest(BaseModel):
    scan_id: str
    rule_id: str


# ---------------------------------------------------------------------------
# Root / health
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api")
def api_root():
    return {
        "ok": True,
        "service": "DBA AI Agent",
        "version": app.version,
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "fastapi",
        "version": app.version,
    }


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

@app.get("/api/tools")
def tools():
    return {
        "ok": True,
        "tools": list_tools(),
    }


@app.get("/api/tools/{tool_name:path}")
def run_tool(tool_name: str):
    try:
        return execute_tool(tool_name)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except PermissionError as exc:
        raise HTTPException(
            status_code=403,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Linux metrics
# ---------------------------------------------------------------------------

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
    limit: int = Query(
        default=200,
        ge=1,
        le=1000,
    )
):
    return get_metrics_history(limit)


# ---------------------------------------------------------------------------
# Health services
# ---------------------------------------------------------------------------

@app.get("/api/linux/health")
def linux_health():
    return get_linux_health()


@app.get("/api/oracle/health")
def oracle_health():
    return get_oracle_health()


@app.get("/api/system/health")
def system_health():
    return get_system_health()


# ---------------------------------------------------------------------------
# Analysis / reports
# ---------------------------------------------------------------------------

@app.post("/api/analyze")
def analyze_api(req: AnalyzeRequest):
    from analyzer import analyze
    from report import generate_and_save

    result = analyze(req.minutes)

    path = generate_and_save(result)

    result["_report_path"] = path

    return {
        "ok": True,
        "result": result,
    }


@app.get("/api/reports")
def reports_api():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT
                ts,
                severity,
                issue,
                root_cause,
                markdown_path
            FROM reports
            ORDER BY ts DESC
            LIMIT 20
            """
        ).fetchall()

    finally:
        conn.close()

    return {
        "ok": True,
        "reports": [
            dict(row)
            for row in rows
        ],
    }


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

@app.get("/api/services")
def services_api():
    from service_control import list_services

    return {
        "ok": True,
        "services": list_services(),
    }


@app.get("/api/services/{service_name}")
def service_status_api(service_name: str):
    from service_control import (
        service_exists,
        perform_action,
    )

    if not service_exists(service_name):
        raise HTTPException(
            status_code=404,
            detail="Unknown service",
        )

    return perform_action(
        service_name,
        "status",
    )


@app.post("/api/service/action")
def service_action_api(req: ServiceActionRequest):
    from service_control import (
        service_exists,
        perform_action,
    )

    if not service_exists(req.service):
        raise HTTPException(
            status_code=404,
            detail="Unknown service",
        )

    # status is read-only.
    if req.action == "status":
        return perform_action(
            req.service,
            "status",
        )

    # State-changing actions remain protected.
    return {
        "ok": False,
        "requires_approval": True,
        "service": req.service,
        "action": req.action,
        "message": (
            "State-changing service actions require "
            "the Stage 1 approval workflow."
        ),
    }


# ---------------------------------------------------------------------------
# OSCAP / Security
# ---------------------------------------------------------------------------

@app.get("/api/security/content")
def security_content():
    return execute_tool(
        "oscap.content"
    )


@app.post("/api/security/scan")
def security_scan(req: ScanRequest):
    return execute_tool(
        "oscap.scan",
        profile=req.profile,
    )


@app.get("/api/security/scan/{scan_id}")
def security_scan_status(scan_id: str):
    return execute_tool(
        "oscap.scan_status",
        scan_id=scan_id,
    )


@app.get("/api/security/findings")
def security_findings(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    )
):
    return execute_tool(
        "oscap.findings_history",
        limit=limit,
    )


@app.get("/api/security/report/{scan_id}")
def security_report(scan_id: str):
    result = execute_tool(
        "oscap.report",
        scan_id=scan_id,
    )

    if not result.get("ok"):
        raise HTTPException(
            status_code=404,
            detail=result.get(
                "error",
                "Report unavailable",
            ),
        )

    path = result.get("report_html_path")

    if not path or not Path(path).is_file():
        raise HTTPException(
            status_code=404,
            detail="Report file unavailable",
        )

    # Only serve reports from the configured scans directory.
    scans_dir = Path(
        config.SCANS_DIR
    ).resolve()

    report_path = Path(path).resolve()

    if scans_dir not in report_path.parents:
        raise HTTPException(
            status_code=403,
            detail="Invalid report path",
        )

    return HTMLResponse(
        report_path.read_text(
            encoding="utf-8"
        )
    )


@app.post("/api/security/fix")
def security_fix_preview(req: FixPreviewRequest):
    """
    Preview-only OSCAP remediation.

    Actual execution is deliberately disabled until
    the Stage 1 approval/risk/audit workflow exists.
    """

    result = execute_tool(
        "oscap.fix_preview",
        scan_id=req.scan_id,
        rule_id=req.rule_id,
    )

    if not result.get("ok"):
        raise HTTPException(
            status_code=404,
            detail=result.get(
                "error",
                "Finding not found",
            ),
        )

    return {
        **result,
        "requires_approval": True,
        "execution_allowed": False,
        "message": (
            "Fix execution is disabled until the "
            "controlled approval workflow is enabled."
        ),
    }


# ---------------------------------------------------------------------------
# Legacy action compatibility
# ---------------------------------------------------------------------------

@app.post("/api/actions/apply")
def actions_apply(req: LegacyActionRequest):
    return {
        "ok": False,
        "requires_approval": True,
        "action_key": req.action_key,
        "message": (
            "Direct remediation is disabled. "
            "Use the controlled approval workflow."
        ),
    }


# ---------------------------------------------------------------------------
# AI Orchestrator
# ---------------------------------------------------------------------------

@app.get("/api/ai/status")
def ai_status_api():
    """
    Return local AI configuration and tool-routing status.

    This endpoint does not perform inference.
    """

    try:
        return {
            "ok": True,
            **ai_status(),
        }

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(exc),
            },
        )


@app.post("/api/chat")
def chat_api(req: ChatRequest):
    """
    Send a user request to the Stage 1 AI orchestrator.

    Flow:

        User
          |
          v
        FastAPI
          |
          v
        Domain Router
          |
          v
        Ollama
          |
          v
        Registered read-only tools
          |
          v
        Ollama final response

    The AI cannot execute arbitrary shell commands,
    arbitrary SQL or remediation actions.
    """

    try:
        result = run_ai(
            req.message
        )

        if not result.get("ok"):
            return JSONResponse(
                status_code=502,
                content={
                    "ok": False,
                    "ai_connected": False,
                    "result": result,
                },
            )

        return {
            "ok": True,
            "ai_connected": True,
            "result": result,
        }

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "ai_connected": True,
                "error": str(exc),
            },
        )