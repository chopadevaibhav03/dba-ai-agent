"""
Report generator.

Takes an analysis result (from analyzer.analyze) and:
1. Saves it as a timestamped markdown file under reports/
2. Logs it into the SQLite 'reports' table for history/trend viewing.
"""

import json
import os
import sqlite3
from datetime import datetime, timezone

import config
from automation import WHITELIST


def init_reports_table():
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            severity TEXT,
            issue TEXT,
            root_cause TEXT,
            recommended_actions TEXT,
            explanation TEXT,
            raw_json TEXT,
            markdown_path TEXT
        )
        """
    )
    conn.commit()
    return conn


def render_markdown(result: dict) -> str:
    ts = result.get("_analyzed_at", datetime.now(timezone.utc).isoformat())
    severity = result.get("severity", "info").upper()
    actions = result.get("recommended_actions", [])

    action_lines = []
    for key in actions:
        if key in WHITELIST:
            action_lines.append(f"- **{key}** — {WHITELIST[key][0]}")
        else:
            action_lines.append(f"- {key} (not in whitelist -- will not auto-run)")
    actions_md = "\n".join(action_lines) if action_lines else "_No action recommended._"

    summary = result.get("_summary", {})

    return f"""# System health report

**Generated:** {ts}
**Severity:** {severity}

## Issue
{result.get('issue', 'n/a')}

## Root cause
{result.get('root_cause', 'n/a')}

## Recommended actions
{actions_md}

## Why
{result.get('explanation', 'n/a')}

## Metrics snapshot
```json
{json.dumps(summary, indent=2)}
```
"""


def generate_and_save(result: dict) -> str:
    """Render, write to disk, log to DB. Returns the markdown file path."""
    conn = init_reports_table()

    md = render_markdown(result)
    ts = result.get("_analyzed_at", datetime.now(timezone.utc).isoformat())
    fname = ts.replace(":", "-").replace(".", "-") + ".md"
    path = os.path.join(config.REPORTS_DIR, fname)

    with open(path, "w") as f:
        f.write(md)

    conn.execute(
        """
        INSERT INTO reports (ts, severity, issue, root_cause, recommended_actions, explanation, raw_json, markdown_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts,
            result.get("severity"),
            result.get("issue"),
            result.get("root_cause"),
            json.dumps(result.get("recommended_actions", [])),
            result.get("explanation"),
            json.dumps(result),
            path,
        ),
    )
    conn.commit()
    conn.close()
    return path


if __name__ == "__main__":
    from analyzer import analyze

    result = analyze()
    path = generate_and_save(result)
    print(f"Report saved to {path}")
    print(render_markdown(result))
