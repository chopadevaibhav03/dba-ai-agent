"""
Chat agent: turns free-text prompts into either an instant regex-matched
service action, or a full tool-calling conversation with Ollama for
anything broader (scans, log checks, process lists, security checks, etc.)

Two layers, in order:

1. REGEX FAST PATH -- common, unambiguous phrasing ("list services",
   "is X running", "stop/start/restart X") is handled instantly without
   touching Ollama at all. This keeps basic service control fast and
   reliable no matter how loaded the system or the model is.

2. TOOL-CALLING AGENT -- anything else goes to Ollama with a real toolset
   (tools.py) it can call: top processes, disk breakdown, listening ports,
   recent errors, failed logins. Read-only tools execute immediately and
   their results are fed back to the model for a synthesized answer.
   State-changing actions are NEVER executed by the model directly --
   it can only "propose" one (via the propose_service_action /
   propose_remediation tools), which the API layer turns into a
   confirmation prompt for the human, exactly like the regex path does.

The model never outputs a shell command. Every tool is a fixed Python
function; service names are re-validated against real systemd units in
service_control.py before anything executes.
"""

import json
import re

import requests

import config
from automation import WHITELIST
from tools import TOOLS_SCHEMA, TOOL_FUNCTIONS

MAX_TOOL_ITERATIONS = 4
OLLAMA_CHAT_URL = config.OLLAMA_URL.replace("/api/generate", "/api/chat")

SYSTEM_PROMPT = f"""You are a helpful Linux system administration assistant running locally
on a RHEL 9 server. You have tools to inspect the system (processes, disk usage,
listening ports, recent errors, failed logins) -- use them whenever a question
needs real data instead of guessing.

You also have two special tools for taking action:
- propose_service_action: use when the user wants to start/stop/restart a service.
  This does NOT execute anything -- it just registers the proposed action for a
  human to confirm. Never claim you've already done it.
- propose_remediation: use when you want to recommend one of these known-safe
  fixes: {', '.join(WHITELIST.keys())}. Same rule -- proposing only, never claiming
  it's done.

Keep replies short and concrete. When you call a tool, wait for its result before
answering -- don't guess at data you could look up.
"""

_PROPOSE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "propose_service_action",
            "description": "Propose starting, stopping, or restarting a service. Requires human confirmation -- does not execute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "bare service name, e.g. splunkd"},
                    "action": {"type": "string", "enum": ["start", "stop", "restart"]},
                },
                "required": ["service", "action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_remediation",
            "description": "Propose one of the known-safe whitelisted remediation actions. Requires human confirmation -- does not execute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_key": {"type": "string", "enum": list(WHITELIST.keys())},
                },
                "required": ["action_key"],
            },
        },
    },
]

ALL_TOOLS = TOOLS_SCHEMA + _PROPOSE_TOOLS


# ---------- regex fast path (unchanged behavior, no Ollama needed) ----------

_LIST_RE = re.compile(r"\b(list|show)\b.*\bservices?\b", re.IGNORECASE)
_STATUS_RE = re.compile(
    r"^(?:is|check)\s+(?:the\s+)?([a-zA-Z0-9_.\-@]+)\s+(?:running|active|status)\??$",
    re.IGNORECASE,
)
_ACTION_RE = re.compile(
    r"^(stop|start|restart)\s+(?:the\s+)?([a-zA-Z0-9_.\-@]+)(?:\s+service)?\.?$",
    re.IGNORECASE,
)
_SECURITY_SCAN_RE = re.compile(
    r"(?=.*\b(?:security|vulnerabilit\w*|compliance|harden\w*)\b)(?=.*\b(?:scan|check)\w*\b)",
    re.IGNORECASE,
)


def _regex_intent(text: str):
    t = text.strip()
    if _SECURITY_SCAN_RE.search(t):
        return {"intent": "start_security_scan", "action": None, "service": None, "reply": ""}
    if _LIST_RE.search(t):
        return {"intent": "list_services", "action": None, "service": None, "reply": ""}
    m = _STATUS_RE.match(t)
    if m:
        return {"intent": "service_action", "action": "status", "service": m.group(1), "reply": ""}
    m = _ACTION_RE.match(t)
    if m:
        return {"intent": "service_action", "action": m.group(1).lower(), "service": m.group(2), "reply": ""}
    return None


# ---------- tool-calling agent for everything else ----------

def _ollama_chat(messages: list, tools: list) -> dict:
    resp = requests.post(
        OLLAMA_CHAT_URL,
        json={
            "model": config.OLLAMA_MODEL,
            "messages": messages,
            "tools": tools,
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def run_agent(user_text: str) -> dict:
    """
    Full tool-calling turn. Returns one of:
      {"type": "info", "reply": "..."}
      {"type": "confirm_service", "service": "...", "action": "...", "reply": "..."}
      {"type": "confirm_remediation", "action_key": "...", "reply": "..."}
      {"type": "error", "reply": "..."}
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            data = _ollama_chat(messages, ALL_TOOLS)
            message = data.get("message", {})
            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                # model gave a final answer
                return {"type": "info", "reply": message.get("content", "").strip() or "(no response)"}

            messages.append(message)

            for call in tool_calls:
                fn = call.get("function", {})
                name = fn.get("name")
                args = fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                if name == "propose_service_action":
                    service = args.get("service", "")
                    action = args.get("action", "")
                    return {
                        "type": "confirm_service",
                        "service": service,
                        "action": action,
                        "reply": message.get("content") or f"Proposing to {action} {service}.",
                    }

                if name == "propose_remediation":
                    key = args.get("action_key", "")
                    return {
                        "type": "confirm_remediation",
                        "action_key": key,
                        "reply": message.get("content") or f"Proposing to run: {key}.",
                    }

                fn_impl = TOOL_FUNCTIONS.get(name)
                if fn_impl is None:
                    result = {"ok": False, "error": f"Unknown tool: {name}"}
                else:
                    try:
                        result = fn_impl(**args)
                    except TypeError:
                        result = fn_impl()  # tool called with no/invalid args, use defaults
                    except Exception as e:
                        result = {"ok": False, "error": str(e)}

                messages.append({"role": "tool", "content": json.dumps(result)})

        return {"type": "info", "reply": "Reached the tool-call limit for this turn -- try a more specific question."}

    except requests.exceptions.RequestException as e:
        return {
            "type": "error",
            "reply": (
                f"Couldn't reach Ollama ({e}). Check it's running and that OLLAMA_MODEL "
                f"('{config.OLLAMA_MODEL}') in config.py matches `ollama list` exactly. "
                "Simple commands like 'list services', 'is X running', 'stop X' still work without it."
            ),
        }


# ---------- public entry point used by api.py ----------

def parse_and_respond(user_text: str) -> dict:
    """Try the regex fast path first; fall back to the tool-calling agent."""
    quick = _regex_intent(user_text)
    if quick:
        return quick
    return run_agent(user_text)


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or "list running services"
    print(json.dumps(parse_and_respond(text), indent=2))
