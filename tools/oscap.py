"""Tool Registry adapters for the existing OpenSCAP engine.

The underlying oscap_tool.py remains the scan engine. These adapters expose
safe, deterministic operations to the central Tool Registry.
"""
from typing import Optional

import config
import oscap_tool


def content() -> dict:
    return {
        "content_path": config.OSCAP_CONTENT,
        "default_profile": config.OSCAP_DEFAULT_PROFILE,
        "scans_dir": config.SCANS_DIR,
    }


def scan(profile: Optional[str] = None) -> dict:
    scan_id = oscap_tool.start_scan(profile=profile)
    return {
        "ok": True,
        "scan_id": scan_id,
        "profile": profile or config.OSCAP_DEFAULT_PROFILE,
        "status": "queued",
    }


def scan_status(scan_id: str) -> dict:
    return oscap_tool.get_scan_status(scan_id)


def findings_history(limit: int = 100) -> list:
    limit = max(1, min(int(limit), 500))
    return oscap_tool.get_findings_history(limit)


def report(scan_id: str) -> dict:
    status = oscap_tool.get_scan_status(scan_id)
    if not status.get("ok"):
        return status

    report_path = status.get("report_html_path")
    if not report_path:
        return {
            "ok": False,
            "error": "Report is not available yet",
            "status": status.get("status"),
        }

    return {
        "ok": True,
        "scan_id": scan_id,
        "report_html_path": report_path,
        "status": status.get("status"),
    }


def fix_preview(scan_id: str, rule_id: str) -> dict:
    status = oscap_tool.get_scan_status(scan_id)
    if not status.get("ok"):
        return status

    for finding in status.get("findings", []):
        if finding.get("rule_id") == rule_id:
            return {
                "ok": True,
                "scan_id": scan_id,
                "rule_id": rule_id,
                "fix_script": finding.get("fix_script", ""),
                "fix_text": finding.get("fix_text", ""),
            }

    # Some versions store findings under parsed/summary structures.
    for finding in (status.get("parsed") or {}).get("fails", []):
        if finding.get("rule_id") == rule_id:
            return {
                "ok": True,
                "scan_id": scan_id,
                "rule_id": rule_id,
                "fix_script": finding.get("fix_script", ""),
                "fix_text": finding.get("fix_text", ""),
            }

    return {
        "ok": False,
        "error": "Rule not found in scan",
        "scan_id": scan_id,
        "rule_id": rule_id,
    }


OSCAP_TOOLS = {
    "oscap.content": {
        "description": "Return configured OpenSCAP content and default profile.",
        "function": content,
        "read_only": True,
        "category": "oscap",
    },
    "oscap.scan": {
        "description": "Start a background OpenSCAP assessment using the configured RHEL content.",
        "function": scan,
        "read_only": True,
        "category": "oscap",
    },
    "oscap.scan_status": {
        "description": "Return status and results for an OpenSCAP scan.",
        "function": scan_status,
        "read_only": True,
        "category": "oscap",
    },
    "oscap.findings_history": {
        "description": "Return previously observed OpenSCAP findings.",
        "function": findings_history,
        "read_only": True,
        "category": "oscap",
    },
    "oscap.report": {
        "description": "Return the generated HTML report path for an OpenSCAP scan.",
        "function": report,
        "read_only": True,
        "category": "oscap",
    },
    "oscap.fix_preview": {
        "description": "Preview the vetted OpenSCAP remediation script for a finding without executing it.",
        "function": fix_preview,
        "read_only": True,
        "category": "oscap",
    },
}
