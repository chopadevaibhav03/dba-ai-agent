"""
Automation executor.

SAFETY MODEL:
- The LLM (or UI) can only ever request an action by its whitelist KEY.
- It can never supply a freeform shell command.
- Every action here is deliberately safe/reversible for a first pass.
- Nothing executes unless confirm=True is explicitly passed
  (the Streamlit UI wires this to a confirmation button).

Add new actions carefully -- anything added to WHITELIST becomes something
the LLM is allowed to recommend and a user can trigger with one click.
"""

import subprocess
from datetime import datetime, timezone

import config

# key -> (description, shell command)
# Keep these safe, idempotent, and reversible. Avoid destructive commands.
WHITELIST = {
    "clear_tmp_cache": (
        "Remove files older than 7 days from /tmp",
        "find /tmp -type f -atime +7 -delete",
    ),
    "clear_yum_cache": (
        "Clear the dnf/yum package cache to free disk space",
        "dnf clean all",
    ),
    "drop_page_cache": (
        "Ask the kernel to drop clean filesystem page cache (safe, cache rebuilds naturally)",
        "sync && echo 1 > /proc/sys/vm/drop_caches",
    ),
    "restart_service_example": (
        "Restart a named service (placeholder -- edit target service before use)",
        "systemctl restart CHANGE_ME.service",
    ),
    "compress_old_logs": (
        "Gzip journal/log files older than 3 days under /var/log",
        "find /var/log -type f -mtime +3 -name '*.log' -exec gzip {} \\;",
    ),
}


def list_actions() -> dict:
    return {k: v[0] for k, v in WHITELIST.items()}


def execute(action_key: str, confirm: bool = False) -> dict:
    """
    Execute a whitelisted action. Returns a result dict; never raises on
    command failure (captures stderr instead) so the UI can display it.
    """
    if action_key not in WHITELIST:
        return {"ok": False, "error": f"'{action_key}' is not a whitelisted action."}

    if config.REQUIRE_CONFIRMATION and not confirm:
        return {
            "ok": False,
            "error": "Confirmation required. Call execute(action_key, confirm=True).",
        }

    description, command = WHITELIST[action_key]
    try:
        proc = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        return {
            "ok": proc.returncode == 0,
            "action": action_key,
            "description": description,
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "executed_at": datetime.now(timezone.utc).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"Command timed out: {command}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    print("Whitelisted actions:")
    for key, desc in list_actions().items():
        print(f"  {key}: {desc}")
