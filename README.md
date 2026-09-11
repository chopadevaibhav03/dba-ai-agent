# DBA AI Agent

> **AI-powered Linux, Oracle DBA, OpenSCAP, VAPT and security-automation platform**
>
> The project is designed to combine deterministic system/database tooling with a local LLM while keeping execution controlled, auditable and human-approved.

---

## 1. Project Vision

The goal of **DBA AI Agent** is to build a local operations assistant for DBAs, Linux administrators and security teams.

The platform will allow a user to ask questions such as:

- What is the current CPU or memory usage?
- Is the Linux server healthy?
- Which services failed?
- Are there listening ports?
- Is Oracle healthy?
- What PDBs are available?
- Are any Oracle sessions blocking others?
- Which tablespaces are close to full?
- What are the current OpenSCAP findings?
- Why is a finding important?
- What should be done to remediate it?
- Can a proposed remediation be executed after human approval?

The important design principle is:

> **The LLM explains, reasons and orchestrates. Deterministic tools collect data and perform controlled actions.**

The LLM must **not** become an unrestricted shell or SQL executor.

---

# 2. Target Architecture

```text
                         ┌─────────────────────┐
                         │       DBA / User    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       Web UI        │
                         │      DataPatro       │
                         └──────────┬──────────┘
                                    │ HTTP
                                    ▼
                         ┌─────────────────────┐
                         │       Apache       │
                         │     Port 80/443     │
                         └──────────┬──────────┘
                                    │ reverse proxy
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │     Application     │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼────────────────┐
                    │               │                │
                    ▼               ▼                ▼
             ┌────────────┐ ┌─────────────┐ ┌──────────────┐
             │ AI         │ │ Deterministic│ │ Security /   │
             │ Orchestrator│ │ Services     │ │ OSCAP        │
             └─────┬──────┘ └──────┬──────┘ └──────┬───────┘
                   │               │                │
                   ▼               ▼                ▼
             ┌────────────┐  ┌─────────────┐  ┌─────────────┐
             │   Ollama   │  │ Tool Registry│  │ OpenSCAP    │
             │ llama3.2:3b│  └──────┬──────┘  │ RHEL 8 SSG  │
             └────────────┘         │         └─────────────┘
                                    │
                       ┌────────────┼────────────┐
                       │            │            │
                       ▼            ▼            ▼
                  ┌─────────┐ ┌─────────┐ ┌──────────┐
                  │  Linux  │ │ Oracle  │ │  OSCAP   │
                  │  Tools  │ │  Tools  │ │  Tools   │
                  └────┬────┘ └────┬────┘ └─────┬────┘
                       │           │             │
                       ▼           ▼             ▼
                    RHEL       Oracle 19c     SCAP Data
```

---

# 3. Safety Architecture

The architecture deliberately separates **reasoning** from **execution**.

```text
User Request
     │
     ▼
FastAPI
     │
     ▼
Domain Router
     │
     ▼
AI Orchestrator
     │
     ▼
Ollama / Local LLM
     │
     ▼
Tool Registry
     │
     ▼
Deterministic Python Tool
     │
     ▼
Linux / Oracle / OpenSCAP
```

The architecture must **not** become:

```text
User
  ↓
LLM
  ↓
arbitrary shell command
```

or:

```text
User
  ↓
LLM
  ↓
arbitrary SQL
```

Initial tools are read-only.

---

# 4. Current Environment

## Server

```text
Host:       vaibhav.localdomain
OS:         RHEL 8.10
Kernel:     4.18.0-372.9.1.el8.x86_64
CPU:        4 logical CPUs
RAM:        ~15.8 GiB
```

## Application

```text
Project path:
/home/test/opt/os-agent

FastAPI:
127.0.0.1:8801

Apache:
Port 80

Browser:
http://192.168.2.213/
```

Apache reverse-proxies requests from port 80 to FastAPI on port 8801.

---

# 5. What Has Been Completed

## Stage 0 — Initial Foundation

- Existing project preserved.
- Initial application structure established.
- Existing monitoring functionality retained.
- Git repository created.
- Baseline tag created.

Checkpoint:

```text
v0.1.0-stage0
```

---

## Stage 1 — Linux / FastAPI Foundation

Completed:

- FastAPI foundation
- Existing metrics endpoints migrated
- Linux health aggregation
- Linux tool registry
- Oracle service foundation
- OpenSCAP foundation
- Unified system health
- Apache reverse proxy
- Enterprise web UI
- Tool schema definitions
- Deterministic domain router
- Initial AI orchestration
- Ollama integration
- `/api/chat`
- `/api/ai/status`

Checkpoints:

```text
v0.2.0-stage1-linux
v0.3.0-stage1-deterministic-foundation
```

---

# 6. Current FastAPI API

Current application routes include:

```text
GET  /
GET  /api
GET  /api/health
GET  /api/tools
GET  /api/tools/{tool_name:path}

GET  /api/metrics/latest
GET  /api/metrics/history

GET  /api/linux/health
GET  /api/oracle/health
GET  /api/system/health

POST /api/analyze

GET  /api/reports

GET  /api/services
GET  /api/services/{service_name}
POST /api/service/action

GET  /api/security/content
POST /api/security/scan
GET  /api/security/scan/{scan_id}
GET  /api/security/findings
GET  /api/security/report/{scan_id}
POST /api/security/fix

POST /api/actions/apply

GET  /api/ai/status
POST /api/chat
```

The API surface is still being hardened and reorganized as the project moves toward a production architecture.

---

# 7. Linux Tooling

The current Linux registry contains 18 read-only tools:

```text
linux.cpu
linux.disk
linux.failed_logins
linux.failed_services
linux.firewall
linux.inodes
linux.journal_errors
linux.listening_ports
linux.load
linux.logged_in_users
linux.memory
linux.network_interfaces
linux.network_stats
linux.process_summary
linux.selinux
linux.swap
linux.system_info
linux.top_processes
```

These tools provide deterministic Linux information to the application and, eventually, to the AI orchestrator.

---

# 8. Linux Health

The Linux health service aggregates information such as:

- CPU
- load average
- memory
- swap
- root filesystem
- failed services
- SELinux
- firewall
- system information

Example current observations:

```text
CPU:          ~32.5%
Load:         ~0.47 / 0.79 / 0.78
Memory:       ~31.1%
Swap:         0%
Root disk:    ~71.3%
Failed units: 0
```

These values are runtime observations and will naturally change.

---

# 9. Oracle 19c Integration

Oracle integration is now connected to the real Oracle environment.

Environment:

```text
Oracle:
19c Enterprise Edition

SID:
ORCLCDB

ORACLE_HOME:
/opt/oracle/product/19c/dbhome_1

CDB:
ORCLCDB

PDB:
ORCLPDB1

Listener:
192.168.2.213:1521
```

The project uses `python-oracledb`.

The current connection has been successfully tested against:

```text
ORCLPDB1
```

---

# 10. Oracle Tool Registry

Current Oracle tools:

```text
oracle.connection
oracle.database_info
oracle.instance_info
oracle.pdbs
oracle.tablespaces
oracle.sessions
oracle.blocking_sessions
```

These are intended to provide structured, read-only Oracle information.

The architecture deliberately avoids exposing a generic:

```text
execute_any_sql()
```

interface to the LLM.

---

# 11. Current Oracle Observations

The current environment has:

```text
CDB:
ORCLCDB

Database:
READ WRITE

Instance:
OPEN / ACTIVE

PDB:
ORCLPDB1 - READ WRITE
PDB$SEED - READ ONLY
```

Tablespace observations from testing included:

```text
SYSTEM      ~97.19%
SYSAUX      ~93.73%
UNDOTBS1    ~35.18%
USERS       ~20%
```

These high SYSTEM/SYSAUX values need DBA attention and are useful for validating future AI analysis.

---

# 12. OpenSCAP Integration

OpenSCAP is part of the security/compliance architecture.

Current environment:

```text
OpenSCAP:
1.3.14

Content:
/usr/share/xml/scap/ssg/content/ssg-rhel8-ds.xml

Operating System:
RHEL 8.10
```

The current system contains RHEL 8 Security Guide content.

The project does not assume RHEL 9 content is installed.

---

# 13. OSCAP Tools

Current registry tools:

```text
oscap.content
oscap.scan
oscap.scan_status
oscap.findings_history
oscap.report
oscap.fix_preview
```

The AI v1 tool set currently excludes:

```text
oscap.scan
```

The reason is safety and resource control.

Scanning should remain an explicit controlled operation rather than something the LLM can repeatedly trigger.

---

# 14. OSCAP API

Security endpoints currently include:

```text
GET  /api/security/content
POST /api/security/scan
GET  /api/security/scan/{scan_id}
GET  /api/security/findings
GET  /api/security/report/{scan_id}
POST /api/security/fix
```

The current fix path is preview/approval oriented.

It must not silently execute remediation.

---

# 15. AI Architecture

The current local AI stack is:

```text
FastAPI
   ↓
AI Orchestrator
   ↓
Ollama
   ↓
llama3.2:3b
```

Ollama runs locally:

```text
127.0.0.1:11434
```

The model supports tool calling.

The project is designed so that the model does not directly access privileged operating-system or database interfaces.

---

# 16. Domain Router

The deterministic domain router currently identifies:

```text
linux
oracle
oscap
general
```

Examples:

```text
"What is the current CPU usage?"
        → linux

"Why is Linux memory high?"
        → linux

"Is Oracle healthy?"
        → oracle

"Are there any blocking sessions?"
        → oracle

"Show my PDB status"
        → oracle

"What are my OSCAP findings?"
        → oscap

"Explain the CIS findings"
        → oscap

"What is the capital of India?"
        → general
```

Explicit domain terms receive priority.

This is intentionally deterministic instead of allowing the LLM to decide the entire execution path.

---

# 17. Tool Registry

The registry currently contains:

```text
Linux:   18
Oracle:   7
OSCAP:    6

Total:   31
```

All registered tools are currently defined as read-only.

The AI status endpoint exposes the AI-visible tool count separately because certain tools, such as `oscap.scan`, are intentionally excluded from AI v1.

---

# 18. AI Tool Calling

The intended flow is:

```text
User
 │
 ▼
Domain Router
 │
 ▼
AI Orchestrator
 │
 ▼
Ollama
 │
 ├── final answer
 │
 └── tool call
        │
        ▼
   Tool Registry
        │
        ▼
   Deterministic Tool
        │
        ▼
 Linux / Oracle / OSCAP
        │
        ▼
 Tool Result
        │
        ▼
 Ollama
        │
        ▼
 Final Answer
```

The current implementation has the foundation for this architecture, but tool-calling performance and end-to-end behavior still need optimization and validation.

---

# 19. Current AI Performance Problem

The largest current AI issue is performance when tool schemas are included.

Direct local model calls without tools have been substantially faster than the FastAPI tool-enabled path.

Observed testing showed approximately:

```text
Direct /api/generate:
~20.7 seconds

Direct /api/chat without tools:
~11.2 seconds

FastAPI tool-enabled Linux request:
~300 seconds
```

The ~300-second request reached the configured timeout.

The likely area to investigate is the tool-enabled Ollama request path, including:

- tool schema size
- message format
- model tool-call behavior
- prompt size
- number of schemas
- context size
- CPU inference cost
- timeout behavior
- unnecessary tool schemas sent to the model

This is a priority before expanding the AI architecture.

---

# 20. Current AI Strategy

The immediate AI milestone is intentionally small:

```text
Browser UI
    ↓
POST /api/chat
    ↓
FastAPI
    ↓
Ollama /api/chat
    ↓
llama3.2:3b
    ↓
Response
    ↓
Browser UI
```

First make simple AI chat reliable and responsive.

Then:

```text
Simple AI
    ↓
Domain Routing
    ↓
One Tool
    ↓
Multiple Tools
    ↓
Tool Result Reasoning
    ↓
Structured Output
    ↓
Approval
    ↓
Controlled Remediation
```

Do not introduce every AI feature at once.

---

# 21. Security Model

The security model is based on:

- least privilege
- deterministic tools
- explicit tool registry
- read-only by default
- server-side validation
- approval gates
- audit records
- controlled execution
- verification
- rollback where possible

The LLM should never be treated as a trusted privileged executor.

---

# 22. Future Remediation Architecture

Future remediation should follow:

```text
Finding
   ↓
AI Analysis
   ↓
Risk Classification
   ↓
┌───────────────────────────┐
│ Low                       │
│ Limited Auto-Approval     │
└───────────────────────────┘
              │
              │
              ▼
┌───────────────────────────┐
│ Medium / High Risk        │
│ Human Approval Required   │
└───────────────────────────┘
              │
              ▼
      Controlled Executor
              │
              ▼
          Verification
              │
              ▼
            Report
              │
              ▼
            Audit
```

The remediation executor must use fixed, constrained actions rather than arbitrary commands.

---

# 23. Human Approval Architecture

The planned approval flow:

```text
Finding
   ↓
Proposed Action
   ↓
Risk Classification
   ↓
Pending Approval Record
   ↓
Human Approves / Rejects
   ↓
Server Validates Approval
   ↓
Controlled Executor
   ↓
Verification
   ↓
Audit
```

Approval must be enforced server-side.

The UI must not be the only security boundary.

---

# 24. VAPT Roadmap

VAPT is a planned security capability.

The intended progression is:

```text
Asset Discovery
      ↓
Configuration Analysis
      ↓
Vulnerability Detection
      ↓
Finding Normalization
      ↓
Risk Classification
      ↓
Recommended Remediation
      ↓
Human Approval
      ↓
Controlled Remediation
      ↓
Verification
      ↓
Audit / Report
```

The project should initially focus on safe defensive analysis.

Autonomous exploitation is not part of the initial architecture.

---

# 25. Zabbix Roadmap

Zabbix is planned as a future monitoring/data source.

Conceptually:

```text
Linux
Oracle
Network
Applications
     ↓
   Zabbix
     ↓
Historical Metrics / Events
     ↓
DBA AI Agent
     ↓
Analysis / Correlation
```

Zabbix should be treated as a monitoring and history source.

It should not become the AI brain.

---

# 26. RAG Roadmap

RAG will be added later for trusted knowledge such as:

- Oracle documentation
- Linux documentation
- OpenSCAP guidance
- internal SOPs
- runbooks
- security standards
- remediation procedures
- architecture documentation

Future flow:

```text
User Question
     ↓
Domain Router
     ↓
Retriever
     ↓
Trusted Knowledge
     ↓
AI Orchestrator
     ↓
Tool Registry
     ↓
Final Answer
```

RAG should support the deterministic tool architecture, not replace it.

---

# 27. Ansible / Salt Roadmap

Ansible and/or Salt are future controlled execution mechanisms.

They should not be introduced as unrestricted AI command executors.

Future architecture:

```text
AI Recommendation
       ↓
Approval
       ↓
Validated Action
       ↓
Ansible / Salt
       ↓
Target Host
       ↓
Verification
       ↓
Audit
```

Execution should only happen through approved, predefined operations.

---

# 28. Planned Data Architecture

The application currently uses SQLite-oriented persistence for project data and history.

Future normalized entities should include:

```text
Host
OracleInstance
Metric
Finding
Event
Action
Approval
Verification
Audit
Report
```

A future database architecture may evolve as scale requirements increase.

---

# 29. Observability

The project needs observability for:

- API latency
- AI latency
- Ollama inference time
- tool execution time
- tool failures
- request failures
- OpenSCAP scan duration
- Oracle query duration
- CPU
- memory
- disk
- application health

The AI performance tracker already records timing information such as:

```text
routing_ms
schema_build_ms
ollama_calls
tool_execution
total_ms
```

---

# 30. Current Problems and Status

| Problem | Status | Notes |
|---|---|---|
| FastAPI foundation | SOLVED | Working |
| Linux metrics migration | SOLVED | Working |
| Linux health aggregation | SOLVED | Working |
| Linux tool registry | SOLVED | 18 tools |
| Oracle connectivity | SOLVED | Real Oracle 19c connection tested |
| Oracle read-only tools | SOLVED | 7 tools |
| OSCAP content discovery | SOLVED | RHEL 8 content available |
| OSCAP API foundation | SOLVED | Scan/report/finding endpoints exist |
| Domain routing | SOLVED | Linux/Oracle/OSCAP/general |
| Apache reverse proxy | SOLVED | Port 80 → FastAPI 8801 |
| Enterprise UI | SOLVED | Working through Apache |
| AI status endpoint | SOLVED | Working |
| Basic Ollama integration | PARTIAL | Needs end-to-end hardening |
| AI tool calling performance | OPEN | Major priority |
| Simple AI UI response | IN PROGRESS | Must be reliable before expansion |
| Tool-call latency | OPEN | Investigate schemas/context/model behavior |
| Oracle env persistence | OPEN | Needs permanent secure service configuration |
| Authentication/RBAC | OPEN | Required before production management |
| Approval persistence | OPEN | Required for remediation |
| Risk classifier | OPEN | Future |
| Remediation executor | OPEN | Future |
| Verification engine | OPEN | Future |
| Audit framework | OPEN | Future |
| OSCAP finding normalization | OPEN | Future |
| VAPT engine | PLANNED | Future |
| Zabbix integration | PLANNED | Future |
| RAG | PLANNED | Future |
| Ansible/Salt | PLANNED | Future |
| Legacy Flask cleanup | OPEN | Remove after safe migration |
| systemd privilege reduction | OPEN | Current services need hardening |
| `shell=True` cleanup | OPEN | Replace with fixed command execution |
| API authentication | OPEN | Required for production |
| UI/API production hardening | OPEN | Ongoing |

---

# 31. Known Technical Debt

## 31.1 Privileged Services

Some current services run with elevated privileges.

Final architecture should use:

- dedicated service account
- least privilege
- Linux capabilities where appropriate
- restricted filesystem permissions
- SELinux policy where practical

---

## 31.2 Arbitrary Action Endpoint

The current project contains action-management paths that need stronger server-side approval enforcement.

Future design:

```text
Request
 ↓
Validate
 ↓
Authorize
 ↓
Approval
 ↓
Action Policy
 ↓
Executor
 ↓
Verify
```

---

## 31.3 Shell Execution

Existing automation code contains shell execution patterns such as `shell=True`.

These should be replaced with:

- fixed executable paths
- fixed argument lists
- allowlisted commands
- dedicated Python functions
- input validation

---

## 31.4 Oracle Credentials

Oracle credentials must never be committed to Git.

Use:

```text
root-owned configuration
permissions: 600
systemd EnvironmentFile
```

Credentials should be rotated if they have ever been exposed.

---

## 31.5 RHEL / OSCAP Content

The current environment is RHEL 8.10 and uses RHEL 8 SSG content.

The application and UI must not incorrectly advertise RHEL 9 compliance content when RHEL 9 content is not installed.

---

# 32. Project Directory

Current major components include:

```text
os-agent/
│
├── core/
│   ├── fastapi_app.py
│   ├── ai_orchestrator.py
│   ├── domain_router.py
│   └── tool_registry.py
│
├── services/
│   ├── metrics_service.py
│   ├── linux_health_service.py
│   ├── oracle_service.py
│   ├── oracle_health_service.py
│   └── system_health_service.py
│
├── tools/
│   ├── linux.py
│   ├── oracle.py
│   └── oscap.py
│
├── static/
│   └── web UI
│
├── requirements.txt
├── README.md
└── ...
```

The exact structure may evolve as the architecture is cleaned up.

---

# 33. Development Rules

## Rule 1 — Do not bypass deterministic tools

Bad:

```text
LLM → arbitrary shell
```

Good:

```text
LLM → registered tool → deterministic Python function
```

---

## Rule 2 — Read-only first

Initial AI capabilities should primarily inspect and explain.

Write/remediation functionality comes later.

---

## Rule 3 — No generic SQL executor

Do not expose:

```text
execute_any_sql(sql)
```

Instead expose purpose-built tools:

```text
oracle.sessions
oracle.tablespaces
oracle.blocking_sessions
```

---

## Rule 4 — No generic shell executor

Do not expose:

```text
execute_any_shell(command)
```

Instead expose controlled operations.

---

## Rule 5 — Human approval for risky operations

High-impact operations require explicit approval.

---

## Rule 6 — Verify every remediation

A successful command is not proof that the desired state was achieved.

Use:

```text
Action
 ↓
Verify
 ↓
Record
```

---

## Rule 7 — Keep the model replaceable

The application should not be tightly coupled to one model.

The intended abstraction is:

```text
AI Orchestrator
      ↓
Provider Interface
      ↓
Ollama / Local Model
```

A future model can be introduced without redesigning the entire application.

---

# 34. Testing Strategy

Testing must happen at several levels.

## Unit Tests

Test:

- domain router
- tool schemas
- tool registry
- Linux services
- Oracle services
- OSCAP parsing
- risk classification
- approval validation

## API Tests

Test:

```text
/api/health
/api/tools
/api/linux/health
/api/oracle/health
/api/system/health
/api/ai/status
/api/chat
```

## Integration Tests

Test:

```text
FastAPI → Linux
FastAPI → Oracle
FastAPI → OpenSCAP
FastAPI → Ollama
```

## Security Tests

Test:

- unauthorized access
- invalid tool names
- invalid parameters
- command injection attempts
- SQL injection attempts
- approval bypass
- privilege escalation
- path traversal
- malformed requests

## Performance Tests

Measure:

```text
API latency
AI latency
tool latency
Oracle latency
OSCAP latency
memory usage
CPU usage
```

---

# 35. Git Strategy

The project uses Git checkpoints.

Current branch:

```text
main
```

Current state:

```text
main
 └── merged Stage 1 foundation
```

Important tags:

```text
v0.1.0-stage0
v0.2.0-stage1-linux
v0.3.0-stage1-deterministic-foundation
```

Current merge commit:

```text
c0d2102
```

The development branch:

```text
stage-1-foundation
```

is currently retained for history and should not be deleted until the current Stage 1 state is fully validated.

---

# 36. Release Strategy

Recommended progression:

```text
v0.1.0
  Stage 0 baseline

v0.2.0
  Linux foundation

v0.3.0
  Deterministic FastAPI foundation

v0.4.0
  AI orchestrator stable

v0.5.0
  AI tool calling stable

v0.6.0
  Approval + audit foundation

v0.7.0
  OSCAP finding intelligence

v0.8.0
  VAPT integration

v0.9.0
  Zabbix / RAG integration

v1.0.0
  Production-ready platform
```

Versions are planning targets and can change as implementation progresses.

---

# 37. Immediate Next Steps

The next development sequence should be:

```text
1. Make simple AI chat reliable
        ↓
2. Fix AI/tool-call latency
        ↓
3. Validate one Linux tool through AI
        ↓
4. Validate one Oracle tool through AI
        ↓
5. Validate OSCAP finding analysis
        ↓
6. Improve structured tool calling
        ↓
7. Add structured response models
        ↓
8. Add audit/event persistence
        ↓
9. Add approval workflow
        ↓
10. Add controlled remediation
        ↓
11. Add verification
        ↓
12. Add VAPT
        ↓
13. Add Zabbix
        ↓
14. Add RAG
        ↓
15. Add Ansible/Salt
        ↓
16. Production hardening
```

---

# 38. What We Are NOT Doing Yet

The following are intentionally deferred:

```text
❌ Google Colab GPU deployment
❌ llama.cpp deployment
❌ Multi-agent architecture
❌ Autonomous unrestricted remediation
❌ Arbitrary shell execution through LLM
❌ Arbitrary SQL execution through LLM
❌ RAG before core orchestration is stable
❌ Zabbix before core monitoring is stable
❌ Ansible/Salt before approval architecture is stable
❌ PostgreSQL/pgvector before scale requires it
❌ Large distributed architecture before single-node architecture is stable
```

The project should remain focused on making the current deterministic + local AI architecture reliable first.

---

# 39. Final Architecture

The long-term platform is:

```text
                           DBA / Security User
                                   │
                                   ▼
                          ┌─────────────────┐
                          │    DataPatro UI  │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │     Apache      │
                          └────────┬────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │     FastAPI     │
                          └────────┬────────┘
                                   │
                  ┌────────────────┼─────────────────┐
                  │                │                 │
                  ▼                ▼                 ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │ Domain Router│ │ AI Orchestrator│ │ API Services │
          └──────┬───────┘ └───────┬──────┘ └──────────────┘
                 │                 │
                 │                 ▼
                 │          ┌──────────────┐
                 │          │    Ollama    │
                 │          │ Local LLM    │
                 │          └──────┬───────┘
                 │                 │
                 └─────────────────┤
                                   ▼
                          ┌─────────────────┐
                          │  Tool Registry  │
                          └────────┬────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
          ┌────────────┐    ┌────────────┐    ┌────────────┐
          │Linux Tools │    │Oracle Tools│    │OSCAP Tools │
          └─────┬──────┘    └─────┬──────┘    └─────┬──────┘
                │                 │                  │
                ▼                 ▼                  ▼
              RHEL             Oracle 19c          OpenSCAP

                                   │
                                   ▼
                           ┌────────────────┐
                           │ Persistence    │
                           │ Metrics        │
                           │ Findings       │
                           │ Events         │
                           │ Actions        │
                           │ Approvals      │
                           │ Audit          │
                           └────────────────┘
```

Future execution layer:

```text
AI Recommendation
       ↓
Risk Classification
       ↓
Human Approval
       ↓
Policy Validation
       ↓
Controlled Executor
       ↓
Ansible / Salt / Fixed Actions
       ↓
Verification
       ↓
Audit
```

---

# 40. Definition of Success

The project is successful when a DBA can ask:

> "Why is my Oracle database unhealthy?"

and the platform can:

```text
1. Understand the question
2. Route it to Oracle
3. Select safe tools
4. Collect real Oracle information
5. Analyze the results
6. Explain the problem
7. Recommend a remediation
8. Classify the risk
9. Ask for human approval when required
10. Execute only an approved controlled action
11. Verify the result
12. Record the complete audit trail
```

Similarly, for Linux/security:

```text
User
 ↓
Question
 ↓
Domain Detection
 ↓
Deterministic Data Collection
 ↓
AI Analysis
 ↓
Finding
 ↓
Risk
 ↓
Recommendation
 ↓
Approval
 ↓
Controlled Action
 ↓
Verification
 ↓
Audit
```

That is the core purpose of DBA AI Agent.

---

# 41. Project Status

**Current overall status: Stage 1 — Foundation + initial AI integration**

### Working

- FastAPI foundation
- Apache reverse proxy
- Web UI
- Linux monitoring
- Linux health
- Linux tool registry
- Oracle connectivity
- Oracle health
- Oracle read-only tools
- OpenSCAP integration foundation
- Security endpoints
- Tool registry
- Domain routing
- Ollama integration
- AI status endpoint
- Initial AI orchestration

### In Progress

- Reliable simple AI chat through UI
- AI tool calling
- Tool-call performance optimization
- Structured AI responses
- AI observability

### Open

- Authentication
- RBAC
- approval persistence
- risk classification
- controlled remediation
- verification engine
- audit framework
- OSCAP finding normalization
- security hardening
- privilege reduction
- legacy Flask cleanup

### Planned

- VAPT
- Zabbix
- RAG
- Ansible/Salt
- production hardening
- broader Oracle DBA automation

---

# 42. Single Source of Truth

This `README.md` is intended to be the **single project-level source of truth** for:

- project vision
- architecture
- current implementation
- completed work
- known problems
- technical debt
- security model
- roadmap
- future architecture
- development principles
- release planning

Operational procedures and deployment-specific runbooks may remain under `docs/`, but the project should not maintain multiple competing project-level README/tracker documents.

---

# 43. Change Log

## 2026-09-11

- Consolidated project vision and roadmap into a single README.
- Documented FastAPI architecture.
- Documented Linux tooling.
- Documented Oracle 19c integration.
- Documented OpenSCAP integration.
- Documented local Ollama/llama3.2:3b architecture.
- Documented deterministic domain routing.
- Documented tool registry.
- Documented AI performance issue.
- Documented security and approval architecture.
- Documented VAPT, Zabbix, RAG and Ansible/Salt future roadmap.
- Documented technical debt and known problems.
- Documented current Git/release state.
- Removed obsolete experimental Colab and llama.cpp planning from the project roadmap.

---

## Maintainer Notes

When the architecture or implementation changes, update this README at the same checkpoint.

Do not allow the README to describe features that are not actually implemented.

The project should prefer:

```text
Working code
    ↓
Test
    ↓
Document
    ↓
Commit
    ↓
Tag checkpoint
```

over documenting future functionality as if it already exists.
