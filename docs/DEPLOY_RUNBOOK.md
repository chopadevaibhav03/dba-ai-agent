# Deployment runbook — OS Monitoring Agent

Commands only, in order, to get the web UI running on a fresh RHEL 9 box.
Assumes the project files already exist somewhere accessible (e.g. you have
them locally and will paste/copy them onto the server).

All commands below assume the project lives at **`/opt/os-agent`**. Every
command runs from that one location — don't mix in any other copy.

---

## 1. Place the project and set ownership

```bash
sudo mkdir -p /opt/os-agent
sudo chown -R $(whoami):$(whoami) /opt/os-agent
```

Copy all project files (`.py` files, `static/`, `deploy/`, `requirements.txt`)
into `/opt/os-agent`. If pasting file contents directly instead of
transferring files, use `cat > filename << 'EOF' ... EOF` for each one.

```bash
cd /opt/os-agent
ls
# should show: analyzer.py api.py app.py automation.py chat_agent.py
# collector.py config.py report.py service_control.py stress_test.py
# requirements.txt static/ deploy/
```

---

## 2. Create the Python virtual environment (fresh, in place)

**Never copy a venv folder from elsewhere — always create it here, directly.**

```bash
cd /opt/os-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Confirm Ollama is reachable and note the exact model name

```bash
curl http://localhost:11434/api/tags
```

Copy the exact `"name"` value from the output (e.g. `llama3.2:3B` — case
and tag matter). Set it in `config.py`:

```bash
grep OLLAMA_MODEL config.py
# edit config.py if it doesn't match exactly what ollama list/api showed
```

---

## 4. Sanity-check the collector by hand

```bash
cd /opt/os-agent
source venv/bin/activate
python3 collector.py --once
```

Should print a JSON snapshot of CPU/RAM/swap/disk. If this fails, fix it
before continuing — nothing downstream will work otherwise.

---

## 5. Check for port conflicts before binding anything

```bash
ss -ltnp | grep 8800
```

Should be empty. (On this host, port 8000 was already taken by Splunk's
web UI — that's why this project uses **8800** instead. If 8800 is also
taken on your box, pick another free port and update it in both
`deploy/os-agent-web.service` and `deploy/os-agent-apache.conf`.)

---

## 6. Install the systemd services

```bash
sudo cp /opt/os-agent/deploy/os-agent-collector.service /etc/systemd/system/
sudo cp /opt/os-agent/deploy/os-agent-web.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Both `.service` files have `User=` set to whoever owns `/opt/os-agent`
(step 1). If you used a different user, edit `User=` in both files to match
before copying them in.

```bash
sudo systemctl enable --now os-agent-collector
sudo systemctl status os-agent-collector
# should say: active (running)

sudo systemctl enable --now os-agent-web
sudo systemctl status os-agent-web
# should say: active (running) -- wait 15s and check again to rule out crash-looping
```

If either fails, check logs immediately rather than guessing:
```bash
sudo journalctl -u os-agent-collector -n 40 --no-pager
sudo journalctl -u os-agent-web -n 40 --no-pager
```

---

## 7. Test the API directly, bypassing Apache

```bash
curl http://127.0.0.1:8800/api/metrics/latest
curl -X POST http://127.0.0.1:8800/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"list running services"}'
```

Both should return real JSON. If not, stop here and fix it before touching
Apache — Apache just forwards to this, it can't fix a broken backend.

---

## 8. Install and configure Apache

```bash
sudo dnf install httpd -y
sudo systemctl enable --now httpd

sudo cp /opt/os-agent/deploy/os-agent-apache.conf /etc/httpd/conf.d/os-agent.conf
sudo setsebool -P httpd_can_network_connect 1
sudo systemctl restart httpd
```

Check the static files are where Apache expects them:
```bash
ls /opt/os-agent/static/
# should show: index.html style.css app.js
```

---

## 9. Open the firewall

```bash
sudo firewall-cmd --add-service=http --permanent
sudo firewall-cmd --reload
```

---

## 10. Load it in a browser

```
http://<server-ip>/
```

Dashboard tab should show live CPU/Mem/Swap/Disk numbers within ~10-20
seconds (as the collector writes samples). Chat control tab: try
`list running services` or `is httpd running` — these resolve instantly
without needing Ollama. Try `stop <some-service>` to see the confirm flow.

---

## Quick reference: logs and troubleshooting commands

```bash
# Live logs
sudo journalctl -u os-agent-web -f
sudo journalctl -u os-agent-collector -f
sudo tail -f /var/log/httpd/os-agent-error.log

# Restart everything
sudo systemctl restart os-agent-collector os-agent-web httpd

# Check what's listening where
ss -ltnp | grep -E '80|8800|11434'

# Confirm ownership matches the service's User= line
ls -la /opt/os-agent
grep User= /etc/systemd/system/os-agent-web.service
```
