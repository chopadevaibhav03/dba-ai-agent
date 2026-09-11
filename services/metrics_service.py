import json
import sqlite3

import config


def get_latest_metrics() -> dict:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        row = conn.execute(
            "SELECT * FROM metrics ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return {
            "ok": False,
            "error": "No metrics yet",
        }

    sample = dict(row)

    sample["disk"] = json.loads(
        sample.pop("disk_json") or "{}"
    )

    return {
        "ok": True,
        "sample": sample,
    }


def get_metrics_history(limit: int = 200) -> dict:
    limit = min(max(limit, 1), 1000)

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        rows = conn.execute(
            """
            SELECT
                ts,
                cpu_percent,
                mem_percent,
                swap_percent
            FROM metrics
            ORDER BY ts DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    samples = [dict(row) for row in rows][::-1]

    return {
        "ok": True,
        "samples": samples,
    }