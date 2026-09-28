"""
LLM analyzer.

Pulls a recent window of metrics from SQLite, summarizes it (so we don't
dump raw time-series at the model), and asks the local Ollama model to
diagnose the system and propose fixes. The model is instructed to reply
in strict JSON so the UI and automation executor can consume it directly.

Usage:
    python3 analyzer.py                # analyze last 5 minutes, print result
"""

import json
import sqlite3
import statistics
import sys
from datetime import datetime, timedelta, timezone

import requests

import config
from automation import WHITELIST


def get_recent_samples(minutes: int = 5) -> list[dict]:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    rows = conn.execute(
        "SELECT * FROM metrics WHERE ts >= ? ORDER BY ts ASC", (cutoff,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def summarize(samples: list[dict]) -> dict:
    """Collapse a window of raw samples into a compact summary for the LLM."""
    if not samples:
        return {}

    def stats(key):
        vals = [s[key] for s in samples if s[key] is not None]
        if not vals:
            return {"avg": None, "max": None}
        return {"avg": round(statistics.mean(vals), 1), "max": round(max(vals), 1)}

    latest = samples[-1]
    disk_latest = json.loads(latest["disk_json"]) if latest["disk_json"] else {}

    return {
        "window_minutes": round(
            (
                datetime.fromisoformat(samples[-1]["ts"])
                - datetime.fromisoformat(samples[0]["ts"])
            ).total_seconds()
            / 60,
            1,
        ),
        "sample_count": len(samples),
        "cpu_percent": stats("cpu_percent"),
        "mem_percent": stats("mem_percent"),
        "swap_percent": stats("swap_percent"),
        "swap_used_mb_latest": latest["swap_used_mb"],
        "swap_trend": "rising" if _is_rising(samples, "swap_used_mb") else "stable_or_falling",
        "load_avg_1_latest": latest["load_avg_1"],
        "disk": disk_latest,
    }


def _is_rising(samples: list[dict], key: str) -> bool:
    if len(samples) < 3:
        return False
    vals = [s[key] for s in samples if s[key] is not None]
    return len(vals) >= 3 and vals[-1] > vals[0] * 1.1  # >10% up over window


def build_prompt(summary: dict) -> str:
    allowed_actions = ", ".join(WHITELIST.keys())
    return f"""You are a Linux sysadmin assistant monitoring a RHEL 9 server.

Here is a summary of system metrics over the last {summary.get('window_minutes', '?')} minutes:
{json.dumps(summary, indent=2)}

Task:
1. Decide if there is a real issue (ignore normal/healthy ranges).
2. If there is an issue, identify severity: "info", "warning", or "critical".
3. Give a short root-cause explanation in plain English.
4. Recommend 1-3 remediation actions, chosen ONLY from this exact allowed list
   (use the exact key names, do not invent new ones): {allowed_actions}
   If no action from the list applies, return an empty list for recommended_actions.

Respond with ONLY valid JSON, no markdown fences, no extra text, in this exact shape:
{{
  "severity": "info|warning|critical",
  "issue": "one line summary",
  "root_cause": "1-3 sentences",
  "recommended_actions": ["action_key", "..."],
  "explanation": "why these actions help"
}}
"""


def analyze(minutes: int = 5) -> dict:
    samples = get_recent_samples(minutes)
    if not samples:
        return {
            "severity": "info",
            "issue": "No data yet",
            "root_cause": "Collector hasn't gathered enough samples. Let it run for a few minutes.",
            "recommended_actions": [],
            "explanation": "",
        }

    summary = summarize(samples)
    prompt = build_prompt(summary)

    try:
        resp = requests.post(
            config.OLLAMA_URL,
            json={
                "model": config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=120,
        )
        resp.raise_for_status()
        raw_text = resp.json().get("response", "{}")
    except requests.exceptions.RequestException as e:
        return {
            "severity": "warning",
            "issue": "Could not reach Ollama",
            "root_cause": (
                f"Request to {config.OLLAMA_URL} failed: {e}. "
                f"Check that Ollama is running and that OLLAMA_MODEL ('{config.OLLAMA_MODEL}') "
                "in config.py exactly matches `ollama list` output (including any :tag)."
            ),
            "recommended_actions": [],
            "explanation": "",
            "_summary": summary,
            "_analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        result = {
            "severity": "warning",
            "issue": "Model returned non-JSON response",
            "root_cause": raw_text[:300],
            "recommended_actions": [],
            "explanation": "",
        }

    result["_summary"] = summary
    result["_analyzed_at"] = datetime.now(timezone.utc).isoformat()
    return result


if __name__ == "__main__":
    mins = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(json.dumps(analyze(mins), indent=2))
