# DBA AI Agent

Local AI-powered Linux, Oracle DBA, Security and VAPT automation
platform.

## Current Stage

**Stage 1 — AI Linux & Oracle Foundation**

The project is being evolved from the original Flask-based OS
monitoring prototype into a FastAPI-based AI operations platform.

The existing Flask implementation is temporarily retained while the
FastAPI migration is developed and tested.

## Architecture

See:

[Stage 1 Architecture](docs/architecture/STAGE-1-FOUNDATION.md)

### Stage 1 Stack

- Python 3.11
- FastAPI
- Ollama
- Llama 3.2:3b
- Oracle Database 19c
- OpenSCAP
- SQLite
- Apache HTTP Server

### Stage 1 Domains

- Linux monitoring and diagnostics
- Oracle Database 19c monitoring and diagnostics
- OpenSCAP integration
- AI-assisted analysis
- Controlled tool execution
- Human approval
- Audit and verification

### Design Principle

The LLM is responsible for reasoning, tool selection and analysis.

It is not an unrestricted shell or SQL executor.

All system operations are performed through controlled Python tools.

# OS monitoring agent (local, Ollama-powered)

Monitors CPU, RAM, swap, and disk on RHEL 9, diagnoses issues with a local
Ollama model (llama3.2), and proposes fixes through a Streamlit UI. Fixes
only run when you click "Apply fix" — nothing executes automatically by
default.

## Architecture

```
collector.py  --writes-->  metrics.db (SQLite)
                                |
                                v
                          analyzer.py  --calls-->  Ollama (localhost:11434)
                                |
                                v
                          report.py  -->  reports/*.md + reports table
                                |
                                v
                            app.py (Streamlit UI)
                                |
                                v
                          automation.py (whitelisted, gated actions)
```

## 1. Install dependencies

```bash
cd os-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Confirm Ollama is running and the model is pulled:
```bash
ollama list          # should show llama3.2
curl http://localhost:11434/api/tags   # should respond
```

## 2. Run the collector

This needs to run continuously to build up history.

```bash
python3 collector.py
```

Leave it running in a terminal, tmux/screen session, or (better) install it
as a systemd service — see below.

## 3. Run the dashboard

In a second terminal:

```bash
streamlit run app.py
```

Open the URL it prints (default `http://localhost:8501`). Click **Analyze now**
to get an on-demand diagnosis from the local model, review any recommended
fix, and click **Apply fix** only if you agree with it.

## 4. Generate test load (optional, for trying it out)

Install stress-ng for realistic load generation:
```bash
sudo dnf install epel-release -y
sudo dnf install stress-ng -y
```

Then, while the collector and dashboard are running:
```bash
python3 stress_test.py cpu --seconds 60
python3 stress_test.py mem --seconds 60 --mb 2048
```

Watch the dashboard update, then click **Analyze now** to see the model
flag it and suggest a fix.

## 5. Run the collector as a systemd service (recommended for real use)

Create `/etc/systemd/system/os-agent-collector.service`:

```ini
[Unit]
Description=OS monitoring agent - metrics collector
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/os-agent
ExecStart=/opt/os-agent/venv/bin/python3 /opt/os-agent/collector.py
Restart=always
RestartSec=5
User=os-agent

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo cp -r os-agent /opt/os-agent
sudo useradd -r -s /sbin/nologin os-agent || true
sudo chown -R os-agent:os-agent /opt/os-agent
sudo systemctl daemon-reload
sudo systemctl enable --now os-agent-collector
sudo systemctl status os-agent-collector
```

For the dashboard, either run `streamlit run app.py` manually when you want
to check on things, or wrap it in a similar systemd unit and put it behind
a reverse proxy (nginx/httpd) if you want it reachable outside localhost.

## 6. Serve it through Apache instead (proper web UI)

If you want a real ChatGPT-style web UI served on port 80, reachable from
any browser on your network, use the Flask + Apache setup instead of
Streamlit. This still uses the same collector.py, analyzer.py, etc. --
`api.py` and `static/` are a second, web-native frontend on top of the
same backend logic.

Architecture: Apache serves `static/` (HTML/CSS/JS) directly and reverse
proxies `/api/*` to Gunicorn, which runs the Flask app (`api.py`).

```bash
# 1. Install deps (flask + gunicorn are already in requirements.txt)
source venv/bin/activate
pip install -r requirements.txt

# 2. Move the project to /opt (matches the systemd unit's WorkingDirectory)
sudo cp -r os-agent /opt/os-agent
sudo useradd -r -s /sbin/nologin os-agent || true
sudo chown -R os-agent:os-agent /opt/os-agent

# 3. Install and enable the Gunicorn service
sudo cp /opt/os-agent/deploy/os-agent-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now os-agent-web
sudo systemctl status os-agent-web    # should show "active (running)"

# 4. Install Apache (httpd) if not already present
sudo dnf install httpd -y
sudo systemctl enable --now httpd

# 5. Install the vhost config
sudo cp /opt/os-agent/deploy/os-agent-apache.conf /etc/httpd/conf.d/os-agent.conf
sudo setsebool -P httpd_can_network_connect 1   # SELinux: allow proxying
sudo systemctl restart httpd

# 6. Open the firewall (if enabled)
sudo firewall-cmd --add-service=http --permanent
sudo firewall-cmd --reload
```

Then open `http://<server-ip>/` in any browser. You'll get:
- A **Dashboard** tab with live CPU/mem/swap/disk cards, a trend chart, and the same
  analyze/apply-fix flow as the Streamlit version.
- A **Chat control** tab -- type prompts like `stop splunkd`, get a confirm
  prompt, click to execute. This is the ChatGPT-style interface.

Don't forget the collector still needs to run separately (see step 5's
systemd unit, `os-agent-collector.service`) -- the web UI only reads from
`metrics.db`, it doesn't collect metrics itself.

**Troubleshooting the web setup:**
- Blank page / 502 from Apache → Gunicorn isn't running: `sudo systemctl status os-agent-web` and check logs with `sudo journalctl -u os-agent-web -f`.
- `/api/*` calls fail with connection refused in the browser console → same as above, or the ProxyPass port doesn't match (`8000` in both the service file and the Apache conf).
- 403 from SELinux even after `setsebool` → check `sudo ausearch -m avc -ts recent` for denials and `restorecon -Rv /opt/os-agent/static`.
- Chat says "not a service" for something you know is running → the parser strips `.service`; try the bare name (e.g. `nginx` not `nginx.service`).

## Extending automation safely

All executable actions live in `automation.py`'s `WHITELIST` dict — the LLM
can only ever recommend an action by its key, never a freeform command.

- Start with `REQUIRE_CONFIRMATION = True` in `config.py` (default) so every
  fix needs a manual click in the UI.
- Once you trust a specific low-risk action (e.g. `clear_tmp_cache`), you
  can wire it to auto-execute on "critical" severity by calling
  `automation.execute(key, confirm=True)` directly from `analyzer.py` —
  but do this per-action, deliberately, not as a blanket policy.
- Never add a whitelist entry that takes a parameter from LLM output
  (like a PID or filename) without validating it strictly — that's how you
  get command injection.

## Tuning

- `config.THRESHOLDS` — percentages that count as concerning (not currently
  wired to auto-trigger analysis, but useful if you want to add a "only
  analyze when over threshold" check in a cron-driven loop).
- `config.POLL_INTERVAL_SECONDS` — collector sampling frequency.
- `config.DISK_MOUNTS` — add more mount points to monitor, e.g. `["/", "/var", "/home"]`.
- `analyzer.py`'s `analyze(minutes=5)` — change the analysis window.

## Files

| File | Purpose |
|---|---|
| `config.py` | thresholds, paths, Ollama settings, OpenSCAP settings |
| `collector.py` | psutil-based sampler, writes to SQLite |
| `analyzer.py` | summarizes metrics, calls Ollama, parses JSON diagnosis |
| `automation.py` | whitelisted, gated remediation actions |
| `report.py` | renders markdown reports, logs history |
| `service_control.py` | validated systemctl wrapper (start/stop/restart/status), uses scoped sudo for state changes |
| `chat_agent.py` | regex fast-path + Ollama tool-calling agent for free-text prompts |
| `tools.py` | read-only inspection tools the chat agent can call (processes, disk, ports, logs) |
| `oscap_tool.py` | OpenSCAP integration — async security/compliance scans, LLM-summarized findings |
| `app.py` | Streamlit dashboard (quick local iteration) |
| `api.py` | Flask REST API for the web UI (production path) |
| `static/` | HTML/CSS/JS frontend served by Apache/Flask |
| `deploy/` | Apache vhost + systemd units for collector and web app |
| `docs/PROJECT_LOG.md` | why every design decision was made, plus a full troubleshooting journal |
| `docs/DEPLOY_RUNBOOK.md` | pure command sequence to deploy from scratch |
| `stress_test.py` | generates CPU/memory load for testing |

See `docs/PROJECT_LOG.md` for the full history of what's been built and why,
and `docs/DEPLOY_RUNBOOK.md` for the exact deployment command sequence.
