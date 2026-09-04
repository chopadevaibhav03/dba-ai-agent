"""
Central configuration for the OS monitoring agent.
Edit thresholds here to tune when the agent flags a problem.
"""

import os

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "metrics.db")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# --- Collector ---
POLL_INTERVAL_SECONDS = 10       # how often to sample metrics
DISK_MOUNTS = ["/"]              # add more mount points if needed, e.g. ["/", "/var", "/home"]

# --- Ollama ---
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

# --- Thresholds (percent) that trigger an "analyze now" worthy condition ---
THRESHOLDS = {
    "cpu_percent": 85,
    "mem_percent": 85,
    "swap_percent": 50,     # any real swap usage is worth flagging
    "disk_percent": 90,
}

# --- Automation safety ---
# Automation NEVER runs unless explicitly confirmed (UI button or confirm=True).
# Only actions in automation.py's WHITELIST can ever be executed.
REQUIRE_CONFIRMATION = True

# --- OpenSCAP ---
OSCAP_CONTENT = "/usr/share/xml/scap/ssg/content/ssg-rhel8-ds.xml"
OSCAP_DEFAULT_PROFILE = "xccdf_org.ssgproject.content_profile_cis"
SCANS_DIR = os.path.join(BASE_DIR, "scans")
# OSCAP_SCAN_TIMEOUT_SECONDS removed -- scans run unbounded in a background
# thread now, since profile scans can legitimately take anywhere from a
# couple minutes to 15+ depending on load. Nothing else blocks on this.
OSCAP_MAX_FINDINGS_FOR_LLM = 15      # cap what gets sent to the model, keep prompts small