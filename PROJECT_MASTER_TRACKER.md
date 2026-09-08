# DBA AI Agent — Master Project Tracker

> Living project document. Update this file after every meaningful implementation, test, decision, problem, fix, Git checkpoint, and architecture change.
>
> **GitHub:** https://github.com/chopadevaibhav03/dba-ai-agent  
> **Active branch:** `stage-1-foundation`  
> **Current milestone:** Stage 1 Linux + Oracle foundation in progress; Oracle health verified, FastAPI/unified health and AI orchestration remain.

---

# 1. Project Vision

Build a local AI-assisted operations platform for Linux/RHEL monitoring, Oracle DBA operations, OpenSCAP security/compliance, VAPT analysis, Ollama-based local AI, human-in-the-loop approval, controlled remediation, verification, reporting, audit/history, and future Zabbix/RAG/Ansible/Salt integrations.

## Core Principle

**The LLM is the reasoning/orchestration layer — not the privileged executor.**

```text
User
  |
  v
FastAPI
  |
  v
AI Orchestrator
  |
  v
Tool Registry
  |
  v
Deterministic Python Tool
  |
  +--> Linux
  +--> Oracle
  +--> OSCAP
```

Forbidden:

```text
LLM ---> arbitrary shell
LLM ---> arbitrary SQL
```

---

# 2. Project History

## Stage 0 — Existing OS Agent

The original project contained:

```text
collector.py
analyzer.py
automation.py
service_control.py
chat_agent.py
oscap_tool.py
report.py
api.py
app.py
tools.py
config.py
static/
deploy/
docs/
```

Capabilities included Linux metrics collection, SQLite persistence, Ollama analysis, Flask API, Streamlit UI, service control, controlled automation, OpenSCAP scanning, reporting/history, Apache deployment, and systemd services.

### Stage 0 checkpoint

```text
v0.1.0-stage0
```

---

# 3. Stage 1 Architecture

```text
                         +----------------------+
                         |       WEB UI         |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |       APACHE         |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |       FASTAPI        |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |   AI ORCHESTRATOR    |
                         | Ollama / Llama 3.2:3b|
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |    TOOL REGISTRY     |
                         | Explicit + Bounded   |
                         +----+--------+--------+
                              |        |        |
                 +------------+        |        +-------------+
                 |                     |                      |
                 v                     v                      v
          +-------------+       +-------------+        +-------------+
          | Linux Tools |       |Oracle Tools |        | OSCAP Tools |
          +------+------+       +------+------+        +------+------+
                 |                     |                      |
                 v                     v                      v
               RHEL                Oracle 19c             OpenSCAP
```

Persistence:

```text
Linux / Oracle / OSCAP / Findings / Reports / Metrics
                         |
                         v
                       SQLite
```

---

# 4. Stage 1 Roadmap

| Step | Work | Status |
|---|---|---|
| 1 | Architecture documentation | DONE |
| 2 | FastAPI foundation | DONE |
| 3 | Migrate existing API endpoints | IN PROGRESS |
| 4 | Validate Linux agent | DONE |
| 5 | Formal tool registry | DONE |
| 6 | Oracle connection layer | DONE |
| 7 | Oracle read-only tools | DONE |
| 8 | Oracle health service | DONE |
| 9 | Expose Oracle health via FastAPI | NEXT |
| 10 | Unified Linux + Oracle health | PLANNED |
| 11 | Complete FastAPI endpoint migration | IN PROGRESS |
| 12 | Validate UI against FastAPI | IN PROGRESS |
| 13 | Ollama + Linux + Oracle orchestration | PLANNED |
| 14 | Structured AI output | PLANNED |
| 15 | Risk / policy / approval / audit | PLANNED |
| 16 | Automated tests + security hardening | PLANNED |
| 17 | OSCAP Tool Registry integration | PLANNED |
| 18 | Stage 1 regression + release tag | PLANNED |

---

# 5. Current Environment

| Component | Current state |
|---|---|
| Host OS | Red Hat Enterprise Linux 8.10 |
| Kernel | 4.18.0-372.9.1.el8.x86_64 |
| Architecture | x86_64 |
| CPU | 4 physical / 4 logical |
| RAM | 15.46 GB |
| Swap | 7.89 GB |
| Hostname | vaibhav.localdomain |
| Network | ens18 / 192.168.2.213 |
| FastAPI development port | 8801 |
| Legacy Flask/Gunicorn | 127.0.0.1:8800 |
| Apache | Port 80 |
| Ollama | 127.0.0.1:11434 |
| Model | llama3.2:3b |
| OpenSCAP | 1.3.14 |
| Oracle | 19c Enterprise Edition |
| CDB | ORCLCDB |
| PDB | ORCLPDB1 |

---

# 6. Git and GitHub

Repository:

```text
https://github.com/chopadevaibhav03/dba-ai-agent
```

Branch model:

```text
main
 |
 +-- v0.1.0-stage0
 |
 +-- stage-1-foundation
       |
       +-- FastAPI
       +-- Metrics
       +-- Tool Registry
       +-- Linux tools
       +-- Linux health
       +-- Oracle
       +-- Unified health
       +-- AI orchestration
```

Do not develop directly on `main`.

Typical workflow:

```bash
cd /home/test/opt/os-agent
git status
git diff --stat
git add .
git commit -m "feat: <short description>"
git push origin stage-1-foundation
```

Checkpoint:

```bash
git tag -a v0.x.x-<milestone> -m "<description>"
git push origin v0.x.x-<milestone>
```

### Current checkpoint

```text
v0.2.0-stage1-linux
```

Meaning: Linux monitoring, tool registry, and Linux health foundation is checkpointed before Oracle work.

---

# 7. Current Project Structure

```text
dba-ai-agent/
├── core/
│   ├── fastapi_app.py
│   └── tool_registry.py
├── services/
│   ├── metrics_service.py
│   └── linux_health_service.py
├── tools/
│   └── linux.py
├── static/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── deploy/
│   ├── os-agent-apache.conf
│   ├── os-agent-collector.service
│   └── os-agent-web.service
├── docs/
│   ├── DEPLOY_RUNBOOK.md
│   └── PROJECT_LOG.md
├── collector.py
├── analyzer.py
├── automation.py
├── service_control.py
├── chat_agent.py
├── oscap_tool.py
├── report.py
├── api.py
├── app.py
├── requirements.txt
└── README.md
```

---

# 8. Achievements

- Preserved Stage 0 and created a rollback baseline.
- Documented Stage 1 architecture.
- Created FastAPI foundation.
- Added `/api/health`.
- Added metrics service.
- Migrated `/api/metrics/latest`.
- Migrated `/api/metrics/history`.
- FastAPI serves the static UI.
- Created a formal central tool registry.
- Expanded Linux monitoring from 4 to 18 read-only tools.
- Created Linux health aggregation.
- Added deterministic health thresholds.
- Added per-tool error isolation.
- Prevented false disk alerts from removable/media/pseudo-filesystems.
- Verified the host as RHEL 8.10.
- Established GitHub branch/tag workflow.

---

# 9. FastAPI Foundation

Application:

```text
DBA AI Agent
version: 0.2.0-stage1
```

Development:

```bash
uvicorn core.fastapi_app:app --host 0.0.0.0 --port 8801
```

Temporary browser access:

```text
http://192.168.2.213:8801/
```

Final architecture:

```text
Browser
  |
  v
Apache :80
  |
  v
FastAPI 127.0.0.1:8801
```

FastAPI should ultimately be localhost-only behind Apache.

---

# 10. Metrics Service

Created:

```text
services/metrics_service.py
```

Functions:

```python
get_latest_metrics()
get_metrics_history(limit)
```

Endpoints:

```text
GET /api/metrics/latest
GET /api/metrics/history
```

---

# 11. Tool Registry

Created:

```text
core/tool_registry.py
```

Purpose: central registry for all AI-callable tools.

Security properties:

- Explicit registration
- Exact tool names
- Read-only flag
- Category
- Deterministic Python function
- Unknown tools rejected
- Non-read-only tools rejected during read-only phase

Representative design:

```python
from tools.linux import LINUX_TOOLS

TOOLS = {}

for name, function in LINUX_TOOLS.items():
    TOOLS[name] = {
        "description": "...",
        "function": function,
        "read_only": True,
        "category": "linux",
    }

def execute_tool(name: str, **kwargs):
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")

    tool = TOOLS[name]

    if not tool["read_only"]:
        raise PermissionError(
            f"Tool '{name}' is not allowed in read-only mode"
        )

    return tool["function"](**kwargs)
```

---

# 12. Linux Tool Inventory

Current 18 tools:

```text
linux.system_info
linux.cpu
linux.memory
linux.swap
linux.load
linux.disk
linux.inodes
linux.top_processes
linux.process_summary
linux.network_interfaces
linux.network_stats
linux.listening_ports
linux.failed_services
linux.journal_errors
linux.failed_logins
linux.selinux
linux.firewall
linux.logged_in_users
```

| Tool | Purpose |
|---|---|
| `linux.system_info` | OS, distribution, hostname/FQDN, kernel, architecture, CPU cores, boot time, uptime |
| `linux.cpu` | CPU utilization and load |
| `linux.memory` | RAM utilization and memory details |
| `linux.swap` | Swap usage and swap I/O |
| `linux.load` | 1/5/15-minute load and load per CPU |
| `linux.disk` | Mounted filesystem capacity/utilization |
| `linux.inodes` | Inode utilization |
| `linux.top_processes` | Top CPU/memory processes |
| `linux.process_summary` | Process count/state summary |
| `linux.network_interfaces` | Interfaces, addresses, state, MTU |
| `linux.network_stats` | RX/TX traffic, errors and drops |
| `linux.listening_ports` | TCP/UDP listening ports and PIDs |
| `linux.failed_services` | Failed systemd services |
| `linux.journal_errors` | Recent journal errors |
| `linux.failed_logins` | Recent authentication failures |
| `linux.selinux` | SELinux state/enforcement/configuration |
| `linux.firewall` | Firewall state/zones |
| `linux.logged_in_users` | Current login sessions |

---

# 13. Linux Health Service

Created:

```text
services/linux_health_service.py
```

Endpoint:

```text
GET /api/linux/health
```

Architecture:

```text
/api/linux/health
       |
       v
Linux Health Service
       |
       +--> 18 registered Linux tools
       |
       v
Deterministic Health Calculation
       |
       v
healthy / warning / critical
```

Error isolation:

```python
def _run_tool(tool_name: str) -> dict:
    try:
        result = execute_tool(tool_name)

        if isinstance(result, dict):
            return result

        return {"ok": True, "data": result}

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)
        }
```

---

# 14. Linux Health Rules

| Metric | Warning | Critical |
|---|---:|---:|
| CPU | >= 85% | >= 95% |
| Memory | >= 85% | >= 95% |
| Swap | >= 90% | — |
| Persistent filesystem | >= 85% | >= 95% |
| Failed systemd service | — | Any failed service |
| SELinux | Not enforcing | — |
| Firewall | Inactive | — |

These thresholds can later become configurable/policy-driven.

---

# 15. Disk Handling

A mounted RHEL ISO reports 100% usage:

```text
/run/media/test/RHEL-8-6-0-BaseOS-x86_64
```

This is expected because the ISO is read-only.

Ignored for persistent disk health:

```text
/run/media/
/media/
/mnt/
/dev/
/proc/
/sys/
/run/
```

---

# 16. Current Linux Health Result

Latest verified result:

```text
Overall: WARNING
Critical: 0
Warnings: 2
```

Warnings:

```text
1. SELinux is not currently enforcing.
2. Firewall does not appear to be active.
```

Observed:

| Area | Value |
|---|---:|
| CPU | 39.2% |
| Memory | 62.7% |
| Swap | 10.9% |
| Root filesystem | 70.4% used |
| Processes | ~351 |
| Running | 1 |
| Zombie | 0 |
| Listening entries | 34 |
| Failed services | 0 |
| Logged-in users | 4 |
| Recent failed logins | 7 |

---

# 17. Ollama

Local endpoint:

```text
http://127.0.0.1:11434
```

Model:

```text
llama3.2:3b
```

Verification:

```bash
ollama list
curl -s http://127.0.0.1:11434/api/tags | python -m json.tool
```

Planned AI responsibilities:

- Intent understanding
- Tool selection
- Diagnosis explanation
- Recommendation generation
- Finding summarization
- Natural-language interaction

The model does not receive arbitrary OS/database privileges.

---

# 18. Oracle Environment

Oracle:

```text
Oracle Database 19c Enterprise Edition
19.3.0.0.0
```

CDB:

```text
ORCLCDB
```

PDB:

```text
ORCLPDB1
```

Known state:

```text
ORCLCDB  = OPEN / READ WRITE / CDB
ORCLPDB1 = READ WRITE
PDB$SEED = READ ONLY
```

Important:

```bash
echo $ORACLE_SID
```

may be empty when executed as `root`. The application must use an explicit DSN/configuration rather than relying on the `oracle` user's interactive shell environment.

---

# 20. Oracle Implementation — Completed Foundation

## 19.1 Oracle Connection Verification

Verified on the RHEL host from the project Python 3.11 virtual environment:

```text
Python 3.11.13
oracledb 4.0.2
DSN: 192.168.2.213:1521/ORCLPDB1
USER: system
```

Successful connection result:

```text
connected: True
db_name: ORCLPDB1
service_name: orclpdb1
instance_name: ORCLCDB
```

The listener is reachable on `192.168.2.213:1521`. The application must use explicit DSN/configuration rather than the interactive `oracle` user's `ORACLE_SID`.

## 19.2 Oracle Service

Created and verified:

```text
services/oracle_service.py
```

The service exposes only fixed, read-only operations:

```text
test_connection()
database_info()
instance_info()
pdbs()
tablespaces()
sessions()
blocking_sessions()
```

There is intentionally no `execute_any_sql()` interface.

## 19.3 Oracle Tool Registry

Created:

```text
tools/oracle.py
```

Registered Oracle tools:

```text
oracle.connection
oracle.database_info
oracle.instance_info
oracle.pdbs
oracle.tablespaces
oracle.sessions
oracle.blocking_sessions
```

All seven are registered as read-only tools alongside the 18 Linux tools, for a current total of **25 registered tools**. Direct execution through `core.tool_registry.execute_tool()` was verified.

## 19.4 Oracle Health Service

Created and verified:

```text
services/oracle_health_service.py
```

The service calls registered Oracle tools and deterministically calculates `healthy`, `warning`, or `critical`. Tool execution errors are treated as health concerns rather than silently producing a healthy result.

Latest verified Oracle health:

```text
status: critical
critical_count: 1
warning_count: 1
errors: []
```

Findings observed during verification:

```text
SYSTEM   97.19%  -> CRITICAL
SYSAUX   93.73%  -> WARNING
```

Connection remained healthy:

```text
ORCLPDB1 / orclpdb1 / ORCLCDB
```

No blocking sessions were reported during the tool verification.

## 19.5 Oracle Configuration

Development configuration is kept outside Python source code in a protected file:

```text
/home/test/opt/os-agent/.oracle.env
```

The file is intended to be root-owned with mode `600` and must be excluded from Git. The password must never be committed to the repository or documentation. Production systemd configuration still needs to consume this configuration securely.

## 19.6 Oracle Architecture Checkpoint

```text
FastAPI
   |
   v
Tool Registry
   |
   +--> oracle.connection
   +--> oracle.database_info
   +--> oracle.instance_info
   +--> oracle.pdbs
   +--> oracle.tablespaces
   +--> oracle.sessions
   +--> oracle.blocking_sessions
              |
              v
       oracle_service.py
              |
              v
          Oracle 19c
          ORCLCDB
             |
             +--> ORCLPDB1
```

**Next Oracle task:** expose the verified health service through FastAPI as `GET /api/oracle/health`, then build unified Linux + Oracle health.

---

# 20. Oracle — Next Implementation

Verify driver:

```bash
cd /home/test/opt/os-agent
source venv/bin/activate
python -c "import oracledb; print('oracledb:', oracledb.__version__)"
```

If missing:

```bash
pip install oracledb
```

Direct test:

```python
import oracledb

connection = oracledb.connect(
    user="system",
    password="YOUR_PASSWORD",
    dsn="127.0.0.1:1521/ORCLPDB1"
)

print("Oracle connection successful")

cursor = connection.cursor()
cursor.execute("""
    SELECT
        sys_context('USERENV', 'DB_NAME'),
        sys_context('USERENV', 'SERVICE_NAME')
    FROM dual
""")

print(cursor.fetchone())
cursor.close()
connection.close()
```

Expected:

```text
Oracle connection successful
('ORCLCDB', 'ORCLPDB1')
```

Do not hard-code credentials.

Planned configuration:

```text
ORACLE_USER
ORACLE_PASSWORD
ORACLE_DSN
```

---

# 21. Planned Oracle Structure

```text
services/
├── metrics_service.py
├── linux_health_service.py
├── oracle_service.py
└── oracle_health_service.py

tools/
├── linux.py
└── oracle.py
```

---

# 22. Planned Oracle Tools

| Tool | Purpose |
|---|---|
| `oracle.database_info` | Database name, open mode, role, CDB state |
| `oracle.instance_info` | Instance status, host, version, startup time |
| `oracle.pdbs` | PDB names, open modes, restricted state |
| `oracle.tablespaces` | Capacity, free space, utilization |
| `oracle.sessions` | Session counts and selected session information |
| `oracle.blocking_sessions` | Blocking/blocked session relationships |
| `oracle.health` | Deterministic Oracle health summary |

Initial rule:

```text
ALL ORACLE TOOLS = READ ONLY
```

There will be no `execute_any_sql()` endpoint.

---

# 23. Oracle Architecture

```text
FastAPI
   |
   v
AI Orchestrator
   |
   v
Tool Registry
   |
   +--> oracle.database_info
   +--> oracle.instance_info
   +--> oracle.pdbs
   +--> oracle.tablespaces
   +--> oracle.sessions
   +--> oracle.blocking_sessions
   +--> oracle.health
              |
              v
        Python oracledb
              |
              v
         Oracle 19c
         ORCLCDB
            |
            +--> ORCLPDB1
```

---

# 24. Unified Linux + Oracle Health

Desired question:

```text
"Is my Linux server and Oracle database healthy?"
```

```text
User
 |
 v
FastAPI
 |
 v
AI Orchestrator
 |
 +---------------------+
 |                     |
 v                     v
Linux Health       Oracle Health
 |                     |
 v                     v
18 tools             7 tools
 |                     |
 +----------+----------+
            |
            v
Unified deterministic health
            |
            v
AI explanation
```

Python determines the underlying health state. AI explains and prioritizes evidence.

---

# 25. Planned AI Orchestration

```text
User Question
      |
      v
FastAPI
      |
      v
AI Orchestrator
      |
      +--> Intent
      +--> Registered tool selection
      |
      v
Tool Registry
      |
      v
Deterministic Tool
      |
      v
Structured Result
      |
      v
Ollama / Llama 3.2:3b
      |
      v
Diagnosis / Explanation / Recommendation
```

Tool selection must remain constrained to registered tools.

---

# 26. Future Risk / Approval / Remediation

```text
FINDING
   |
   v
AI ANALYSIS
   |
   v
RISK CLASSIFIER
   |
   +---- LOW ------> limited pre-approved action
   |
   +---- MEDIUM ---> HUMAN APPROVAL
   |
   +---- HIGH -----> HUMAN APPROVAL / NO AUTO ACTION
                         |
                         v
                      EXECUTOR
                         |
                         v
                       VERIFY
                         |
                         v
                       REPORT
                         |
                         v
                       AUDIT
```

The LLM must never directly execute arbitrary shell or SQL.

---

# 27. Human Approval

Future flow:

```text
Finding
  |
  v
Proposed Action
  |
  v
Risk Classification
  |
  v
Pending Approval Record
  |
  v
Human Approves / Rejects
  |
  v
Server validates approval
  |
  v
Controlled Executor
```

A browser/client flag such as `confirm=true` must not be the final authorization mechanism.

---

# 28. Verification

Every write operation should follow:

```text
BEFORE STATE
     |
     v
APPROVED ACTION
     |
     v
EXECUTION
     |
     v
AFTER STATE
     |
     v
VERIFICATION
```

Then:

```text
REPORT
  |
  v
AUDIT
```

---

# 29. OpenSCAP Roadmap

Installed:

```text
/usr/bin/oscap
OpenSCAP 1.3.14
```

Supported:

```text
SCAP 1.3
XCCDF 1.2
OVAL 5.11.1
CPE 2.3
CVSS 2.0
CVE 2.0
```

Future standardized flow:

```text
Tool Registry
     |
     v
OSCAP Tools
     |
     v
Scan
     |
     v
Parse / Normalize
     |
     v
Finding Model
     |
     v
AI Explanation
     |
     v
Risk / Approval / Remediation
```

Actual host is RHEL 8.10, so final SCAP content/profile selection must match that platform.

---

# 29. VAPT Roadmap

```text
Asset Discovery
      |
      v
Allowed Scan Scope
      |
      v
Vulnerability / Exposure Checks
      |
      v
Finding Normalization
      |
      v
AI Explanation
      |
      v
Risk Classification
      |
      +--> Evidence
      +--> Recommendation
      +--> Approval
      |
      v
Controlled Remediation
      |
      v
Verification
      |
      v
Report + Audit
```

VAPT must remain controlled and scoped. The LLM should not become an unrestricted autonomous exploitation engine.

---

# 30. Zabbix — Future

Zabbix will provide metrics, history, events, triggers, and monitoring state.

```text
Zabbix
  |
  v
Integration Layer
  |
  v
AI Orchestrator
  |
  v
Tool Registry
  |
  +--> Analysis
  +--> Recommendation
  +--> Approval
  +--> Controlled Action
```

Zabbix is a monitoring source, not the AI brain.

---

# 31. RAG — Future

Useful trusted knowledge:

- DBA SOPs
- Linux runbooks
- Security standards
- Hardening guides
- Approved remediation procedures
- Architecture documents
- Operational policies

```text
User / Finding
      |
      v
AI Orchestrator
      |
      +--> Live tool data
      +--> Trusted RAG knowledge
      |
      v
Context-aware recommendation
      |
      v
Risk / Approval
```

RAG should be added after live tools and finding models are stable.

---

# 32. Ansible / Salt — Future

They should become controlled execution backends only after the approval architecture is stable.

Preferred:

```text
Finding
  |
  v
Risk Policy
  |
  v
Human Approval
  |
  v
Approved Execution Plan
  |
  v
Ansible / Salt
  |
  v
Verification
  |
  v
Audit
```

Not:

```text
LLM --> Ansible --> anything
```

---

# 33. API Roadmap

| Endpoint | Purpose | Status |
|---|---|---|
| `GET /api/health` | FastAPI service health | DONE |
| `GET /api/metrics/latest` | Latest metrics | DONE |
| `GET /api/metrics/history` | Metric history | DONE |
| `GET /api/tools` | Registered tools | DONE |
| `GET /api/tools/{tool_name}` | Registered read-only tool | DONE |
| `GET /api/linux/health` | Aggregate Linux health | DONE |
| `GET /api/oracle/database` | Oracle database info | PLANNED |
| `GET /api/oracle/instance` | Oracle instance info | PLANNED |
| `GET /api/oracle/pdbs` | PDB status | PLANNED |
| `GET /api/oracle/tablespaces` | Tablespace health | PLANNED |
| `GET /api/oracle/sessions` | Session information | PLANNED |
| `GET /api/oracle/blocking` | Blocking sessions | PLANNED |
| `GET /api/oracle/health` | Aggregate Oracle health | PLANNED |

---

# 34. Deployment Architecture

Development:

```text
Windows Browser
      |
      v
192.168.2.213:8801
      |
      v
Uvicorn / FastAPI
```

Target:

```text
Windows Browser
      |
      v
RHEL :80
      |
      v
Apache
      |
      v
FastAPI :8801 localhost-only
      |
      +--> Ollama :11434 localhost
      +--> SQLite
      +--> Linux
      +--> Oracle :1521
      +--> OpenSCAP
```

---

# 35. Testing Commands

## FastAPI

```bash
curl -s http://127.0.0.1:8801/api/health | python -m json.tool
curl -s http://127.0.0.1:8801/api/tools | python -m json.tool
curl -s http://127.0.0.1:8801/api/linux/health | python -m json.tool
```

## Linux tools

```bash
curl -s http://127.0.0.1:8801/api/tools/linux.cpu | python -m json.tool
curl -s http://127.0.0.1:8801/api/tools/linux.memory | python -m json.tool
curl -s http://127.0.0.1:8801/api/tools/linux.swap | python -m json.tool
curl -s http://127.0.0.1:8801/api/tools/linux.selinux | python -m json.tool
```

## Syntax

```bash
python -m py_compile \
  core/fastapi_app.py \
  core/tool_registry.py \
  services/metrics_service.py \
  services/linux_health_service.py \
  tools/linux.py
```

## Processes

```bash
ps -ef | grep -E "uvicorn|gunicorn" | grep -v grep
```

## Services

```bash
sudo systemctl status os-agent-collector --no-pager
sudo systemctl status os-agent-web --no-pager
sudo systemctl status httpd --no-pager
sudo systemctl status ollama --no-pager
```

## Network

```bash
ss -lntup
```

## SELinux

```bash
getenforce
sestatus
```

## Firewall

```bash
systemctl status firewalld --no-pager
firewall-cmd --state 2>/dev/null || true
```

## OpenSCAP

```bash
which oscap
oscap --version
```

## Ollama

```bash
ollama list
curl -s http://127.0.0.1:11434/api/tags | python -m json.tool
```

---

# 36. Problems Encountered and Fixes

## FastAPI `/` returned 404

**Cause:** static root route was missing.

**Fix:** mount `/static` and serve `index.html` at `/`.

**Result:** UI worked.

## Browser could not reach development FastAPI

**Cause:** service was bound to localhost.

**Temporary fix:**

```bash
uvicorn core.fastapi_app:app --host 0.0.0.0 --port 8801
```

**Result:** browser testing worked.

**Final:** localhost-only behind Apache.

## Tool registry initially showed only 4 tools

**Cause:** running Uvicorn process had stale imports/process state.

**Fix:** restart FastAPI.

**Result:** 18 Linux tools became visible.

## Malformed curl

Two commands were accidentally concatenated.

**Lesson:** execute validation commands separately.

## RHEL ISO showed 100% disk

**Cause:** ISO9660 read-only media.

**Fix:** filter removable/media/pseudo-filesystems.

## UI was messy

**Cause:** early UI assumptions did not match all actual API structures.

**Decision:** stabilize backend contracts first; redesign UI later.

---

# 37. Security Observations

## SELinux

```text
Enabled
Current mode: permissive
Configured mode: enforcing
```

Health warning.

## Firewall

```text
inactive
```

Health warning.

## Failed SSH Attempts

Seven recent failed authentication events were observed from:

```text
192.168.2.37
```

They involved an invalid user string resembling:

```text
su - oracle
```

This is a security event requiring investigation, not automatic proof of malicious intent.

## SELinux Denials

Journal errors include SELinux denials involving the Python 3.11 virtual environment under:

```text
/home/test/opt/os-agent
```

Do not automatically modify policy during the read-only phase.

## Listening Services

Observed important ports include:

```text
22     SSH
80     Apache
1521   Oracle
3000   Grafana
3306   MySQL
8801   FastAPI
11434  Ollama
```

Later work should classify expected versus unexpected exposure.

---

# 38. Security Hardening Required

Before production remediation:

1. Remove arbitrary shell execution patterns.
2. Replace `shell=True` with fixed argument execution.
3. Reduce service privileges.
4. Keep FastAPI localhost-only behind Apache.
5. Add server-side approval state.
6. Add authentication/authorization for management endpoints.
7. Add audit records.
8. Validate tool arguments.
9. Prevent arbitrary SQL.
10. Prevent arbitrary commands.
11. Protect secrets.
12. Align OpenSCAP content with RHEL 8.10.
13. Verify every write operation.
14. Provide rollback where possible.

---

# 39. Configuration and Secrets

Planned:

```text
ORACLE_USER=system
ORACLE_PASSWORD=<secret>
ORACLE_DSN=127.0.0.1:1521/ORCLPDB1

OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

Never commit passwords, API keys, SSH credentials, tokens, private certificates, or secrets.

---

# 40. Oracle Milestone Acceptance Criteria

- [ ] `oracledb` imports successfully.
- [ ] Python connects to Oracle.
- [ ] DSN uses `127.0.0.1:1521/ORCLPDB1`.
- [ ] Credentials are externalized.
- [ ] Connection failures are structured.
- [ ] Oracle connection service exists.
- [ ] No arbitrary SQL endpoint exists.
- [ ] All Oracle tools registered.
- [ ] All initial Oracle tools are read-only.
- [ ] Database info works.
- [ ] Instance info works.
- [ ] PDB info works.
- [ ] Tablespace info works.
- [ ] Session info works.
- [ ] Blocking-session info works.
- [ ] Oracle health works.

---

# 41. Stage 1 Success Criteria

The platform should reliably answer:

```text
"Is my Linux server and Oracle database healthy?"
```

using:

```text
Linux evidence
+
Oracle evidence
+
Deterministic health logic
+
AI explanation
```

without giving the LLM direct arbitrary execution privileges.

---

# 42. Known Technical Debt

- README has older `/opt/os-agent` references.
- Actual deployment path is `/home/test/opt/os-agent`.
- Flask migration is incomplete.
- Streamlit remains legacy.
- Legacy automation needs hardening.
- Some systemd services run with high privileges.
- FastAPI needs final Apache-only deployment.
- Frontend needs a complete data-model-aligned redesign.
- Chart.js currently uses a CDN.
- Approval workflow needs backend state.
- Audit model needs formalization.
- OpenSCAP content/profile needs RHEL 8.10 alignment.
- Oracle integration has not started.
- Unified health has not started.
- AI orchestration has not started.

---

# 43. Final Implementation Order

1. Verify Git checkpoint.
2. Verify/install `python-oracledb`.
3. Test direct Oracle connectivity.
4. Create `services/oracle_service.py`.
5. Create `tools/oracle.py`.
6. Add deterministic read-only Oracle SQL.
7. Register Oracle tools.
8. Add Oracle API endpoints.
9. Create `oracle_health_service.py`.
10. Combine Linux + Oracle health.
11. Integrate Ollama tool calling.
12. Add structured AI responses.
13. Add finding/event persistence.
14. Add risk classification.
15. Add approval workflow.
16. Add controlled execution.
17. Add verification.
18. Add audit trail.
19. Standardize OpenSCAP.
20. Redesign UI around stable APIs.
21. Add VAPT.
22. Add Zabbix.
23. Add RAG.
24. Add Ansible/Salt execution backends.

---

# 44. Final Architecture

```text
                           +----------------+
                           |    WEB UI      |
                           +-------+--------+
                                   |
                                   v
                           +---------------+
                           |    Apache     |
                           +-------+-------+
                                   |
                                   v
                           +---------------+
                           |    FastAPI    |
                           +-------+-------+
                                   |
                                   v
                      +-------------------------+
                      |    AI ORCHESTRATOR      |
                      |     Ollama / LLM        |
                      +-----------+-------------+
                                  |
                                  v
                      +-------------------------+
                      |      TOOL REGISTRY      |
                      +-----------+-------------+
                                  |
             +--------------------+--------------------+
             |                    |                    |
             v                    v                    v
       +-----------+        +-----------+        +-----------+
       |   Linux   |        |  Oracle   |        |  OSCAP    |
       |   Tools   |        |   Tools   |        |   Tools   |
       +-----+-----+        +-----+-----+        +-----+-----+
             |                    |                    |
             v                    v                    v
           RHEL               Oracle 19c           OpenSCAP

                                  |
                                  v
                      +-------------------------+
                      | Finding / Event Model   |
                      +-----------+-------------+
                                  |
                                  v
                      +-------------------------+
                      | AI Analysis              |
                      +-----------+-------------+
                                  |
                                  v
                      +-------------------------+
                      | Risk / Policy Engine     |
                      +-----------+-------------+
                                  |
                         +--------+--------+
                         |                 |
                         v                 v
                     LOW ACTION       HUMAN APPROVAL
                         |                 |
                         +--------+--------+
                                  |
                                  v
                      +-------------------------+
                      | Controlled Executor      |
                      | Ansible / Salt / Native  |
                      +-----------+-------------+
                                  |
                                  v
                           Verification
                                  |
                                  v
                           Reporting
                                  |
                                  v
                             Audit DB
                                  |
                                  v
                              SQLite
```

---

# 45. Decision Log

## Decision 001 — FastAPI

FastAPI is the long-term API framework.

## Decision 002 — Keep Flask During Migration

Flask is not deleted immediately. Existing functionality is migrated endpoint-by-endpoint.

## Decision 003 — Tool Registry

All AI-callable operations must pass through an explicit registry.

## Decision 004 — Read-Only First

Linux and Oracle begin as read-only domains.

## Decision 005 — No Arbitrary SQL

No `execute_any_sql()`.

## Decision 006 — No Arbitrary Shell

No LLM-generated arbitrary shell execution.

## Decision 007 — Human-in-the-Loop

Medium/high-risk changes require approval.

## Decision 008 — Zabbix Later

Zabbix is a later monitoring/history/event integration.

## Decision 009 — RAG Later

RAG is added after live tools and finding models are stable.

## Decision 010 — Ansible/Salt Later

They become controlled execution backends after risk/approval architecture is stable.

---

# 46. Current Status

| Domain | Status |
|---|---|
| Git/GitHub | Established |
| Stage 0 baseline | Stable/tagged |
| FastAPI | Working |
| Metrics service | Working |
| Tool registry | Working |
| Linux monitoring | 18 read-only tools working |
| Linux health | Working |
| Linux UI | Functional; redesign pending |
| Oracle connection | NEXT |
| Oracle tools | Not started |
| Unified health | Planned |
| Ollama orchestration | Planned |
| Risk/approval/audit | Planned |
| OpenSCAP standardization | Planned |
| VAPT | Future |
| Zabbix | Future |
| RAG | Future |
| Ansible/Salt | Future execution backend |

---

# 47. Change Log

## 2026-09-05

### Objective
Create one permanent master Markdown tracker for the entire project.

### Completed
- Consolidated project history.
- Added Stage 0 baseline.
- Added Stage 1 architecture.
- Added Linux monitoring inventory.
- Added current environment.
- Added commands.
- Added problems/fixes.
- Added security observations.
- Added Git/GitHub workflow.
- Added Oracle roadmap.
- Added future AI/remediation/VAPT/OpenSCAP/Zabbix/RAG/Ansible architecture.
- Added decision log.
- Added per-change update template.

### Current Next Action

```text
Verify/install python-oracledb
        |
        v
Direct Oracle connection test
        |
        v
Oracle connection service
        |
        v
Oracle read-only tools
```

---

# 48. Per-Change Update Template

Copy this for every meaningful future change:

```markdown
## YYYY-MM-DD — <Change Title>

### Objective
What are we trying to achieve?

### Files Changed
- `path/file.py`
- `path/other.py`

### Architecture Change
What changed in the architecture?

### Implementation
What was implemented?

### Commands
```bash
# commands
```

### API Changes
- `GET /...`
- `POST /...`

### Testing
```bash
# tests
```

### Result
PASS / FAIL

### Problems
What went wrong?

### Fix
How was it fixed?

### Security Impact
Any security consideration?

### Git
```bash
git status
git diff --stat
git add .
git commit -m "..."
git push origin stage-1-foundation
```

### Checkpoint
Commit/tag if applicable.

### Next Step
What happens next?
```

---

# 49. Maintenance Rule

After every meaningful project change, update this document with:

1. Date
2. Objective
3. Files changed
4. Architecture change
5. Code/commands
6. API changes
7. Test result
8. Problem
9. Fix
10. Security impact
11. Git commit/tag
12. Next step

**This file is the living source of truth for project history and future reference.**

---

# 50. Current UI / Runtime Checkpoint — 2026-09-06

## Current State

The Stage 1 FastAPI UI is currently reachable from the Windows browser through the development endpoint:

```text
http://192.168.2.213:8801/
```

The current UI is functional enough for backend validation, but visual refinement is intentionally postponed until the backend architecture and Oracle integration are stable.

## UI Areas Currently Visible

The current browser screenshots show these application areas:

```text
DBA AI Agent
├── Dashboard
├── Processes
├── Network
├── Services
├── Security
├── Events
└── AI Assistant
```

### Dashboard

Currently displays Linux host/resource information including:

- Host information
- CPU usage
- Memory usage
- Swap usage
- Disk information
- Health summary
- Security posture
- Resource trend chart
- Top processes section
- Failed services section
- AI analysis section
- Report history section

The dashboard currently reflects the Linux monitoring foundation. Oracle health information is not yet integrated.

### Processes

The Processes page is connected to the Linux monitoring area and provides process summary information. The current screenshot shows process counts and a Top Processes area, but the detailed process table is not yet consistently populated in the UI.

### Network

The Network page currently exposes:

- Network interfaces
- Network statistics
- Listening ports

This is backed by the read-only Linux network tools.

### Services

The Services page currently shows failed systemd services. The current host reported no failed services during the captured UI state.

### Security

The Security page currently exposes:

- SELinux status
- Firewall status
- Failed login information
- Logged-in users
- OpenSCAP scan entry point

The current screenshot shows SELinux as `Permissive` and firewall as `Inactive`.

The OpenSCAP section currently has a UI/configuration display issue showing `undefined`; this is recorded as a frontend/backend integration item to fix after the core backend work is stable.

### Events

The Events page provides sections for:

- Journal errors
- Failed login attempts

The current UI screenshot displays no recent events. This does not replace the previously verified backend/tool results and should be treated as a UI data-refresh/mapping item until reconciled.

### AI Assistant

The AI Assistant page currently shows:

```text
Local AI
Ollama - llama3.2
```

and a chat input area.

The chat area is currently a UI shell; the full Stage 1 Ollama + Tool Registry orchestration is not yet implemented.

## Current UI Architecture

```text
Browser / Windows
        |
        | HTTP :8801 (development only)
        v
+---------------------+
| FastAPI Application |
+----------+----------+
           |
     +-----+-----+------------------+
     |           |                  |
     v           v                  v
 Metrics      Linux Health      Tool Registry
 Service       Service              |
                                  Linux tools
                                     |
                                     v
                                  RHEL host
```

## Current Backend Status

```text
Stage 1
  |
  +-- FastAPI foundation          [WORKING]
  +-- Metrics service             [WORKING]
  +-- Tool registry               [WORKING]
  +-- 18 Linux read-only tools    [WORKING]
  +-- Linux health service        [WORKING]
  +-- Linux UI                    [FUNCTIONAL / REFINEMENT PENDING]
  +-- Oracle connection           [NEXT]
  +-- Oracle read-only tools      [NOT STARTED]
  +-- Unified health              [PLANNED]
  +-- Ollama orchestration        [PLANNED]
  +-- Risk / approval / audit     [PLANNED]
```

## UI Evidence

The 2026-09-06 browser screenshots supplied during development document the current state of:

1. Dashboard
2. Processes
3. Network
4. Services
5. Security
6. Events
7. AI Assistant

These screenshots are development evidence only. They are not treated as the final UI design.

## Important Boundary

UI redesign is **not** the next implementation priority.

The project will continue in this order:

```text
Current Linux UI checkpoint
          |
          v
Verify python-oracledb
          |
          v
Direct Oracle connectivity test
          |
          v
Oracle connection service
          |
          v
Oracle read-only tools
          |
          v
Oracle health service
          |
          v
Unified Linux + Oracle health
          |
          v
Ollama orchestration
```

## Current Decision

Keep the existing UI as a functional development interface while the backend is being expanded. Do not spend significant implementation effort on CSS/layout redesign until the Linux + Oracle backend contract is stable.

---

# 51. Change Log — 2026-09-06 UI Checkpoint

### Change
Recorded the current browser/UI state supplied during Stage 1 development.

### Evidence
- FastAPI development UI reachable on port `8801`.
- Dashboard, Processes, Network, Services, Security, Events, and AI Assistant views are present.
- Security page currently displays SELinux `Permissive` and firewall `Inactive`.
- OpenSCAP UI currently displays an `undefined` value in its scan/profile area.
- AI Assistant UI is present but full tool-calling orchestration is still pending.

### Code Change
No backend code change was made by this checkpoint. This is a project-state/documentation update only.

### Next Implementation
Oracle connection layer remains the next technical milestone.


---

# 52. Oracle Integration Coding Checkpoint — 2026-09-06

## 52.1 Current UI checkpoint

The current FastAPI development UI has been verified in the browser at the temporary development address on port `8801`.

Current visible sections:

```text
Dashboard | Processes | Network | Services | Security | Events | AI Assistant
```

The UI is considered functional for backend development. UI redesign remains deferred until the Linux + Oracle backend contracts are stable.

Observed current pages include:

- Dashboard: Linux resource cards, health summary, security posture, resource trends, processes/services and AI analysis areas.
- Processes: process summary and top-process area.
- Network: interfaces, network statistics and listening-port area.
- Services: failed-services view.
- Security: SELinux/firewall/security posture and OpenSCAP area.
- Events: journal errors and failed-login area.
- AI Assistant: local Ollama/Llama 3.2 interface.

## 52.2 Next implementation: Oracle 19c read-only foundation

The next backend milestone is now explicitly:

```text
Oracle 19c Connection Layer
        |
        v
Oracle Read-Only Tools
        |
        v
Oracle Health Service
        |
        v
Unified Linux + Oracle Health
```

The first implementation is intentionally read-only. The AI layer must not receive arbitrary SQL execution capability.

## 52.3 Oracle service being implemented

New planned/working files for this milestone:

```text
services/oracle_service.py
services/oracle_health_service.py
tools/oracle.py
```

The Oracle service uses `python-oracledb` and environment-based credentials:

```text
ORACLE_USER
ORACLE_PASSWORD
ORACLE_DSN
```

No Oracle password is stored in source code.

## 52.4 Initial Oracle tool contract

```text
oracle.connection
oracle.database_info
oracle.instance_info
oracle.pdbs
oracle.tablespaces
oracle.sessions
oracle.blocking_sessions
```

All initial tools are explicitly read-only and use fixed SQL statements owned by the Python application.

## 52.5 Oracle security boundary

```text
                 Ollama / Llama 3.2:3b
                           |
                           v
                    Tool Registry
                           |
                  +--------+--------+
                  |                 |
             Linux tools       Oracle tools
                  |                 |
                  v                 v
              RHEL APIs       Fixed SQL only
                                    |
                                    v
                                Oracle 19c
```

Forbidden design:

```text
LLM -> arbitrary SQL -> Oracle
```

Required design:

```text
LLM -> named registered tool -> deterministic Python function -> fixed SQL -> Oracle
```

## 52.6 Oracle health rules

Initial deterministic rules:

- Connection failure -> `critical`
- Instance not `OPEN` -> `critical`
- Database not `READ WRITE` -> `warning` (except this is informational for environments intentionally using another mode)
- Non-seed PDB not `READ WRITE` -> `warning`
- Tablespace usage >= 95% -> `critical`
- Tablespace usage >= 85% -> `warning`
- Blocking session relationship detected -> `warning`
- Otherwise -> `healthy`

The health calculation is deterministic Python logic; the LLM will later explain findings rather than determine whether a database is healthy.

## 52.7 Implementation status

```text
Oracle service code                 PREPARED
Oracle tool definitions             PREPARED
Oracle health aggregation           PREPARED
FastAPI Oracle endpoints            NEXT
Tool registry Oracle registration   NEXT
Direct Oracle connectivity test     REQUIRED
Oracle runtime verification         NOT YET VERIFIED
```

This distinction is intentional: code prepared in the development workspace is not considered production/VM-verified until the user runs it against the actual Oracle 19c instance.

## 52.8 Required environment on the Oracle host

Run as the application user, not by putting the password into source code:

```bash
cd /home/test/opt/os-agent
source venv/bin/activate
pip install oracledb
```

Then configure:

```bash
export ORACLE_USER="system"
export ORACLE_PASSWORD="<actual-password>"
export ORACLE_DSN="127.0.0.1:1521/ORCLPDB1"
```

A later deployment step should move these values into a protected environment/configuration mechanism rather than a shell history or source file.

## 52.9 Acceptance test

The first Oracle acceptance test is:

```python
import oracledb

connection = oracledb.connect(
    user="system",
    password="YOUR_PASSWORD",
    dsn="127.0.0.1:1521/ORCLPDB1",
)

print("Oracle connection successful")

cursor = connection.cursor()
cursor.execute("""
    SELECT
        sys_context('USERENV', 'DB_NAME'),
        sys_context('USERENV', 'SERVICE_NAME')
    FROM dual
""")

print(cursor.fetchone())

cursor.close()
connection.close()
```

Expected identity for the current lab database:

```text
Oracle connection successful
('ORCLCDB', 'ORCLPDB1')
```

## 52.10 Current architecture after this milestone

```text
Browser
   |
   v
Apache
   |
   v
FastAPI
   |
   +------------------+
   |                  |
   v                  v
Linux Health      Oracle Health
   |                  |
   v                  v
Linux Tools        Oracle Tools
   |                  |
   v                  v
RHEL            Oracle 19c
```

The next coding operation is to register the Oracle tools in the central registry and expose deterministic Oracle endpoints through FastAPI after direct connectivity is verified.


---

# Stage 1 Completion Gate

Stage 1 is **not complete** until the following are implemented and regression-tested:

| Area | Status |
|---|---|
| Architecture/documentation | DONE |
| FastAPI foundation | DONE |
| Linux metrics + 18 tools | DONE |
| Linux health | DONE |
| Tool Registry | DONE |
| Oracle connection | DONE |
| Oracle 7 read-only tools | DONE |
| Oracle health service | DONE |
| `/api/oracle/health` | NEXT |
| Unified Linux + Oracle health | PENDING |
| Full FastAPI endpoint migration | IN PROGRESS |
| UI/backend functional validation | IN PROGRESS |
| Secure systemd Oracle configuration | PENDING |
| Ollama tool orchestration | PENDING |
| Structured AI output | PENDING |
| Risk/policy foundation | PENDING |
| Human approval foundation | PENDING |
| Audit trail | PENDING |
| Automated regression tests | PENDING |
| Security hardening | PENDING |
| OSCAP Tool Registry integration | PENDING |
| Final regression + Stage 1 release tag | PENDING |

## Stage 1 Exit Principle

No Stage 2 work should begin until the Stage 1 completion gate is satisfied or an item is explicitly documented as deferred to a later stage.

---

# 54. 2026-09-07 — Oracle Health FastAPI Endpoint

## Objective
Expose the already-verified deterministic Oracle health service through the FastAPI application as:

```text
GET /api/oracle/health
```

This closes the next Stage 1 completion-gate item without connecting Ollama or introducing autonomous execution.

## Files Changed

- `core/fastapi_app.py`

## Architecture Change

Before:

```text
FastAPI
  |
  +--> Linux Health
  |
  +--> Tool Registry
          |
          +--> Oracle Tools
                |
                +--> Oracle 19c
```

After:

```text
FastAPI
  |
  +--> /api/linux/health
  |
  +--> /api/oracle/health
          |
          v
    Oracle Health Service
          |
          v
     Tool Registry
          |
          +--> oracle.connection
          +--> oracle.database_info
          +--> oracle.instance_info
          +--> oracle.pdbs
          +--> oracle.tablespaces
          +--> oracle.sessions
          +--> oracle.blocking_sessions
          |
          v
       Oracle 19c
```

## Implementation

Add the Oracle health service import:

```python
from services.oracle_health_service import get_oracle_health
```

Add the deterministic read-only endpoint:

```python
@app.get("/api/oracle/health")
def oracle_health():
    return get_oracle_health()
```

No arbitrary SQL endpoint is introduced and no write operation is exposed.

## API Change

New endpoint:

```text
GET /api/oracle/health
```

Expected response shape:

```json
{
  "status": "critical",
  "critical_count": 1,
  "warning_count": 1,
  "findings": [
    {
      "severity": "critical",
      "source": "tablespace",
      "message": "Tablespace SYSTEM is 97.19% full",
      "tablespace": "SYSTEM",
      "usage_percent": 97.19
    },
    {
      "severity": "warning",
      "source": "tablespace",
      "message": "Tablespace SYSAUX is 93.73% full",
      "tablespace": "SYSAUX",
      "usage_percent": 93.73
    }
  ],
  "errors": [],
  "connection": {
    "connected": true,
    "db_name": "ORCLPDB1",
    "service_name": "orclpdb1",
    "instance_name": "ORCLCDB"
  }
}
```

The values above are the latest deterministic Oracle service verification baseline; the live endpoint must be tested on the RHEL host.

## Test Commands

Run on the Oracle/RHEL host from the project directory:

```bash
cd /home/test/opt/os-agent
source venv/bin/activate

python -m py_compile core/fastapi_app.py

# Start FastAPI for the development test if it is not already running:
uvicorn core.fastapi_app:app --host 127.0.0.1 --port 8801
```

In another shell:

```bash
curl -s http://127.0.0.1:8801/api/oracle/health | python -m json.tool
```

Also verify the existing endpoints remain healthy:

```bash
curl -s http://127.0.0.1:8801/api/health | python -m json.tool
curl -s http://127.0.0.1:8801/api/linux/health | python -m json.tool
curl -s http://127.0.0.1:8801/api/tools | python -m json.tool
```

## Result

Implementation prepared against the current FastAPI foundation. Live endpoint validation must be performed on the user's RHEL host because this working environment does not contain the current deployed project tree or Oracle listener.

## Security Impact

- Endpoint is read-only.
- It delegates to the deterministic Oracle health service.
- It does not accept SQL from the client.
- It does not expose Oracle credentials.
- It does not grant the LLM direct database access.

## Stage 1 Gate Update

```text
Oracle health service              DONE
/api/oracle/health                 IMPLEMENTED — LIVE TEST PENDING
Unified Linux + Oracle health      NEXT
```

## Next Step

Build the unified deterministic Linux + Oracle health endpoint after `/api/oracle/health` is live-tested.

---

# 2026-09-07 — AI Orchestrator Performance Investigation Checkpoint

## Objective

Begin the AI phase of Stage 1 while keeping `llama3.2:3b` as the AI reasoning/tool-selection brain. Measure where the AI request latency is occurring before making further architecture or code changes.

## Current Stage 1 Position

```text
Stage 1 — Deterministic Foundation
    |
    +-- FastAPI foundation                         DONE
    +-- Linux tools / health                       DONE
    +-- Oracle tools / health                      DONE
    +-- OSCAP tool registry                        DONE
    +-- Unified tool registry                      DONE
    +-- Deterministic domain routing               DONE
    +-- FastAPI browser/UI path                    DONE
    +-- AI orchestrator foundation                 DONE
    |
    +-- AI performance/tool-calling validation     IN PROGRESS
    +-- AI structured output                       NEXT
    +-- Risk / approval / audit                    NEXT
    +-- Regression/security testing                NEXT
    +-- Stage 1 release checkpoint                 PENDING
```

The latest deterministic foundation checkpoint remains:

```text
Branch: stage-1-foundation
Tag:    v0.3.0-stage1-deterministic-foundation
```

No new AI release tag has been created yet.

## Architecture Change

The Stage 1 AI path is now defined as:

```text
USER
  |
  v
WEB UI / curl
  |
  v
Apache
  |
  v
FastAPI :8801
  |
  v
AI Orchestrator
  |
  +--> Deterministic Domain Router
  |       |
  |       +--> Linux
  |       +--> Oracle
  |       +--> OSCAP
  |       +--> General
  |
  +--> Ollama / Llama 3.2:3b
  |
  v
Tool Registry
  |
  +--> Linux read-only tools
  +--> Oracle read-only tools
  +--> OSCAP read-only tools
```

The deterministic router is a safety/performance pre-filter. It does **not** replace the LLM as the AI brain.

The AI boundary remains:

```text
LLM ---> explicit registered tools only
LLM -X-> arbitrary shell
LLM -X-> arbitrary SQL
LLM -X-> unrestricted remediation
```

## Files / Components Changed During AI Phase

The active AI implementation is centered on:

```text
core/ai_orchestrator.py
core/domain_router.py
core/tool_registry.py
core/fastapi_app.py
```

`core/ai_orchestrator.py` was instrumented to capture:

- domain routing time
- tool-schema build time
- every Ollama call duration
- tool-schema count
- tool execution duration
- total request duration
- Ollama timeout value

## API Changes

Existing AI endpoints:

```text
GET  /api/ai/status
POST /api/chat
```

The AI status endpoint reports the configured provider/model, domain routing state, tool counts, excluded tools, read-only mode, maximum tool iterations, and Ollama timeout.

The `/api/chat` response now includes a timing object when the orchestrator completes or times out:

```json
{
  "timing": {
    "routing_ms": 0.45,
    "schema_build_ms": 0.10,
    "ollama_calls": [],
    "tool_execution": [],
    "total_ms": 0,
    "total_seconds": 0
  }
}
```

The exact values are runtime measurements and will vary by request.

## Performance Test Results — 2026-09-07

### Test 1 — Direct Ollama `/api/generate`

Command used:

```bash
time curl -s --max-time 60 http://127.0.0.1:11434/api/generate \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "llama3.2:3b",
    "prompt": "Reply with exactly: AI TEST OK",
    "stream": false
  }' | python -m json.tool
```

Result:

```text
HTTP/API result: SUCCESS
Wall time:        20.683 seconds
Ollama duration:  20.524782670 seconds
Model load:        0.003885494 seconds
Prompt tokens:     32
Prompt evaluation: 15.522558 seconds
Generated tokens:  4
Generation:         4.167151 seconds
```

### Test 2 — Direct Ollama `/api/chat` without tools

Command used:

```bash
time curl -s --max-time 60 http://127.0.0.1:11434/api/chat \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "llama3.2:3b",
    "messages": [
      {
        "role": "user",
        "content": "Reply with exactly: AI TEST OK"
      }
    ],
    "stream": false
  }' | python -m json.tool
```

Result:

```text
HTTP/API result: SUCCESS
Wall time:        11.239 seconds
Ollama duration:  11.127102162 seconds
Model load:        0.013420999 seconds
Prompt tokens:     32
Prompt evaluation: 6.077345 seconds
Generated tokens:  4
Generation:        5.028378 seconds
```

### Test 3 — FastAPI `/api/chat` with Linux tool schemas

User request:

```text
What is the current CPU usage?
```

Result:

```text
FastAPI total:       300.114 seconds
Routing:               0.45 ms
Schema build:          0.107 ms
Ollama call:         300.113 seconds
Linux schemas:          18
Tool executions:          0
Result:              HTTP timeout
```

The request ended with:

```text
HTTPConnectionPool(host='localhost', port=11434):
Read timed out. (read timeout=300)
```

## Findings

The current evidence shows:

1. Ollama is running and reachable on `127.0.0.1:11434`.
2. `llama3.2:3b` can successfully generate a response.
3. Direct `/api/chat` without tools is significantly faster than the `/api/generate` baseline in this test.
4. FastAPI routing and tool-schema construction are not the source of the 300-second delay.
5. The timed-out FastAPI request received no LLM tool call, so no registered tool was executed.
6. The 300-second delay is introduced when the AI orchestrator sends its tool-enabled `/api/chat` request, or by the subsequent tool-calling protocol/payload behavior.
7. Model loading is not the dominant problem in the direct Ollama tests.

At this checkpoint, it is **not yet proven** whether the primary cause is:

```text
18 Linux tool schemas
        OR
full system/tool prompt
        OR
Ollama tool-calling behavior
        OR
conversation/tool-call message format
```

Therefore no speculative architectural change has been committed.

## Security Impact

No new privileged execution path was introduced during this performance investigation.

AI-callable operations remain read-only and are constrained by the explicit tool registry. `oscap.scan` remains excluded from AI v1. Arbitrary shell execution, arbitrary SQL, and unrestricted remediation remain prohibited.

## Problem

`POST /api/chat` through the FastAPI AI orchestrator can block until the configured 300-second Ollama timeout when processing a Linux request with tool schemas.

## Current Fix / Decision

Do **not** increase the timeout further and do **not** remove Llama from the architecture.

The next investigation will isolate the tool-enabled Ollama request directly, outside FastAPI, to determine whether the 18 Linux schemas or the tool-calling protocol is responsible.

## Next Work Session

Run the isolated 18-tool Ollama test before modifying the orchestrator:

```bash
python - <<'PY'
import time
import requests
import config
from core.ai_orchestrator import build_tool_schemas

tools = build_tool_schemas("linux")
print("Tool count:", len(tools))

payload = {
    "model": config.OLLAMA_MODEL,
    "messages": [
        {
            "role": "user",
            "content": "What is the current CPU usage?"
        }
    ],
    "tools": tools,
    "stream": False
}

print("Sending request to Ollama...")
start = time.perf_counter()

try:
    response = requests.post(
        "http://127.0.0.1:11434/api/chat",
        json=payload,
        timeout=120
    )
    elapsed = time.perf_counter() - start
    print("HTTP status:", response.status_code)
    print("Elapsed:", round(elapsed, 3), "seconds")
    print(response.text)
except Exception as exc:
    elapsed = time.perf_counter() - start
    print("ERROR:", exc)
    print("Elapsed:", round(elapsed, 3), "seconds")
PY
```

Also measure the serialized schema size if required:

```bash
python - <<'PY'
import json
from core.ai_orchestrator import build_tool_schemas

tools = build_tool_schemas("linux")
print("Tool count:", len(tools))
print("JSON size:", len(json.dumps(tools)), "bytes")
print("JSON size:", round(len(json.dumps(tools)) / 1024, 2), "KB")
PY
```

Do not change the AI architecture until this isolation test is complete.

## Stage 1 AI Gate

```text
AI endpoint integration                 DONE
Deterministic domain routing             DONE
AI timing instrumentation                DONE
Direct Ollama baseline                   DONE
Tool-enabled Ollama isolation             NEXT
AI tool-calling end-to-end                PENDING
Structured AI output                     PENDING
Risk / approval / audit                  PENDING
Regression + security testing            PENDING
AI release tag                           PENDING
```

## End-of-Day Status

```text
2026-09-07

Stage 1 deterministic foundation:       CHECKPOINTED
AI integration:                         IN PROGRESS
Llama model:                            llama3.2:3b
Ollama connectivity:                    VERIFIED
Direct /api/chat:                       VERIFIED (~11 sec)
FastAPI tool-enabled AI:                TIMEOUT at 300 sec
Root cause:                             UNDER INVESTIGATION
Next action:                            Isolate 18-tool Ollama request
```
