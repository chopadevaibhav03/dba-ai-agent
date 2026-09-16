"""
AI Orchestrator v1

Architecture:

    User
      |
      v
    FastAPI
      |
      v
    Domain Router
      |
        +---- Linux  ----> Linux tools
        |
        +---- Oracle ----> Oracle tools
        |
        +---- OSCAP  ----> OSCAP read-only tools
        |
        +---- General ---> No operational tools
        |
        v
    Ollama / Llama 3.2:3b
      |
      v
    Final response

Stage 1 safety:

    - Only registered tools may be called.
    - Only read-only tools are exposed.
    - No arbitrary shell.
    - No arbitrary SQL.
    - No remediation.
    - No sudo.
    - oscap.scan is excluded from AI.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any

import requests

import config
from core.domain_router import detect_domain
from core.tool_registry import execute_tool, list_tools
from service_control import list_services
from services.oracle_health_service import get_oracle_health


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_CHAT_URL = config.OLLAMA_URL.replace(
    "/api/generate",
    "/api/chat",
)

MAX_TOOL_ITERATIONS = 4

OLLAMA_TIMEOUT_SECONDS = 300


# ---------------------------------------------------------------------------
# AI safety
# ---------------------------------------------------------------------------

EXCLUDED_TOOLS = {
    "oscap.scan",
}


# Domain -> allowed tool prefixes
DOMAIN_TOOL_PREFIXES = {
    "linux": (
        "linux.",
    ),
    "oracle": (
        "oracle.",
    ),
    "oscap": (
        "oscap.",
    ),
    "general": (),
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
You are the AI operations assistant for a local Linux, Oracle and
OpenSCAP administration platform.

The server is running RHEL 8.

You have access only to registered READ-ONLY diagnostic tools.

IMPORTANT SAFETY RULES:

1. Use tools whenever the user asks for current system information.
2. Never invent current system values.
3. Never execute arbitrary shell commands.
4. Never execute arbitrary SQL.
5. Never modify files.
6. Never modify services.
7. Never modify databases.
8. Never perform remediation.
9. Never start an OpenSCAP scan.
10. Never claim that a change was performed.
11. Only use tools explicitly provided to you.
12. Base operational answers on actual tool results.
13. If a tool cannot answer the question, say so clearly.
14. Never use bracketed placeholder text like "[Insert information]"
    in your answer. If you don't have a real value, say you don't
    have that data instead of leaving a placeholder.

When a tool result shows a problem:

- explain what the result means
- identify the likely impact
- suggest what should be investigated next
- do NOT perform the fix

You are an analysis and diagnostic assistant,
not an autonomous executor.

For the final answer after tool results are available, use exactly this shape:

Status: <one word — Healthy, Warning, or Critical>
Finding: <one sentence stating what the tool found, nothing else>
Next step: <one sentence — either 'No action needed' or a single concrete recommendation. Never both recommend an action and tell the user not to take it.>

Do not hedge or contradict the tool result.
Do not add caveats about the tool's limitations unless the tool result itself was empty or an error.
Keep answers concise and practical.
""".strip()


# ---------------------------------------------------------------------------
# Tool schema helpers
# ---------------------------------------------------------------------------

def _build_tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a central tool-registry definition into Ollama's
    function-calling format.
    """

    name = tool.get("name")

    if not name:
        raise ValueError("Tool registry entry has no name")

    description = tool.get(
        "description",
        f"Read-only diagnostic tool: {name}",
    )

    parameters = tool.get("parameters")

    if not isinstance(parameters, dict):
        parameters = {
            "type": "object",
            "properties": {},
        }

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }


def build_tool_schemas(
    domain: str | None = None,
) -> list[dict[str, Any]]:
    """
    Build Ollama tool schemas for one domain.

    Linux:
        only linux.* tools

    Oracle:
        only oracle.* tools

    OSCAP:
        only oscap.* read-only tools

    General:
        no operational tools
    """

    selected_domain = domain or "general"

    prefixes = DOMAIN_TOOL_PREFIXES.get(
        selected_domain,
        (),
    )

    if not prefixes:
        return []

    registry_tools = list_tools()

    schemas: list[dict[str, Any]] = []

    for tool in registry_tools:

        name = tool.get("name")

        if not name:
            continue

        # Safety exclusion
        if name in EXCLUDED_TOOLS:
            continue

        # Domain isolation
        if not name.startswith(prefixes):
            continue

        try:
            schemas.append(
                _build_tool_schema(tool)
            )
        except Exception:
            # A malformed registry entry must not crash the AI layer.
            continue

    return schemas


# ---------------------------------------------------------------------------
# Ollama communication
# ---------------------------------------------------------------------------

def _call_ollama(
    messages: list[dict[str, Any]],
    domain: str,
    timing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Send one request to Ollama.

    Only tools belonging to the detected domain are supplied.

    Timing is optionally recorded into the supplied timing dictionary.
    """

    schema_start = time.perf_counter()

    tools = build_tool_schemas(domain)

    schema_elapsed = (
        time.perf_counter() - schema_start
    ) * 1000

    if timing is not None:
        timing.setdefault(
            "schema_build_ms",
            0.0,
        )

        timing["schema_build_ms"] += schema_elapsed

    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": getattr(config, "OLLAMA_KEEP_ALIVE", "30m"),
        "options": {
            "temperature": 0.2,
        },
    }

    # For general questions there are no operational tools.
    if tools:
        payload["tools"] = tools

    call_start = time.perf_counter()

    try:
        response = requests.post(
            OLLAMA_CHAT_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        data = response.json()

        call_elapsed = (
            time.perf_counter() - call_start
        ) * 1000

        if timing is not None:
            timing.setdefault(
                "ollama_calls",
                [],
            )

            timing["ollama_calls"].append(
                {
                    "duration_ms": round(
                        call_elapsed,
                        2,
                    ),
                    "duration_seconds": round(
                        call_elapsed / 1000,
                        3,
                    ),
                    "tool_schema_count": len(tools),
                    "domain": domain,
                }
            )

        return data

    except requests.exceptions.RequestException as exc:

        call_elapsed = (
            time.perf_counter() - call_start
        ) * 1000

        if timing is not None:
            timing.setdefault(
                "ollama_calls",
                [],
            )

            timing["ollama_calls"].append(
                {
                    "duration_ms": round(
                        call_elapsed,
                        2,
                    ),
                    "duration_seconds": round(
                        call_elapsed / 1000,
                        3,
                    ),
                    "tool_schema_count": len(tools),
                    "domain": domain,
                    "error": str(exc),
                }
            )

        raise


# ---------------------------------------------------------------------------
# Tool argument handling
# ---------------------------------------------------------------------------

def _normalize_arguments(
    arguments: Any,
) -> dict[str, Any]:
    """
    Ollama may return function arguments as either a dictionary
    or a JSON string.
    """

    if arguments is None:
        return {}

    if isinstance(arguments, dict):
        return arguments

    if isinstance(arguments, str):

        try:
            parsed = json.loads(arguments)

            if isinstance(parsed, dict):
                return parsed

        except json.JSONDecodeError:
            pass

    return {}


# ---------------------------------------------------------------------------
# Registered tool execution
# ---------------------------------------------------------------------------

def _execute_registered_tool(
    tool_name: str,
    arguments: dict[str, Any],
    timing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Execute a tool through the central registry.

    The AI layer never directly imports or executes Linux/Oracle/
    OSCAP implementation functions.
    """

    if tool_name in EXCLUDED_TOOLS:

        return {
            "ok": False,
            "error": (
                f"Tool '{tool_name}' is not available "
                "to the AI layer."
            ),
        }

    tool_start = time.perf_counter()

    try:

        result = execute_tool(
            tool_name,
            **arguments,
        )

        tool_elapsed = (
            time.perf_counter() - tool_start
        ) * 1000

        if timing is not None:
            timing.setdefault(
                "tool_execution",
                [],
            )

            timing["tool_execution"].append(
                {
                    "tool": tool_name,
                    "duration_ms": round(
                        tool_elapsed,
                        2,
                    ),
                    "duration_seconds": round(
                        tool_elapsed / 1000,
                        3,
                    ),
                }
            )

        return result

    except Exception as exc:

        tool_elapsed = (
            time.perf_counter() - tool_start
        ) * 1000

        if timing is not None:
            timing.setdefault(
                "tool_execution",
                [],
            )

            timing["tool_execution"].append(
                {
                    "tool": tool_name,
                    "duration_ms": round(
                        tool_elapsed,
                        2,
                    ),
                    "duration_seconds": round(
                        tool_elapsed / 1000,
                        3,
                    ),
                    "error": str(exc),
                }
            )

        return {
            "ok": False,
            "error": str(exc),
        }


def _is_empty_result(result: Any) -> bool:
    """
    True if a tool result represents "no data". Used to bypass the
    model entirely for empty results -- narrating "nothing found" is
    exactly the case where a small local model is most prone to
    inventing example data instead of reporting the empty result.
    """
    if result is None:
        return True
    if isinstance(result, list):
        return len(result) == 0
    if isinstance(result, dict):
        if result.get("ok") is False:
            return False  # an error isn't "empty" -- let the model explain it
        for key in ("findings", "results", "rows", "items", "data", "sessions"):
            if key in result and isinstance(result[key], list):
                return len(result[key]) == 0
        if not result:
            return True
    return False


# ---------------------------------------------------------------------------
# Conservative deterministic fast paths
# ---------------------------------------------------------------------------

def try_fast_path(
    user_message: str,
) -> dict[str, Any] | None:
    """Answer a few unambiguous operational questions without Ollama."""

    message = user_message.strip().lower()

    service_match = re.fullmatch(
        r"(?:is ([a-z0-9_.@-]+) running|([a-z0-9_.@-]+) status)",
        message,
    )

    if service_match:
        service = service_match.group(1) or service_match.group(2)
        result = _execute_registered_tool(
            "linux.failed_services",
            {},
        )
        failed_services = result.get("services", []) if result.get("ok") else []
        failed_units = {
            str(item.get("unit", "")).removesuffix(".service")
            for item in failed_services
            if isinstance(item, dict)
        }

        if not result.get("ok"):
            reply = f"I could not check service status: {result.get('error', 'unknown error')}"
        elif service.removesuffix(".service") in failed_units:
            reply = f"{service} is failed."
        else:
            reply = f"{service} is not in the failed services list."

        return {
            "ok": True,
            "reply": reply,
            "tool_calls": [{"name": "linux.failed_services", "arguments": {}, "result": result}],
        }

    if message in {"list services", "show services"}:
        try:
            services = list_services(active_only=False)
            result = {"ok": True, "services": services}
            names = [str(item.get("unit", item)) for item in services]
            reply = (
                f"Services: {', '.join(names)}"
                if names
                else "No services were returned."
            )
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}
            reply = f"I could not list services: {exc}"

        return {
            "ok": True,
            "reply": reply,
            "tool_calls": [{"name": "service_control.list_services", "arguments": {}, "result": result}],
        }

    if message in {"cpu usage", "current cpu"}:
        result = _execute_registered_tool("linux.cpu", {})
        if result.get("ok"):
            reply = (
                f"CPU usage is {result.get('usage_percent', '--')}%. "
                f"Load averages: {result.get('load_1m', '--')}, "
                f"{result.get('load_5m', '--')}, "
                f"{result.get('load_15m', '--')} (1m, 5m, 15m)."
            )
        else:
            reply = f"I could not read CPU usage: {result.get('error', 'unknown error')}"

        return {
            "ok": True,
            "reply": reply,
            "tool_calls": [{"name": "linux.cpu", "arguments": {}, "result": result}],
        }

    return None


def try_oracle_fast_path(
    user_message: str,
) -> dict[str, Any] | None:
    """Summarize the complete Oracle health snapshot in one Ollama call."""

    message = user_message.strip().lower()
    if not re.fullmatch(
        r"(?:is oracle healthy|oracle health|oracle status)[?.!]?$",
        message,
    ):
        return None

    total_start = time.perf_counter()
    timing: dict[str, Any] = {
        "routing_ms": 0.0,
        "schema_build_ms": 0.0,
        "ollama_calls": [],
        "tool_execution": [],
    }
    health = get_oracle_health()
    messages = [
        {
            "role": "system",
            "content": (
                "Summarize the supplied Oracle health data in plain English. "
                "State the overall status first, then mention the most important "
                "findings. Do not call tools, invent values, or add markdown tables."
            ),
        },
        {
            "role": "user",
            "content": (
                "Oracle health snapshot:\n"
                + json.dumps(health, default=str)
            ),
        },
    ]

    data = _call_ollama(messages, "general", timing)
    response = data.get("message") or {}
    reply = (
        response.get("content")
        or "The AI did not return an Oracle health summary."
    ).strip()
    total_elapsed = (time.perf_counter() - total_start) * 1000
    timing["total_ms"] = round(total_elapsed, 2)
    timing["total_seconds"] = round(total_elapsed / 1000, 3)

    return {
        "ok": True,
        "reply": reply,
        "domain": "oracle_fast_path",
        "tool_calls": [],
        "iterations": 1,
        "model": config.OLLAMA_MODEL,
        "health": health,
        "timing": timing,
    }


# ---------------------------------------------------------------------------
# Main AI function
# ---------------------------------------------------------------------------

def run_ai(
    user_message: str,
) -> dict[str, Any]:
    """
    Execute one AI diagnostic request.

    Flow:

        user message
            |
            v
        domain router
            |
            v
        domain-specific tools
            |
            v
        Ollama
            |
            v
        tool calls
            |
            v
        central registry
            |
            v
        tool results
            |
            v
        Ollama final answer
    """

    total_start = time.perf_counter()

    user_message = (
        user_message or ""
    ).strip()

    if not user_message:

        return {
            "ok": False,
            "reply": "Please provide a question.",
            "domain": "general",
            "tool_calls": [],
        }

    oracle_fast_path = try_oracle_fast_path(user_message)
    if oracle_fast_path is not None:
        return oracle_fast_path

    fast_path = try_fast_path(user_message)
    if fast_path is not None:
        fast_path["domain"] = "fast_path"
        return fast_path

    # ---------------------------------------------------------------
    # Determine domain BEFORE calling Ollama.
    # ---------------------------------------------------------------

    routing_start = time.perf_counter()

    domain = detect_domain(
        user_message
    )

    routing_elapsed = (
        time.perf_counter() - routing_start
    ) * 1000

    timing: dict[str, Any] = {
        "routing_ms": round(
            routing_elapsed,
            2,
        ),
        "schema_build_ms": 0.0,
        "ollama_calls": [],
        "tool_execution": [],
    }

    system_content = SYSTEM_PROMPT

    if domain == "general":
        system_content += (
            "\n\nNOTE: No diagnostic tools are available for this "
            "request -- it did not match Linux, Oracle, or OSCAP. "
            "If the user is asking about specific system, database, "
            "or security data (status, usage, health, findings), you "
            "do NOT have that information. Say so plainly and suggest "
            "they ask about Linux, Oracle, or OSCAP specifically. Do "
            "NOT provide any specific number, percentage, or status."
        )

    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": system_content,
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    tool_history: list[dict[str, Any]] = []

    try:

        for iteration in range(
            MAX_TOOL_ITERATIONS
        ):

            data = _call_ollama(
                messages,
                domain,
                timing,
            )

            message = (
                data.get("message")
                or {}
            )

            tool_calls = (
                message.get("tool_calls")
                or []
            )

            # -------------------------------------------------------
            # Model returned final answer.
            # -------------------------------------------------------

            if not tool_calls:

                reply = (
                    message.get("content")
                    or "The AI did not return a response."
                ).strip()

                total_elapsed = (
                    time.perf_counter()
                    - total_start
                ) * 1000

                timing["total_ms"] = round(
                    total_elapsed,
                    2,
                )

                timing["total_seconds"] = round(
                    total_elapsed / 1000,
                    3,
                )

                return {
                    "ok": True,
                    "reply": reply,
                    "domain": domain,
                    "tool_calls": tool_history,
                    "iterations": iteration + 1,
                    "model": config.OLLAMA_MODEL,
                    "timing": timing,
                }

            # -------------------------------------------------------
            # Preserve assistant message containing tool calls.
            # -------------------------------------------------------

            messages.append(message)

            # -------------------------------------------------------
            # Execute every requested tool.
            # -------------------------------------------------------

            for call in tool_calls:

                function = (
                    call.get("function")
                    or {}
                )

                tool_name = function.get(
                    "name"
                )

                arguments = _normalize_arguments(
                    function.get("arguments")
                )

                if not tool_name:
                    continue

                result = _execute_registered_tool(
                    tool_name,
                    arguments,
                    timing,
                )

                tool_history.append(
                    {
                        "name": tool_name,
                        "arguments": arguments,
                        "result": result,
                    }
                )

                # Send the actual tool result back to Ollama.
                messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(
                            result,
                            default=str,
                        ),
                    }
                )

            # If every tool called this turn came back empty, answer
            # deterministically -- never let the model narrate "nothing
            # found" into invented example data.
            this_round = tool_history[-len(tool_calls):]
            if tool_calls and all(
                _is_empty_result(history["result"])
                for history in this_round
            ):
                names = ", ".join(
                    history["name"]
                    for history in this_round
                )
                total_elapsed = (
                    time.perf_counter() - total_start
                ) * 1000
                timing["total_ms"] = round(
                    total_elapsed,
                    2,
                )
                timing["total_seconds"] = round(
                    total_elapsed / 1000,
                    3,
                )
                return {
                    "ok": True,
                    "reply": (
                        f"No results were returned by {names}. "
                        "Nothing to report."
                    ),
                    "domain": domain,
                    "tool_calls": tool_history,
                    "iterations": iteration + 1,
                    "model": config.OLLAMA_MODEL,
                    "timing": timing,
                    "empty_result_shortcircuit": True,
                }

        # -----------------------------------------------------------
        # Tool iteration limit reached.
        # -----------------------------------------------------------

        total_elapsed = (
            time.perf_counter()
            - total_start
        ) * 1000

        timing["total_ms"] = round(
            total_elapsed,
            2,
        )

        timing["total_seconds"] = round(
            total_elapsed / 1000,
            3,
        )

        return {
            "ok": False,
            "reply": (
                "The AI reached the maximum number "
                "of diagnostic tool calls for this request."
            ),
            "domain": domain,
            "tool_calls": tool_history,
            "iterations": MAX_TOOL_ITERATIONS,
            "model": config.OLLAMA_MODEL,
            "timing": timing,
        }

    except requests.exceptions.RequestException as exc:

        total_elapsed = (
            time.perf_counter()
            - total_start
        ) * 1000

        timing["total_ms"] = round(
            total_elapsed,
            2,
        )

        timing["total_seconds"] = round(
            total_elapsed / 1000,
            3,
        )

        return {
            "ok": False,
            "reply": (
                "I could not connect to Ollama. "
                "Check that Ollama is running and that "
                f"the configured model '{config.OLLAMA_MODEL}' "
                "is available."
            ),
            "error": str(exc),
            "domain": domain,
            "tool_calls": tool_history,
            "model": config.OLLAMA_MODEL,
            "timing": timing,
        }

    except Exception as exc:

        total_elapsed = (
            time.perf_counter()
            - total_start
        ) * 1000

        timing["total_ms"] = round(
            total_elapsed,
            2,
        )

        timing["total_seconds"] = round(
            total_elapsed / 1000,
            3,
        )

        return {
            "ok": False,
            "reply": "The AI orchestration request failed.",
            "error": str(exc),
            "domain": domain,
            "tool_calls": tool_history,
            "model": config.OLLAMA_MODEL,
            "timing": timing,
        }


# ---------------------------------------------------------------------------
# AI status
# ---------------------------------------------------------------------------

def ai_status() -> dict[str, Any]:
    """
    Return local AI configuration/status.

    This does not run an inference request.
    """

    domain_counts = {}

    for domain in (
        "linux",
        "oracle",
        "oscap",
        "general",
    ):

        domain_counts[domain] = len(
            build_tool_schemas(domain)
        )

    return {
        "provider": "ollama",
        "model": config.OLLAMA_MODEL,
        "chat_url": OLLAMA_CHAT_URL,
        "domain_routing": True,
        "domains": [
            "linux",
            "oracle",
            "oscap",
            "general",
        ],
        "tool_counts": domain_counts,
        "excluded_tools": sorted(
            EXCLUDED_TOOLS
        ),
        "read_only": True,
        "max_tool_iterations": MAX_TOOL_ITERATIONS,
        "ollama_timeout_seconds": OLLAMA_TIMEOUT_SECONDS,
    }


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    import sys

    question = " ".join(
        sys.argv[1:]
    )

    if not question:
        question = (
            "What is the current CPU usage?"
        )

    result = run_ai(
        question
    )

    print(
        json.dumps(
            result,
            indent=2,
            default=str,
        )
    )