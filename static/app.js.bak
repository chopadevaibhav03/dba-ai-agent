const API = "/api";

// ---------- tabs ----------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  });
});

// ---------- dashboard ----------
let trendChart = null;

async function loadLatest() {
  try {
    const res = await fetch(`${API}/metrics/latest`);
    const data = await res.json();
    if (!data.ok) return;
    const s = data.sample;
    document.getElementById("m-cpu").textContent = s.cpu_percent.toFixed(1) + "%";
    document.getElementById("m-mem").textContent = s.mem_percent.toFixed(1) + "%";
    document.getElementById("m-swap").textContent = s.swap_percent.toFixed(1) + "%";
    const rootPct = (s.disk && s.disk["/"] && s.disk["/"].percent) || 0;
    document.getElementById("m-disk").textContent = rootPct.toFixed(1) + "%";
  } catch (e) { /* collector may not have written data yet */ }
}

async function loadHistory() {
  try {
    const res = await fetch(`${API}/metrics/history?limit=100`);
    const data = await res.json();
    if (!data.ok || !data.samples.length) return;
    const labels = data.samples.map(s => new Date(s.ts).toLocaleTimeString());
    const cpu = data.samples.map(s => s.cpu_percent);
    const mem = data.samples.map(s => s.mem_percent);
    const swap = data.samples.map(s => s.swap_percent);

    const ctx = document.getElementById("trend-chart");
    if (trendChart) {
      trendChart.data.labels = labels;
      trendChart.data.datasets[0].data = cpu;
      trendChart.data.datasets[1].data = mem;
      trendChart.data.datasets[2].data = swap;
      trendChart.update("none");
    } else {
      trendChart = new Chart(ctx, {
        type: "line",
        data: {
          labels,
          datasets: [
            { label: "CPU %", data: cpu, borderColor: "#378ADD", tension: 0.25, pointRadius: 0 },
            { label: "Memory %", data: mem, borderColor: "#1D9E75", tension: 0.25, pointRadius: 0 },
            { label: "Swap %", data: swap, borderColor: "#D85A30", tension: 0.25, pointRadius: 0 },
          ],
        },
        options: {
          responsive: true,
          animation: false,
          scales: { y: { beginAtZero: true, max: 100 } },
          plugins: { legend: { position: "bottom" } },
        },
      });
    }
  } catch (e) { /* ignore */ }
}

function severityBadge(sev) {
  const cls = { critical: "sev-critical", warning: "sev-warning", info: "sev-info" }[sev] || "sev-info";
  return `<span class="severity-badge ${cls}">${sev.toUpperCase()}</span>`;
}

async function renderAnalysis(result) {
  const body = document.getElementById("analysis-body");
  let html = `<p>${severityBadge(result.severity || "info")}<strong>${result.issue || ""}</strong></p>`;
  html += `<p class="muted">${result.root_cause || ""}</p>`;

  const actions = result.recommended_actions || [];
  if (actions.length) {
    html += `<p><strong>Recommended actions</strong> (review before applying):</p>`;
    for (const key of actions) {
      html += `<div class="action-row" data-action="${key}">
        <span>${key}</span>
        <button class="btn btn-secondary apply-btn" data-key="${key}">Apply fix</button>
      </div>`;
    }
  } else {
    html += `<p class="muted">No action recommended.</p>`;
  }
  body.innerHTML = html;

  body.querySelectorAll(".apply-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "Applying...";
      const res = await fetch(`${API}/actions/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action_key: btn.dataset.key }),
      });
      const data = await res.json();
      btn.textContent = data.ok ? "Applied" : "Failed";
      if (!data.ok) btn.title = data.error || data.stderr || "Unknown error";
    });
  });
}

async function loadReportHistory() {
  const res = await fetch(`${API}/reports`);
  const data = await res.json();
  const el = document.getElementById("report-history");
  if (!data.ok || !data.reports.length) {
    el.innerHTML = `<p class="muted">No reports yet.</p>`;
    return;
  }
  let rows = data.reports.map(r => `
    <tr>
      <td>${new Date(r.ts).toLocaleString()}</td>
      <td>${severityBadge(r.severity || "info")}</td>
      <td>${r.issue || ""}</td>
    </tr>`).join("");
  el.innerHTML = `<table><thead><tr><th>Time</th><th>Severity</th><th>Issue</th></tr></thead><tbody>${rows}</tbody></table>`;
}

document.getElementById("analyze-btn").addEventListener("click", async () => {
  const btn = document.getElementById("analyze-btn");
  btn.disabled = true;
  btn.textContent = "Analyzing...";
  try {
    const res = await fetch(`${API}/analyze`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    if (!res.ok) {
      const text = await res.text();
      document.getElementById("analysis-body").innerHTML =
        `<p style="color:#a32d2d">Server error (${res.status}). Check: sudo journalctl -u os-agent-web -n 30</p>
         <pre style="white-space:pre-wrap;font-size:11px;">${text.slice(0, 500)}</pre>`;
      return;
    }
    const data = await res.json();
    if (data.ok) {
      await renderAnalysis(data.result);
      await loadReportHistory();
    } else {
      document.getElementById("analysis-body").innerHTML =
        `<p style="color:#a32d2d">${data.error || "Analysis failed"}</p>`;
    }
  } catch (err) {
    document.getElementById("analysis-body").innerHTML =
      `<p style="color:#a32d2d">Network error: ${err.message}</p>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze now";
  }
});

loadLatest();
loadHistory();
loadReportHistory();
setInterval(loadLatest, 10000);
setInterval(loadHistory, 15000);

// ---------- chat control ----------
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg msg-${role}`;
  div.textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return div;
}

function addServiceConfirm(service, action, promptText) {
  const div = document.createElement("div");
  div.className = "msg msg-confirm";
  div.innerHTML = `<div>${promptText}</div>
    <div class="confirm-actions">
      <button class="btn btn-primary confirm-yes">Yes, do it</button>
      <button class="btn btn-secondary confirm-no">Cancel</button>
    </div>`;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;

  div.querySelector(".confirm-yes").addEventListener("click", async () => {
    div.querySelectorAll("button").forEach(b => b.disabled = true);
    const res = await fetch(`${API}/service/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service, action, confirm: true }),
    });
    const data = await res.json();
    div.remove();
    if (data.ok) {
      addMessage("assistant", `Done. ${data.service} is now ${data.new_state || "updated"}.`);
    } else {
      addMessage("assistant", `Failed: ${data.error || data.stderr || "unknown error"}`);
    }
  });

  div.querySelector(".confirm-no").addEventListener("click", () => {
    div.remove();
    addMessage("assistant", "Cancelled, no changes made.");
  });
}

function addRemediationConfirm(actionKey, promptText) {
  const div = document.createElement("div");
  div.className = "msg msg-confirm";
  div.innerHTML = `<div>${promptText}</div>
    <div class="confirm-actions">
      <button class="btn btn-primary confirm-yes">Yes, run it</button>
      <button class="btn btn-secondary confirm-no">Cancel</button>
    </div>`;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;

  div.querySelector(".confirm-yes").addEventListener("click", async () => {
    div.querySelectorAll("button").forEach(b => b.disabled = true);
    const res = await fetch(`${API}/actions/apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_key: actionKey }),
    });
    const data = await res.json();
    div.remove();
    if (data.ok) {
      addMessage("assistant", `Done. Ran: ${actionKey}.`);
    } else {
      addMessage("assistant", `Failed: ${data.error || data.stderr || "unknown error"}`);
    }
  });

  div.querySelector(".confirm-no").addEventListener("click", () => {
    div.remove();
    addMessage("assistant", "Cancelled, no changes made.");
  });
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  addMessage("user", text);
  chatInput.value = "";

  try {
    const res = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    if (!res.ok) {
      addMessage("assistant", `Server error (${res.status}). Check gunicorn logs: journalctl -u os-agent-web -f`);
      return;
    }
    const data = await res.json();

    if (!data.ok) {
      addMessage("assistant", data.error || "Something went wrong.");
      return;
    }

    if (data.type === "confirm_service") {
      addServiceConfirm(data.service, data.action, data.reply);
    } else if (data.type === "confirm_remediation") {
      addRemediationConfirm(data.action_key, data.reply);
    } else if (data.type === "scan_started") {
      addMessage("assistant", data.reply);
      pollScan(data.scan_id, null);  // no dedicated UI target from chat -- just let it finish in the background
    } else {
      addMessage("assistant", data.reply);
    }
  } catch (err) {
    addMessage("assistant", `Network error reaching the API: ${err.message}`);
  }
});

// ---------- security scan tab ----------

function severityColor(sev) {
  return { high: "#a32d2d", medium: "#854f0b", low: "#6b6a66" }[sev] || "#6b6a66";
}

function renderScanResult(data) {
  const el = document.getElementById("scan-body");
  if (!el) return;  // chat-triggered scan with no visible target

  if (data.status === "queued" || data.status === "running") {
    el.innerHTML = `<p class="muted">Scan ${data.status}... this can take several minutes for a full profile.</p>`;
    return;
  }
  if (data.status === "error") {
    el.innerHTML = `<p style="color:#a32d2d">Scan failed: ${data.error}</p>`;
    return;
  }

  const s = data.summary || {};
  const p = data.parsed || {};
  const counts = p.counts || {};

  let html = `<p><strong>Overall risk: ${(s.overall_risk || "unknown").toUpperCase()}</strong></p>`;
  html += `<p class="muted">${s.summary || ""}</p>`;
  html += `<p class="muted">Checked ${p.total_rules_checked || 0} rules -- `;
  html += Object.entries(counts).map(([k, v]) => `${v} ${k}`).join(", ");
  html += `</p>`;

  if ((s.priorities || []).length) {
    html += `<p><strong>Priorities</strong></p>`;
    for (const item of s.priorities) {
      const fixId = `fix-${(item.rule_id || "").replace(/[^a-zA-Z0-9]/g, '')}`;
      html += `<div class="action-row" style="display:block;">
        <div><strong>${item.title}</strong></div>
        <div class="muted">${item.why_it_matters || ""}</div>
        <button class="btn btn-secondary fix-btn" data-rule="${item.rule_id}" data-target="${fixId}">Ask agent to fix this</button>
        <div id="${fixId}"></div>
      </div>`;
    }
  }

  if ((p.fails || []).length) {
    html += `<p><strong>All failed checks (${p.fails.length})</strong></p>`;
    for (const f of p.fails.slice(0, 30)) {
      html += `<div class="action-row">
        <span>${f.rule}</span>
        <span style="color:${severityColor(f.severity)};font-size:12px;">${f.severity}</span>
      </div>`;
    }
  }

  if (data.report_html_path) {
    html += `<p style="margin-top:12px;"><a href="/api/security/report/${data._scan_id}" target="_blank">View full HTML report</a></p>`;
  }

  el.innerHTML = html;

  el.querySelectorAll(".fix-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const res = await fetch(`${API}/security/fix`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scan_id: data._scan_id, rule_id: btn.dataset.rule, confirm: false }),
      });
      const info = await res.json();
      const target = document.getElementById(btn.dataset.target);
      if (!info.fix_script) {
        target.innerHTML = `<p style="color:#a32d2d">${info.error || "No fix script available."}</p>`;
        return;
      }
      target.innerHTML = `<pre style="white-space:pre-wrap;font-size:11px;">${info.fix_script}</pre>
        <button class="btn btn-primary confirm-fix-yes">Yes, apply it</button>
        <button class="btn btn-secondary confirm-fix-no">Cancel</button>`;
      target.querySelector(".confirm-fix-yes").addEventListener("click", async () => {
        target.innerHTML = "Applying...";
        const r2 = await fetch(`${API}/security/fix`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scan_id: data._scan_id, rule_id: btn.dataset.rule, confirm: true }),
        });
        const result = await r2.json();
        target.innerHTML = result.ok ? "Fixed." : `Failed: ${result.stderr || result.error}`;
      });
      target.querySelector(".confirm-fix-no").addEventListener("click", () => { target.innerHTML = ""; });
    });
  });
}

function pollScan(scanId, targetEl) {
  const interval = setInterval(async () => {
    const res = await fetch(`${API}/security/scan/${scanId}`);
    const data = await res.json();
    if (!data.ok) {
      clearInterval(interval);
      return;
    }
    data._scan_id = scanId;
    if (targetEl !== null) renderScanResult(data);
    if (data.status === "done" || data.status === "error") {
      clearInterval(interval);
      if (data.status === "done" && targetEl === null) {
        addMessage("assistant", `Security scan finished. Overall risk: ${(data.summary || {}).overall_risk || "unknown"}. Check the Security tab for details.`);
      }
    }
  }, 5000);
}

const scanBtn = document.getElementById("scan-btn");
if (scanBtn) {
  scanBtn.addEventListener("click", async () => {
    scanBtn.disabled = true;
    document.getElementById("scan-body").innerHTML = `<p class="muted">Starting scan...</p>`;
    try {
      const res = await fetch(`${API}/security/scan`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      });
      const data = await res.json();
      if (data.ok) {
        pollScan(data.scan_id, "scan-body");
      } else {
        document.getElementById("scan-body").innerHTML = `<p style="color:#a32d2d">${data.error}</p>`;
      }
    } finally {
      scanBtn.disabled = false;
    }
  });
}