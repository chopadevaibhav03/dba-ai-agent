"""
OS metrics collector.

Samples CPU, RAM, swap, and disk usage using psutil and writes each
sample into a local SQLite database. Run this as a long-lived process
(directly, or as a systemd service) to build up a time-series history.

Usage:
    python3 collector.py            # run forever, sampling every POLL_INTERVAL_SECONDS
    python3 collector.py --once     # take a single sample and print it (good for testing)
"""

import json
import sqlite3
import sys
import time
from datetime import datetime, timezone

import psutil

import config


def init_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            cpu_percent REAL,
            load_avg_1 REAL,
            load_avg_5 REAL,
            load_avg_15 REAL,
            mem_percent REAL,
            mem_used_mb REAL,
            mem_available_mb REAL,
            swap_percent REAL,
            swap_used_mb REAL,
            disk_json TEXT
        )
        """
    )
    conn.commit()
    return conn


def collect_sample() -> dict:
    """Collect one snapshot of OS metrics. Pure function -- no DB access."""
    cpu_percent = psutil.cpu_percent(interval=1)  # 1s sample window
    load1, load5, load15 = (0.0, 0.0, 0.0)
    if hasattr(psutil, "getloadavg"):
        load1, load5, load15 = psutil.getloadavg()

    vmem = psutil.virtual_memory()
    swap = psutil.swap_memory()

    disk_usage = {}
    for mount in config.DISK_MOUNTS:
        try:
            du = psutil.disk_usage(mount)
            disk_usage[mount] = {
                "percent": du.percent,
                "used_gb": round(du.used / (1024**3), 2),
                "total_gb": round(du.total / (1024**3), 2),
            }
        except FileNotFoundError:
            # mount point doesn't exist on this system, skip it
            continue

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "cpu_percent": cpu_percent,
        "load_avg_1": load1,
        "load_avg_5": load5,
        "load_avg_15": load15,
        "mem_percent": vmem.percent,
        "mem_used_mb": round(vmem.used / (1024**2), 1),
        "mem_available_mb": round(vmem.available / (1024**2), 1),
        "swap_percent": swap.percent,
        "swap_used_mb": round(swap.used / (1024**2), 1),
        "disk": disk_usage,
    }


def save_sample(conn: sqlite3.Connection, sample: dict):
    conn.execute(
        """
        INSERT INTO metrics
            (ts, cpu_percent, load_avg_1, load_avg_5, load_avg_15,
             mem_percent, mem_used_mb, mem_available_mb,
             swap_percent, swap_used_mb, disk_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sample["ts"],
            sample["cpu_percent"],
            sample["load_avg_1"],
            sample["load_avg_5"],
            sample["load_avg_15"],
            sample["mem_percent"],
            sample["mem_used_mb"],
            sample["mem_available_mb"],
            sample["swap_percent"],
            sample["swap_used_mb"],
            json.dumps(sample["disk"]),
        ),
    )
    conn.commit()


def run_forever():
    conn = init_db()
    print(f"Collector started. Sampling every {config.POLL_INTERVAL_SECONDS}s. DB: {config.DB_PATH}")
    try:
        while True:
            sample = collect_sample()
            save_sample(conn, sample)
            print(
                f"[{sample['ts']}] cpu={sample['cpu_percent']}% "
                f"mem={sample['mem_percent']}% swap={sample['swap_percent']}%"
            )
            time.sleep(config.POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nCollector stopped.")
    finally:
        conn.close()


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(json.dumps(collect_sample(), indent=2))
    else:
        run_forever()
