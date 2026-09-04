# OS Monitoring Agent — Project Documentation

**Host:** RHEL 9.8 (`ol9-19`)
**LLM backend:** Ollama, running fully local (`llama3.2:3B`, `llama3.2:1b`)
**Deployed location:** `/opt/os-agent` (single source of truth — see "Where things live")

---

## 1. What we set out to build

Starting point: Ollama + llama3.2 already running locally on RHEL, purely text-based (terminal only).

Goal: turn that into an agent with:
1. A **UI**, not just a terminal.
2. **Basic OS monitoring** — CPU, RAM, swap, disk.
3. **AI-generated reports** — not just raw numbers, but a diagnosis and a suggested fix.
4. **Prompt-driven actions** — type something like "stop splunkd" and have it actually happen, safely, through a chat-style interface.
5. Served properly over **Apache**, not just a dev server, so it's reachable like a real web app.

---

## 2. Architecture — what we built and why

### 2.1 Overall shape

```
psutil (collector.py) --writes--> SQLite (metrics.db)
                                        |
                        +---------------+---------------+
                        |                                |
              analyzer.py (calls Ollama)         api.py reads metrics
                        |                                |
                report.py (saves report)         served to dashboard
                        |
              automation.py (whitelisted fixes, gated by confirmation)

chat_agent.py (regex fast-path, Ollama fallback) --> service_control.py (systemctl, validated)
                                                            |
                                                   gated by confirm=True

Apache (:80) --serves--> static/ (HTML/CSS/JS)
             --proxies /api--> Gunicorn (:8800) --> api.py (Flask)
```

### 2.2 Why each piece exists

**Collector writes to SQLite instead of streaming raw metrics into every LLM call.**
Sending raw time-series data to the model every cycle burns context and produces noisy, inconsistent analysis. Instead, `collector.py` just samples and stores; `analyzer.py` summarizes (avg/max over a window, trend direction) only when an analysis is actually requested.

**The LLM never runs a shell command directly.**
This was a deliberate safety boundary from the start. `analyzer.py` and `chat_agent.py` ask the model to return a *structured intent* (a JSON action from a fixed enum + a service/action name), never a raw command string. `automation.py` and `service_control.py` are the only things that ever call `subprocess`, and they only accept known-safe, pre-validated inputs.

**Service names are validated before anything touches `systemctl`.**
`service_control.py` checks the name against a strict regex (`^[a-zA-Z0-9_.\-@]+$`) *and* confirms the unit actually exists via `systemctl list-unit-files` before allowing any action. This blocks both injection attempts (`splunkd; rm -rf /`) and acting on made-up service names.

**State-changing actions always require explicit confirmation.**
Start/stop/restart never fire on the first message — the UI always shows a confirm/cancel step first (`REQUIRE_CONFIRMATION = True` in `config.py`, enforced independently in the backend too, not just the frontend). Status checks and listing are read-only and run immediately.

**Remediation actions are whitelisted, not freeform.**
`automation.py`'s `WHITELIST` dict is the *only* set of things the "Apply fix" button can ever run (clear tmp, clear yum cache, drop page cache, etc.). The LLM can recommend one of these keys — it cannot invent a new command.

**Regex fast-path added later, for reliability.**
Originally *every* chat message went through Ollama to parse intent — including simple, unambiguous ones like "list services" or "is httpd running." Under load (see §4.8–4.9 below), this made even trivial commands fail. We added a regex layer in `chat_agent.py` that resolves common phrasing instantly, with Ollama only as a fallback for genuinely ambiguous free-form text.

### 2.3 Two UIs, on purpose

We built two frontends against the same backend logic:

- **Streamlit (`app.py`)** — fast to iterate on, good for local testing, not meant for production serving.
- **Flask + static HTML/CSS/JS (`api.py` + `static/`)** — the real deployment path, served through Apache on port 80, styled like a proper web app with a Dashboard tab and a ChatGPT-style Chat control tab.

Both call the same underlying modules (`collector`, `analyzer`, `automation`, `service_control`, `chat_agent`), so nothing is duplicated — only the presentation layer differs.

---

## 3. File inventory

| File | Purpose |
|---|---|
| `config.py` | Central config: DB path, poll interval, Ollama URL/model, thresholds |
| `collector.py` | Samples CPU/RAM/swap/disk via `psutil`, writes to SQLite |
| `analyzer.py` | Summarizes recent samples, calls Ollama, returns structured JSON diagnosis |
| `automation.py` | Whitelisted, gated remediation actions (clear cache, etc.) |
| `report.py` | Renders markdown reports from analysis results, logs history |
| `service_control.py` | Validated `systemctl` wrapper — the only thing that runs start/stop/restart/status |
| `chat_agent.py` | Parses free-text prompts into structured intents (regex fast-path + Ollama fallback) |
| `app.py` | Streamlit dashboard (local iteration) |
| `api.py` | Flask REST API — the production backend behind Apache |
| `static/index.html`, `style.css`, `app.js` | Web UI: Dashboard tab + Chat control tab |
| `deploy/os-agent-apache.conf` | Apache vhost — serves `static/`, proxies `/api/*` to Gunicorn |
| `deploy/os-agent-web.service` | systemd unit running Gunicorn/Flask |
| `deploy/os-agent-collector.service` | systemd unit running the collector continuously |
| `stress_test.py` | Generates CPU/memory load for testing detection end-to-end |

---

## 4. The deployment journey — every issue hit, and why

This is the part worth keeping around. Almost every bug below came from **environment/config drift**, not application logic — a good reminder that in ops work, "where is this actually running, as whom, reading what" matters as much as the code itself.

### 4.1 Ollama 404 on `/api/generate`
**Symptom:** `requests.exceptions.HTTPError: 404 Client Error: Not Found`
**Cause:** `config.py` had `OLLAMA_MODEL = "llama3.2"`, but the actual installed models were tagged `llama3.2:3B` and `llama3.2:1b`. Ollama matches model names exactly, including the tag.
**Fix:** `ollama list` to get the exact name, updated `config.py` to `"llama3.2:3B"`.
**Lesson:** always verify exact model names against `ollama list` / `curl localhost:11434/api/tags` rather than assuming the short name works.

### 4.2 Collector run from the wrong directory
**Symptom:** `python3 collector.py --once` → `No such file or directory`.
**Cause:** Only `collector.py` had been copied over (into `/tmp`), not the rest of the project — the script needs `config.py` in the same folder, and the user was running it from `/root` anyway.
**Fix:** copied the *entire* project folder together via `scp`, ran commands from inside it.

### 4.3 Apache 501 — blank/missing page
**Symptom:** Apache returned an error asking for content that "doesn't exist."
**Cause:** `index.html`, `style.css`, `app.js` had been placed directly in `/opt/os-agent/` instead of `/opt/os-agent/static/` — which is what both Apache's `DocumentRoot` and Flask's `static_folder` expected.
**Fix:** `mkdir static && mv index.html style.css app.js static/`.

### 4.4 Port 8000 already in use — turned out to be Splunk
**Symptom:** Gunicorn: `Address already in use` on port 8000. curl to that port returned a real HTTP response — but it was a **Splunk** redirect (`Server: Splunkd` header), not our app.
**Cause:** Splunk's own web interface listens on port 8000 by default. It grabbed the port before Gunicorn could.
**Fix:** moved the whole app to port **8800** — updated both `os-agent-web.service` (`-b 127.0.0.1:8800`) and `os-agent-apache.conf` (`ProxyPass /api http://127.0.0.1:8800/api`).
**Lesson:** always check what's already listening on a port (`ss -ltnp`) before assuming a fresh app can bind it — especially on a box with other services like Splunk installed.

### 4.5 Broken virtual environment after being moved
**Symptom:** Gunicorn workers crashed on boot with unrelated-looking import tracebacks referencing a path like `/os-agent/venv/...` even though the project now lived at `/opt/os-agent`.
**Cause:** the venv was originally created in a differently-named folder (`/os-agent`) and then copied/moved to `/opt/os-agent`. **Python virtual environments are not relocatable** — they bake absolute paths into their internals, so a copied venv silently breaks.
**Fix:** `rm -rf venv`, recreated it fresh in place (`python3 -m venv venv`), reinstalled dependencies.
**Lesson:** never copy a venv folder between locations — always delete and recreate it at the destination.

### 4.6 `ModuleNotFoundError: No module named 'service_control'`
**Cause:** the file existed in the working project but had simply never been copied onto the server — it was missed during one of the manual file transfers.
**Fix:** copied it over explicitly, confirmed with `ls`.
**Lesson:** when copying files by hand instead of syncing a whole folder, it's easy to miss one — worth doing a file-count/diff check after any manual transfer.

### 4.7 Permission conflicts from switching users mid-project
**Symptom:** `sqlite3.OperationalError: attempt to write a readonly database`.
**Cause:** the project directory ownership and the user actually running each script kept diverging over the course of debugging — root vs. a dedicated `os-agent` service user vs. the personal `vaibhav` account.
**Fix:** standardized on one approach — `chown -R vaibhav:vaibhav /opt/os-agent`, and both systemd services (`os-agent-web.service`, `os-agent-collector.service`) set to `User=vaibhav` to match. Ownership and the systemd `User=` directive must always agree.
**Lesson:** pick one user for a given deployment and keep file ownership and service `User=` in sync everywhere, every time either one changes.

### 4.8 Gunicorn killing workers on slow Ollama responses
**Symptom:** "Analyze now" and chat prompts sometimes returned a bare `Internal Server Error` with no useful message, even though the same request worked moments earlier.
**Cause:** Gunicorn's default worker timeout is 30 seconds. Under heavy synthetic load (CPU and swap pinned at 100% during `stress_test.py` runs), Ollama itself slowed down enough that requests exceeded 30s. Gunicorn killed the worker mid-request — bypassing our own error handling entirely, since the process was terminated, not just the request.
**Fix:** added `--timeout 180` to the Gunicorn `ExecStart` command in `os-agent-web.service`.
**Lesson:** any reverse-proxied app with a slow backend (LLM calls, external APIs) needs its worker timeout set deliberately longer than the slowest expected call — the default is tuned for typical web requests, not LLM inference.

### 4.9 Chat commands unnecessarily dependent on the LLM
**Symptom:** even simple, unambiguous commands like "list running services" or "is httpd running" failed whenever Ollama was slow or briefly unavailable.
**Cause:** the original design routed *every* chat message through Ollama for intent parsing, even messages with obvious, fixed structure.
**Fix:** added a regex-based fast path in `chat_agent.py` that resolves common phrasing ("list/show services", "is X running", "stop/start/restart X") instantly, with zero dependency on Ollama. The LLM is now only consulted as a fallback for genuinely ambiguous free-form phrasing.
**Lesson:** don't route deterministic, pattern-matchable requests through a model — reserve the LLM for the parts of the problem that actually need it.

### 4.10 Silent frontend failures made debugging harder than it needed to be
**Symptom:** clicking "Analyze now" or sending a chat message sometimes appeared to do nothing at all.
**Cause:** the original frontend JS didn't check `response.ok` or catch fetch errors — a failed request just silently did nothing, with the real error only visible in server-side logs the user had to know to check.
**Fix:** added explicit error handling throughout `static/app.js` and in `analyzer.py`/`chat_agent.py` (catching `requests.exceptions.RequestException` and returning a clear, readable message) so failures now show up directly in the UI with an actionable hint (e.g. "check `journalctl -u os-agent-web -f`").
**Lesson:** always surface backend failures to the UI in some form during early development — silent failures multiply debugging time because the person testing has no idea whether the request even reached the server.

---

## 5. Current final configuration (as of last working state)

- **Project root:** `/opt/os-agent` — the only copy in use. Any earlier copies (e.g. under `/root`) are dead and should be ignored/removed.
- **Owner:** `vaibhav` for all files under `/opt/os-agent`, including `venv/` and `metrics.db`.
- **Ollama model:** `llama3.2:3B` (set in `config.py`), reachable at `http://localhost:11434`.
- **Gunicorn:** binds `127.0.0.1:8800` (not 8000 — that's Splunk), `--timeout 180`, runs as `User=vaibhav` via `os-agent-web.service`.
- **Apache:** serves `/opt/os-agent/static` as `DocumentRoot`, proxies `/api/*` to `http://127.0.0.1:8800/api`, listens on port 80.
- **Collector:** runs continuously via `os-agent-collector.service`, also as `vaibhav`, writing to `/opt/os-agent/metrics.db`.

### Services to know

| systemd unit | What it runs | Port |
|---|---|---|
| `os-agent-collector` | `collector.py` — metrics sampling loop | n/a (writes to SQLite) |
| `os-agent-web` | `gunicorn` running `api.py` (Flask) | 127.0.0.1:8800 |
| `httpd` (Apache) | serves frontend + reverse proxy | 0.0.0.0:80 |
| `ollama` | local LLM inference | 127.0.0.1:11434 |

### Common operational commands

```bash
# Check everything is up
sudo systemctl status os-agent-collector os-agent-web httpd ollama

# Restart the app after a code change
sudo systemctl restart os-agent-web
sudo systemctl restart httpd

# Watch logs live
sudo journalctl -u os-agent-web -f
sudo journalctl -u os-agent-collector -f

# Quick backend sanity check, bypassing Apache entirely
curl -X POST http://127.0.0.1:8800/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"is httpd running"}'
```

---

## 6. Safety model recap (worth remembering)

- The LLM only ever proposes an **action key** or a **structured intent** — never a shell command.
- Every service name is validated against real systemd units before any action runs.
- Start/stop/restart always require explicit confirmation in the UI; status/list are read-only and immediate.
- Remediation "fixes" are limited to a fixed whitelist in `automation.py` — nothing outside that list can be executed via the "Apply fix" button.
- If you ever extend the whitelist or the chat action set, keep following this pattern: validate inputs strictly, never let LLM output become a raw command string, and keep state-changing actions behind confirmation.

---

## 7. Open items / things worth revisiting later

- The systemd services currently run as your personal user (`vaibhav`) rather than a dedicated service account — fine for now, but worth reconsidering for a longer-lived deployment (least-privilege).
- No authentication on the web UI — anyone on the network who can reach port 80 can use it, including the chat-based service control. Worth adding basic auth or restricting network access if this moves beyond a personal test box.
- `REQUIRE_CONFIRMATION` is a global switch in `config.py`. If you ever want specific low-risk actions to auto-execute, do it deliberately per-action rather than flipping the global flag.
- Gunicorn timeout of 180s is a workaround for slow Ollama under load — if this keeps happening, it's worth investigating why inference is slow (resource contention with stress testing, model size, concurrent requests) rather than just extending timeouts indefinitely.
