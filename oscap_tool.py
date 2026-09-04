"""
OpenSCAP integration.

Runs `oscap xccdf eval` in a background thread (full profile scans take
minutes -- never run this inline in a web request, learned that lesson
the hard way with Ollama timeouts earlier in this project). Parses the
XCCDF results.xml for pass/fail counts and failed rules by severity, then
asks Ollama to turn that into a short, prioritized remediation summary.

This runs entirely as root (no sudo wrapper needed) since the agent's
service now runs as root throughout.

Remediation: when a fix is applied, it runs the EXACT vetted script that
oscap's own generated HTML report provides for that rule -- never
anything the LLM writes or invents. Applying still always requires an
explicit confirm=True from a human, via /api/security/fix.
"""

import html
import json
import os
import re
import sqlite3
import subprocess
import threading
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

import config

os.makedirs(config.SCANS_DIR, exist_ok=True)

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "unknown": 3, None: 3}


# ---------- findings cache ----------
# Once a rule's failure has been explained by the LLM, the recommendation is
# stored here and reused on every future scan that finds the same rule
# failing -- no repeat LLM call needed. This also means the same finding
# always gets the same explanation, rather than slightly different wording
# each time.

def _init_findings_cache():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS finding_recommendations (
            rule_id TEXT PRIMARY KEY,
            rule_name TEXT,
            severity TEXT,
            recommendation_json TEXT NOT NULL,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            times_seen INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    conn.close()


def _get_cached_recommendation(rule_id: str):
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM finding_recommendations WHERE rule_id = ?", (rule_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "rule_id": row["rule_id"],
        "rule_name": row["rule_name"],
        "severity": row["severity"],
        "recommendation": json.loads(row["recommendation_json"]),
        "times_seen": row["times_seen"],
    }


def _touch_cached_recommendation(rule_id: str):
    """Same finding seen again -- bump times_seen/last_seen, no new LLM call."""
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        "UPDATE finding_recommendations SET last_seen = ?, times_seen = times_seen + 1 WHERE rule_id = ?",
        (now, rule_id),
    )
    conn.commit()
    conn.close()


def _save_new_recommendation(rule_id: str, rule_name: str, severity: str, recommendation: dict):
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        """
        INSERT INTO finding_recommendations (rule_id, rule_name, severity, recommendation_json, first_seen, last_seen, times_seen)
        VALUES (?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(rule_id) DO UPDATE SET
            recommendation_json = excluded.recommendation_json,
            last_seen = excluded.last_seen,
            times_seen = finding_recommendations.times_seen + 1
        """,
        (rule_id, rule_name, severity, json.dumps(recommendation), now, now),
    )
    conn.commit()
    conn.close()


def get_findings_history(limit: int = 100) -> list:
    """All previously-seen findings, most-recently-seen first -- useful for
    a 'known issues' view, or for seeing what keeps recurring across scans."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM finding_recommendations ORDER BY last_seen DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [
        {
            "rule_id": r["rule_id"], "rule_name": r["rule_name"], "severity": r["severity"],
            "recommendation": json.loads(r["recommendation_json"]),
            "first_seen": r["first_seen"], "last_seen": r["last_seen"], "times_seen": r["times_seen"],
        }
        for r in rows
    ]


def _status_path(scan_id: str) -> str:
    return os.path.join(config.SCANS_DIR, f"{scan_id}.json")


def _write_status(scan_id: str, data: dict):
    with open(_status_path(scan_id), "w") as f:
        json.dump(data, f, indent=2)


def get_scan_status(scan_id: str) -> dict:
    path = _status_path(scan_id)
    if not os.path.exists(path):
        return {"ok": False, "error": "Unknown scan_id"}
    with open(path) as f:
        return {"ok": True, **json.load(f)}


def _pretty_rule_name(rule_id: str) -> str:
    name = re.sub(r"^xccdf_org\.ssgproject\.content_rule_", "", rule_id)
    return name.replace("_", " ")


# ---------- rule metadata (real CIS text, not just the bare rule id) ----------
# The datastream oscap itself reads already contains the official title,
# description, rationale, and fix text for every rule. Extracting it once
# and reusing it everywhere (LLM prompts, the UI, the /api/security/fix
# endpoint) is far more accurate than letting the model guess from a bare
# rule id -- and needs zero new documents or infrastructure.

_rule_metadata_cache: dict = {}


def _load_rule_metadata(content_path: str) -> dict:
    if content_path in _rule_metadata_cache:
        return _rule_metadata_cache[content_path]

    metadata = {}
    try:
        tree = ET.parse(content_path)
        root = tree.getroot()
        for elem in root.iter():
            if elem.tag.split("}")[-1] != "Rule":
                continue
            rule_id = elem.get("id", "")
            if not rule_id:
                continue
            fields = {"title": "", "description": "", "rationale": "", "fix_text": ""}
            for child in elem:
                ctag = child.tag.split("}")[-1]
                if ctag == "title" and not fields["title"]:
                    fields["title"] = "".join(child.itertext()).strip()
                elif ctag == "description" and not fields["description"]:
                    fields["description"] = "".join(child.itertext()).strip()
                elif ctag == "rationale" and not fields["rationale"]:
                    fields["rationale"] = "".join(child.itertext()).strip()
                elif ctag == "fixtext" and not fields["fix_text"]:
                    fields["fix_text"] = "".join(child.itertext()).strip()
            metadata[rule_id] = fields
    except Exception as e:
        # Non-fatal -- scan still works, just without enriched text.
        metadata["_error"] = str(e)

    _rule_metadata_cache[content_path] = metadata
    return metadata


def parse_xccdf_results(xml_path: str, content_path: str = None) -> dict:
    """Extract pass/fail counts and failed rules (with severity, and real
    CIS title/description/rationale/fix text when content_path is given)
    from a results.xml produced by `oscap xccdf eval --results ...`."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    rule_results = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag != "rule-result":
            continue
        idref = elem.get("idref", "")
        severity = elem.get("severity", "unknown")
        result_text = None
        for child in elem:
            if child.tag.split("}")[-1] == "result":
                result_text = (child.text or "").strip()
                break
        rule_results.append({"rule_id": idref, "severity": severity, "result": result_text})

    counts = {}
    for r in rule_results:
        counts[r["result"]] = counts.get(r["result"], 0) + 1

    fails = [r for r in rule_results if r["result"] == "fail"]
    fails.sort(key=lambda r: SEVERITY_ORDER.get(r["severity"], 3))

    metadata = _load_rule_metadata(content_path) if content_path else {}

    fails_out = []
    for r in fails:
        meta = metadata.get(r["rule_id"], {})
        fails_out.append({
            "rule": _pretty_rule_name(r["rule_id"]),
            "rule_id": r["rule_id"],
            "severity": r["severity"],
            "title": meta.get("title") or _pretty_rule_name(r["rule_id"]),
            "description": meta.get("description", ""),
            "rationale": meta.get("rationale", ""),
            "fix_text": meta.get("fix_text", ""),
        })

    return {
        "total_rules_checked": len(rule_results),
        "counts": counts,
        "fails": fails_out,
    }


def parse_report_details(html_path: str, rule_ids: list) -> dict:
    """Pull description, rationale, and the exact vetted remediation script
    straight out of the HTML report oscap already generates for this scan.
    This is real SSG content, not anything the model writes -- used to fill
    in fix_script, which the raw XCCDF fixtext often lacks in ready-to-run
    form."""
    with open(html_path, encoding="utf-8") as f:
        content = f.read()

    # Each rule's "Result Details" panel is marked with a class like
    # rule-detail-id-xccdf_org.ssgproject.content_rule_<name>
    parts = re.split(r'(?=<div class="panel panel-default rule-detail)', content)

    def strip_tags(s):
        s = re.sub(r'<[^>]+>', ' ', s)
        s = html.unescape(s)
        return re.sub(r'\s+', ' ', s).strip()

    wanted = set(rule_ids)
    results = {}
    for part in parts:
        idm = re.search(r'rule-detail-id-(xccdf_org\.ssgproject\.content_rule_[A-Za-z0-9_]+)', part)
        if not idm or idm.group(1) not in wanted:
            continue
        rid = idm.group(1)

        def section(name):
            m = re.search(rf'<td>{name}</td><td[^>]*><div class="{name.lower()}">(.*?)</div></td>',
                           part, re.DOTALL)
            return strip_tags(m.group(1)) if m else ""

        script_m = re.search(r'<pre><code>(.*?)</code></pre>', part, re.DOTALL)
        fix_script = html.unescape(script_m.group(1)).strip() if script_m else ""

        results[rid] = {
            "description": section("Description"),
            "rationale": section("Rationale"),
            "fix_script": fix_script,
        }
    return results


def apply_fix(scan_id: str, rule_id: str, fix_script: str) -> dict:
    """Run the exact SSG-provided script for one rule. Never called without
    a prior human confirmation at the API layer. Runs directly as root --
    no sudo wrapper needed since the whole service runs as root."""
    safe_name = re.sub(r'[^A-Za-z0-9_.-]', '_', rule_id)[:80]
    script_path = os.path.join(config.SCANS_DIR, f"{scan_id}-fix-{safe_name}.sh")
    with open(script_path, "w") as f:
        f.write("#!/bin/bash\nset -e\n" + fix_script + "\n")
    os.chmod(script_path, 0o750)

    proc = subprocess.run(
        ["/usr/bin/bash", script_path],
        capture_output=True, text=True, timeout=120,
    )
    return {
        "ok": proc.returncode == 0,
        "rule_id": rule_id,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }


def _explain_new_findings(new_fails: list, total_context: dict) -> dict:
    """Ask Ollama to explain ONLY the findings we've never seen before.
    Every failed item already has a vetted, pre-written fix script from the
    security content -- the model is explicitly told not to invent commands,
    only to explain priority and rationale."""
    prompt_fails = [
        {"rule": f["rule"], "rule_id": f["rule_id"], "severity": f["severity"],
         "rationale": (f.get("rationale") or "")[:400],
         "has_known_fix": bool(f.get("fix_script"))}
        for f in new_fails
    ]

    prompt = f"""You are a Linux security hardening assistant reviewing an OpenSCAP scan
of a database server. Every failed item already has a vetted, pre-written fix script
from the security content -- you are NOT writing or inventing any commands. Your job
is only to explain why each failure matters and which to fix first.

Overall scan context:
- Total rules checked: {total_context['total_rules_checked']}
- Results breakdown: {json.dumps(total_context['counts'])}

These specific failed checks have NOT been explained before and need a fresh
write-up:
{json.dumps(prompt_fails, indent=2)}

Respond with ONLY valid JSON, no markdown, in this exact shape:
{{
  "priorities": [
    {{"rule_id": "exact rule_id from above", "title": "short title", "why_it_matters": "1-2 sentences"}}
  ]
}}
"""
    try:
        resp = requests.post(
            config.OLLAMA_URL,
            json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json"},
            timeout=180,
        )
        resp.raise_for_status()
        return json.loads(resp.json().get("response", "{}"))
    except requests.exceptions.RequestException as e:
        return {"priorities": [], "_error": f"Ollama unreachable: {e}"}
    except json.JSONDecodeError:
        return {"priorities": [], "_error": "Model returned invalid JSON"}


def summarize_findings(parsed: dict) -> dict:
    """
    Turn parsed findings into a prioritized summary, reusing cached
    explanations for any rule that's failed before and only calling Ollama
    for genuinely new failures. This makes repeat scans much faster and
    keeps explanations consistent across runs.
    """
    _init_findings_cache()

    all_fails = parsed["fails"][: config.OSCAP_MAX_FINDINGS_FOR_LLM]
    from_cache = []
    need_explanation = []

    for f in all_fails:
        cached = _get_cached_recommendation(f["rule_id"])
        if cached:
            _touch_cached_recommendation(f["rule_id"])
            from_cache.append({**f, "recommendation": cached["recommendation"], "from_history": True, "times_seen": cached["times_seen"] + 1})
        else:
            need_explanation.append(f)

    new_priorities = []
    if need_explanation:
        explained = _explain_new_findings(need_explanation, parsed)
        new_priorities = explained.get("priorities", [])
        # Match back by rule_id directly -- far more reliable than the old
        # name-based matching, and the model is now asked for rule_id explicitly.
        by_rule_id = {f["rule_id"]: f for f in need_explanation}
        for item in new_priorities:
            match = by_rule_id.get(item.get("rule_id"))
            if match:
                _save_new_recommendation(match["rule_id"], match["rule"], match["severity"], item)

    cached_priorities = [
        {"rule_id": f["rule_id"], "title": f["recommendation"].get("title", f["rule"]),
         "why_it_matters": f["recommendation"].get("why_it_matters", ""),
         "from_history": True, "times_seen": f["times_seen"]}
        for f in from_cache
    ]

    # Rough overall risk from severity mix, since we no longer ask the model
    # for a single holistic judgment when most/all findings came from cache.
    high_count = sum(1 for f in all_fails if f["severity"] == "high")
    overall_risk = "high" if high_count else ("medium" if all_fails else "low")

    return {
        "overall_risk": overall_risk,
        "summary": f"{len(from_cache)} finding(s) matched known issues from previous scans; "
                   f"{len(need_explanation)} new finding(s) analyzed just now.",
        "priorities": cached_priorities + new_priorities,
        "cache_stats": {"from_history": len(from_cache), "newly_analyzed": len(need_explanation)},
    }


def _run_scan_thread(scan_id: str, profile: str):
    _write_status(scan_id, {
        "status": "running",
        "profile": profile,
        "started_at": datetime.now(timezone.utc).isoformat(),
    })

    results_xml = os.path.join(config.SCANS_DIR, f"{scan_id}-results.xml")
    report_html = os.path.join(config.SCANS_DIR, f"{scan_id}-report.html")

    oscap_cmd = [
        "oscap", "xccdf", "eval",
        "--profile", profile,
        "--results", results_xml,
        "--report", report_html,
        config.OSCAP_CONTENT,
    ]

    try:
        # No timeout here on purpose -- full profile scans can legitimately
        # take anywhere from a couple minutes to well over 15, depending on
        # profile and system load. This runs in its own background thread
        # (never inline in a web request), so an unbounded wait here doesn't
        # block Gunicorn, Apache, or anything else -- only this one scan_id's
        # status stays "running" until it's actually done.
        proc = subprocess.run(oscap_cmd, capture_output=True, text=True)

        # oscap exits non-zero when there are failed rules -- that's expected,
        # not an error. Only treat it as failed if the results file is missing.
        if not os.path.exists(results_xml):
            _write_status(scan_id, {
                "status": "error",
                "error": proc.stderr.strip()[:2000] or "oscap produced no results file",
            })
            return

        parsed = parse_xccdf_results(results_xml, config.OSCAP_CONTENT)

        # Pull description/rationale/fix_script out of the HTML report too --
        # this is where the actual runnable remediation script lives.
        top_ids = [f["rule_id"] for f in parsed["fails"][: config.OSCAP_MAX_FINDINGS_FOR_LLM]]
        details = parse_report_details(report_html, top_ids)
        for f in parsed["fails"][: config.OSCAP_MAX_FINDINGS_FOR_LLM]:
            f.update(details.get(f["rule_id"], {}))

        summary = summarize_findings(parsed)

        _write_status(scan_id, {
            "status": "done",
            "profile": profile,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "parsed": parsed,
            "summary": summary,
            "report_html_path": report_html,
        })

    except Exception as e:
        _write_status(scan_id, {"status": "error", "error": str(e)})


def start_scan(profile: str = None) -> str:
    """Kick off a scan in the background. Returns a scan_id to poll."""
    profile = profile or config.OSCAP_DEFAULT_PROFILE
    scan_id = uuid.uuid4().hex[:12]
    _write_status(scan_id, {"status": "queued", "profile": profile})
    thread = threading.Thread(target=_run_scan_thread, args=(scan_id, profile), daemon=True)
    thread.start()
    return scan_id


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "parse":
        print(json.dumps(parse_xccdf_results(sys.argv[2]), indent=2))
    else:
        sid = start_scan()
        print(f"Started scan {sid}. Poll with: python3 oscap_tool.py status {sid}")