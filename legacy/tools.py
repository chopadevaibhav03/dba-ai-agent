"""
Read-only system inspection tools. Every function here is safe to run
without confirmation -- nothing here changes system state.

These are exposed to the LLM as "tools" it can call via Ollama's native
tool-calling API (chat_agent.py). Each function returns a plain dict so it
can be JSON-serialized straight back to the model as a tool result.

Keep every function defensive: catch its own errors, enforce a timeout,
and never let a single failing tool crash the whole agent turn.
"""

import subprocess

import psutil

DEFAULT_TIMEOUT = 15


def top_processes(n: int = 10) -> dict:
    """Top processes by memory and CPU usage."""
    try:
        procs = []
        for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
            try:
                procs.append(p.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        by_mem = sorted(procs, key=lambda x: x.get("memory_percent") or 0, reverse=True)[:n]
        return {
            "ok": True,
            "top_by_memory": [
                {"pid": p["pid"], "name": p["name"], "memory_percent": round(p.get("memory_percent") or 0, 2)}
                for p in by_mem
            ],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Only these paths can be inspected -- never an arbitrary user-supplied path.
ALLOWED_SCAN_PATHS = ["/", "/var", "/home", "/tmp", "/opt"]


def disk_breakdown(path: str = "/var", top_n: int = 8) -> dict:
    """Largest subdirectories under one of a fixed set of allowed paths."""
    if path not in ALLOWED_SCAN_PATHS:
        return {"ok": False, "error": f"path must be one of {ALLOWED_SCAN_PATHS}"}
    try:
        proc = subprocess.run(
            ["du", "-h", "--max-depth=1", path],
            capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
        )
        lines = [l for l in proc.stdout.splitlines() if l.strip()]
        # sort by human-readable size roughly -- good enough for a quick scan
        entries = []
        for line in lines:
            parts = line.split(None, 1)
            if len(parts) == 2:
                entries.append({"size": parts[0], "path": parts[1]})
        return {"ok": True, "path": path, "entries": entries[:top_n]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def listening_ports() -> dict:
    """Ports currently listening for connections, and what's listening on them."""
    try:
        proc = subprocess.run(
            ["ss", "-ltnp"], capture_output=True, text=True, timeout=DEFAULT_TIMEOUT
        )
        lines = [l for l in proc.stdout.splitlines()[1:] if l.strip()]  # skip header
        return {"ok": True, "listening": lines[:30]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def recent_errors(n: int = 20) -> dict:
    """Recent error-level entries from the systemd journal."""
    try:
        proc = subprocess.run(
            ["journalctl", "-p", "err", "-n", str(n), "--no-pager"],
            capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
        )
        lines = [l for l in proc.stdout.splitlines() if l.strip()]
        if not lines and proc.stderr:
            return {"ok": False, "error": proc.stderr.strip()[:300]}
        return {"ok": True, "errors": lines}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def failed_logins(n: int = 10) -> dict:
    """Recent failed SSH login attempts, if any are visible in the journal."""
    try:
        proc = subprocess.run(
            ["journalctl", "-u", "sshd", "-n", "500", "--no-pager"],
            capture_output=True, text=True, timeout=DEFAULT_TIMEOUT,
        )
        matches = [l for l in proc.stdout.splitlines() if "Failed password" in l or "authentication failure" in l]
        if not matches and proc.stderr:
            return {"ok": False, "error": proc.stderr.strip()[:300]}
        return {"ok": True, "failed_logins": matches[-n:]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------- tool schema for Ollama's tool-calling API ----------

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "top_processes",
            "description": "List the top processes by memory usage on this system.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer", "description": "how many to return, default 10"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disk_breakdown",
            "description": "Show largest subdirectories under a given top-level path to find what's using disk space.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": f"one of {ALLOWED_SCAN_PATHS}, default /var"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listening_ports",
            "description": "List all network ports currently listening for connections and which process owns each.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recent_errors",
            "description": "Show recent error-level log entries from the system journal, useful for diagnosing crashes or failures.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer", "description": "how many entries, default 20"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "failed_logins",
            "description": "Check for recent failed SSH login attempts, useful for basic security review.",
            "parameters": {
                "type": "object",
                "properties": {"n": {"type": "integer", "description": "how many to return, default 10"}},
            },
        },
    },
]

TOOL_FUNCTIONS = {
    "top_processes": top_processes,
    "disk_breakdown": disk_breakdown,
    "listening_ports": listening_ports,
    "recent_errors": recent_errors,
    "failed_logins": failed_logins,
}


if __name__ == "__main__":
    import json
    print(json.dumps(top_processes(5), indent=2))
    print(json.dumps(listening_ports(), indent=2))
