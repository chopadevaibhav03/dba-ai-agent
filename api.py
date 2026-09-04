"""
Flask API for the OS monitoring agent web UI.

Serves the static frontend (static/) directly and exposes JSON endpoints
under /api/* for metrics, analysis, reports, and prompt-driven service
control. Meant to run behind Gunicorn, with Apache reverse-proxying to it.

Run for local testing:
    python3 api.py            # dev server on :8000

Run for production (what systemd will do):
    gunicorn -w 2 -b 127.0.0.1:8000 api:app
"""

import json
import os
import sqlite3

from flask import Flask, jsonify, request, send_from_directory

import config
from chat_agent import parse_and_respond
from analyzer import analyze
from automation import WHITELIST, execute
from report import generate_and_save
from service_control import perform_action, list_services, service_exists
import oscap_tool

app = Flask(__name__, static_folder="static", static_url_path="")


# ---------- static frontend ----------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------- metrics ----------

@app.route("/api/metrics/latest")
def api_metrics_latest():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM metrics ORDER BY ts DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "No metrics yet"}), 404
    sample = dict(row)
    sample["disk"] = json.loads(sample.pop("disk_json") or "{}")
    return jsonify({"ok": True, "sample": sample})


@app.route("/api/metrics/history")
def api_metrics_history():
    limit = min(int(request.args.get("limit", 200)), 1000)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT ts, cpu_percent, mem_percent, swap_percent FROM metrics ORDER BY ts DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    samples = [dict(r) for r in rows][::-1]  # oldest first for charting
    return jsonify({"ok": True, "samples": samples})


# ---------- analysis / reports ----------

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    minutes = int((request.json or {}).get("minutes", 5))
    result = analyze(minutes)
    path = generate_and_save(result)
    result["_report_path"] = path
    return jsonify({"ok": True, "result": result})


@app.route("/api/reports")
def api_reports():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT ts, severity, issue, root_cause, markdown_path FROM reports ORDER BY ts DESC LIMIT 20"
    ).fetchall()
    conn.close()
    return jsonify({"ok": True, "reports": [dict(r) for r in rows]})


@app.route("/api/actions/apply", methods=["POST"])
def api_apply_action():
    """Apply a whitelisted remediation action recommended by the analyzer."""
    data = request.json or {}
    key = data.get("action_key")
    if key not in WHITELIST:
        return jsonify({"ok": False, "error": f"'{key}' is not a whitelisted action"}), 400
    result = execute(key, confirm=True)
    return jsonify(result)


# ---------- prompt-driven service control ----------

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Handle a free-text prompt via the agent (regex fast path or full
    tool-calling conversation). Read-only questions get an answer directly.
    Anything state-changing comes back as a confirm_* type for the frontend
    to re-submit via /api/service/action or /api/actions/apply.
    """
    message = (request.json or {}).get("message", "").strip()
    if not message:
        return jsonify({"ok": False, "error": "Empty message"}), 400

    result = parse_and_respond(message)

    # --- regex fast-path shapes (intent/action/service) ---
    if "intent" in result:
        intent = result
        service = intent.get("service")
        action = intent.get("action")

        if intent["intent"] == "start_security_scan":
            scan_id = oscap_tool.start_scan()
            return jsonify({
                "ok": True, "type": "scan_started", "scan_id": scan_id,
                "reply": f"Started a security scan (profile: {config.OSCAP_DEFAULT_PROFILE}). "
                         "This takes a few minutes -- check the Security tab for results.",
            })

        if intent["intent"] == "list_services":
            active = list_services(active_only=True)
            active_names = [s["unit"] for s in active[:25]]
            reply = f"Running services: {', '.join(active_names)}" if active_names else "No services currently active/running."
            return jsonify({"ok": True, "type": "info", "reply": reply})

        if intent["intent"] == "service_action" and service and action:
            if not service_exists(service):
                return jsonify({"ok": True, "type": "error", "reply": f"I don't see a service called '{service}' on this system."})
            if action == "status":
                res = perform_action(service, "status")
                reply = (f"`{res['service']}` is {res['state']}." if res.get("ok")
                          else f"Couldn't check status: {res.get('error')}")
                return jsonify({"ok": True, "type": "info", "reply": reply})
            return jsonify({
                "ok": True, "type": "confirm_service",
                "service": service, "action": action,
                "reply": intent.get("reply") or f"About to {action} {service}. Confirm?",
            })

        return jsonify({"ok": True, "type": "info", "reply": intent.get("reply") or "Not sure how to help with that."})

    # --- tool-calling agent shapes (type already set) ---
    return jsonify({"ok": True, **result})


@app.route("/api/service/action", methods=["POST"])
def api_service_action():
    """Actually execute a service action. Requires confirm=true from the client."""
    data = request.json or {}
    service = data.get("service")
    action = data.get("action")
    confirm = bool(data.get("confirm"))

    if not service or not action:
        return jsonify({"ok": False, "error": "service and action are required"}), 400

    result = perform_action(service, action, confirm=confirm)
    return jsonify(result)


@app.route("/api/service/list")
def api_service_list():
    active_only = request.args.get("active_only", "false").lower() == "true"
    return jsonify({"ok": True, "services": list_services(active_only=active_only)})


# ---------- OpenSCAP security scan ----------

@app.route("/api/security/scan", methods=["POST"])
def api_start_security_scan():
    """Kick off a scan in the background. Returns immediately with a scan_id
    to poll -- full profile scans take minutes, never block a web request on this."""
    profile = (request.json or {}).get("profile")  # None -> uses config default
    scan_id = oscap_tool.start_scan(profile)
    return jsonify({"ok": True, "scan_id": scan_id})


@app.route("/api/security/scan/<scan_id>")
def api_security_scan_status(scan_id):
    status = oscap_tool.get_scan_status(scan_id)
    if not status.get("ok"):
        return jsonify(status), 404
    return jsonify(status)


@app.route("/api/security/fix", methods=["POST"])
def api_security_fix():
    """
    Apply the vetted, oscap-generated remediation script for one failed rule.
    Always requires an explicit confirm=True -- the frontend shows the exact
    script text first and only re-submits with confirm=True after a second,
    deliberate click. This runs the OFFICIAL SSG script, never anything the
    model writes itself.
    """
    data = request.json or {}
    scan_id, rule_id, confirm = data.get("scan_id"), data.get("rule_id"), bool(data.get("confirm"))

    status = oscap_tool.get_scan_status(scan_id)
    if not status.get("ok"):
        return jsonify({"ok": False, "error": "Unknown scan_id"}), 404

    fail = next((f for f in status.get("parsed", {}).get("fails", []) if f["rule_id"] == rule_id), None)
    if not fail or not fail.get("fix_script"):
        return jsonify({"ok": False, "error": "No fix script available for this rule"}), 400

    if not confirm:
        return jsonify({"ok": False, "needs_confirmation": True,
                         "rule_id": rule_id, "fix_script": fail["fix_script"]})

    return jsonify(oscap_tool.apply_fix(scan_id, rule_id, fail["fix_script"]))


@app.route("/api/security/report/<scan_id>")
def api_security_report_html(scan_id):
    """Serve the full OpenSCAP HTML report for a completed scan."""
    # scan_id comes from uuid4().hex[:12] -- alnum only, but validate anyway
    if not scan_id.isalnum():
        return "Invalid scan id", 400
    path = os.path.join(config.SCANS_DIR, f"{scan_id}-report.html")
    if not os.path.exists(path):
        return "Report not found", 404
    return send_from_directory(config.SCANS_DIR, f"{scan_id}-report.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)