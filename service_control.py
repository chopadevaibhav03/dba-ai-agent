"""
Service control layer.

All systemctl calls go through here. Design rules:
- Never build a shell string from user/LLM input. Always pass argument lists
  to subprocess (shell=False) so there's no injection surface.
- Never act on a service name that doesn't actually exist on the system --
  validate against `systemctl list-unit-files` first.
- Read-only actions (status, list) run immediately.
- State-changing actions (start/stop/restart) require confirm=True, wired
  to a UI confirmation click.
"""

import re
import subprocess

VALID_ACTIONS = {"start", "stop", "restart", "status"}
STATE_CHANGING_ACTIONS = {"start", "stop", "restart"}

# service unit names are dot/dash/underscore/alnum only -- this blocks
# anything resembling a shell metacharacter or path traversal attempt
SERVICE_NAME_RE = re.compile(r"^[a-zA-Z0-9_.\-@]+$")


def list_services(active_only: bool = False) -> list[dict]:
    """List known services and their active state."""
    cmd = ["systemctl", "list-units", "--type=service", "--no-legend", "--no-pager", "--plain"]
    if active_only:
        cmd.append("--state=running")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    services = []
    for line in proc.stdout.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4:
            unit, load, active, sub = parts[0], parts[1], parts[2], parts[3]
            services.append({"unit": unit, "load": load, "active": active, "sub": sub})
    return services


def service_exists(service: str) -> bool:
    """Check the service unit actually exists (guards against acting on a made-up name)."""
    if not SERVICE_NAME_RE.match(service):
        return False
    # normalize: allow "splunkd" or "splunkd.service"
    unit = service if service.endswith(".service") else f"{service}.service"
    proc = subprocess.run(
        ["systemctl", "list-unit-files", unit, "--no-legend", "--no-pager"],
        capture_output=True, text=True, timeout=10,
    )
    return unit in proc.stdout


def get_status(service: str) -> dict:
    if not service_exists(service):
        return {"ok": False, "error": f"No such service: {service}"}
    unit = service if service.endswith(".service") else f"{service}.service"
    proc = subprocess.run(
        ["systemctl", "is-active", unit], capture_output=True, text=True, timeout=10
    )
    state = proc.stdout.strip() or "unknown"
    return {"ok": True, "service": unit, "state": state}


def perform_action(service: str, action: str, confirm: bool = False) -> dict:
    if action not in VALID_ACTIONS:
        return {"ok": False, "error": f"Unknown action: {action}"}

    if not service_exists(service):
        return {"ok": False, "error": f"No such service: {service}"}

    unit = service if service.endswith(".service") else f"{service}.service"

    if action == "status":
        return get_status(unit)

    if action in STATE_CHANGING_ACTIONS and not confirm:
        return {
            "ok": False,
            "needs_confirmation": True,
            "service": unit,
            "action": action,
            "error": f"Confirmation required to {action} {unit}.",
        }

    # start/stop/restart need root -- gunicorn runs unprivileged, so this
    # goes through a narrowly-scoped, passwordless sudo rule (see
    # /etc/sudoers.d/os-agent) limited to exactly these three systemctl
    # verbs. "-n" (non-interactive) ensures it fails cleanly instead of
    # hanging if that sudoers rule is ever missing, ​rather than trying to
    # prompt for a password that can never be answered from a background
    # service.
    cmd = ["sudo", "-n", "systemctl", action, unit]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    result = {
        "ok": proc.returncode == 0,
        "service": unit,
        "action": action,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }
    if not result["ok"] and "password is required" in result["stderr"].lower():
        result["error"] = (
            "sudo needs a passwordless rule for systemctl start/stop/restart. "
            "See /etc/sudoers.d/os-agent -- run 'sudo visudo -f /etc/sudoers.d/os-agent' to add it."
        )
    # attach fresh status so the UI can show the outcome immediately
    result["new_state"] = get_status(unit).get("state")
    return result


if __name__ == "__main__":
    import json
    print(json.dumps(list_services(active_only=True)[:5], indent=2))
