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

// ============================================================
// Linux Monitoring UI
// ============================================================

async function loadLinuxHealth() {

  try {

    const res = await fetch(`${API}/linux/health`);

    const result = await res.json();

    if (!result.ok) {
      console.error("Linux health API failed:", result);
      return;
    }

    const health = result.health || {};
    const data = result.data || {};

    // --------------------------------------------------------
    // Global health
    // --------------------------------------------------------

    const globalHealth = document.getElementById("global-health");
    const healthDot = document.getElementById("global-health-dot");
    const healthBadge = document.getElementById("linux-health-badge");

    const status =
      (health.status || "unknown").toLowerCase();

    const statusText =
      status.toUpperCase();

    if (globalHealth) {
      globalHealth.textContent = statusText;
    }

    if (healthBadge) {
      healthBadge.textContent = statusText;
      healthBadge.className =
        `health-badge health-${status}`;
    }

    if (healthDot) {
      healthDot.className =
        `health-dot health-${status}`;
    }


    // --------------------------------------------------------
    // System information
    // --------------------------------------------------------

    const system = data.system || {};

    setText("linux-hostname", system.hostname);
    setText(
      "linux-os",
      system.os_name ||
      system.distribution ||
      system.platform ||
      "--"
    );

    setText(
      "linux-kernel",
      system.kernel ||
      system.platform_release ||
      "--"
    );

    setText(
      "linux-arch",
      system.architecture ||
      "--"
    );

    setText(
      "linux-cpu-cores",
      system.cpu_count ||
      system.cpu_cores ||
      "--"
    );

    setText(
      "linux-uptime",
      formatUptime(
        system.uptime_seconds ||
        system.uptime
      )
    );


    // --------------------------------------------------------
    // CPU
    // --------------------------------------------------------

    const cpu = data.cpu || {};

    const cpuPercent =
      numberValue(
        cpu.usage_percent,
        cpu.cpu_percent
      );

    setPercent("m-cpu", cpuPercent);
    setProgress("cpu-progress", cpuPercent);

    setText(
      "cpu-detail",
      cpuPercent !== null
        ? `${cpuPercent.toFixed(1)}% utilization`
        : "--"
    );


    // --------------------------------------------------------
    // Memory
    // --------------------------------------------------------

    const memory = data.memory || {};

    const memoryPercent =
      numberValue(
        memory.usage_percent,
        memory.percent
      );

    setPercent("m-mem", memoryPercent);
    setProgress("memory-progress", memoryPercent);

    setText(
      "memory-detail",
      formatMemoryDetail(memory)
    );


    // --------------------------------------------------------
    // Swap
    // --------------------------------------------------------

    const swap = data.swap || {};

    const swapPercent =
      numberValue(
        swap.usage_percent,
        swap.percent
      );

    setPercent("m-swap", swapPercent);
    setProgress("swap-progress", swapPercent);

    setText(
      "swap-detail",
      formatMemoryDetail(swap)
    );


    // --------------------------------------------------------
    // Disk
    // --------------------------------------------------------

    const disk = data.disk || {};

    let rootDisk = disk["/"];

    if (!rootDisk) {

      const entries =
        Object.entries(disk);

      if (entries.length) {
        rootDisk = entries[0][1];
      }

    }

    const diskPercent =
      rootDisk
        ? numberValue(
          rootDisk.usage_percent,
          rootDisk.percent
        )
        : null;

    setPercent("m-disk", diskPercent);
    setProgress("disk-progress", diskPercent);

    setText(
      "disk-detail",
      rootDisk
        ? formatDiskDetail(rootDisk)
        : "--"
    );


    // --------------------------------------------------------
    // Load
    // --------------------------------------------------------

    const load = data.load || {};

    const load1 =
      numberValue(
        load.load_1,
        load.load_avg_1
      );

    const load5 =
      numberValue(
        load.load_5,
        load.load_avg_5
      );

    const load15 =
      numberValue(
        load.load_15,
        load.load_avg_15
      );

    setText(
      "m-load",
      load1 !== null
        ? load1.toFixed(2)
        : "--"
    );

    setText(
      "load-detail",
      `${formatNumber(load1)} / ${formatNumber(load5)} / ${formatNumber(load15)}`
    );


    // --------------------------------------------------------
    // Inodes
    // --------------------------------------------------------

    const inodes = data.inodes || {};

    const inodePercent =
      findHighestPercentage(inodes);

    setPercent(
      "m-inodes",
      inodePercent
    );


    // --------------------------------------------------------
    // Processes
    // --------------------------------------------------------

    renderLinuxProcesses(
      data.top_processes,
      data.process_summary
    );


    // --------------------------------------------------------
    // Services
    // --------------------------------------------------------

    renderLinuxServices(
      data.failed_services
    );


    // --------------------------------------------------------
    // Network
    // --------------------------------------------------------

    renderLinuxNetwork(
      data.network_interfaces,
      data.network_stats,
      data.listening_ports
    );


    // --------------------------------------------------------
    // Security
    // --------------------------------------------------------

    renderLinuxSecurity(
      data.selinux,
      data.firewall,
      data.failed_logins,
      data.logged_in_users
    );


    // --------------------------------------------------------
    // Events
    // --------------------------------------------------------

    renderLinuxEvents(
      data.journal_errors,
      data.failed_logins
    );


    // --------------------------------------------------------
    // Health summary
    // --------------------------------------------------------

    renderHealthSummary(health);

  } catch (err) {

    console.error(
      "Linux health request failed:",
      err
    );

    const globalHealth =
      document.getElementById("global-health");

    if (globalHealth) {
      globalHealth.textContent =
        "API ERROR";
    }

  }

}


// ============================================================
// Helper functions
// ============================================================

function setText(id, value) {

  const element =
    document.getElementById(id);

  if (!element) {
    return;
  }

  if (
    value === undefined ||
    value === null ||
    value === ""
  ) {
    element.textContent = "--";
  } else {
    element.textContent = value;
  }

}


function numberValue(...values) {

  for (const value of values) {

    if (
      value !== undefined &&
      value !== null &&
      !Number.isNaN(Number(value))
    ) {
      return Number(value);
    }

  }

  return null;

}


function setPercent(id, value) {

  if (value === null) {

    setText(id, "--");

    return;
  }

  setText(
    id,
    `${value.toFixed(1)}%`
  );

}


function setProgress(id, value) {

  const element =
    document.getElementById(id);

  if (!element) {
    return;
  }

  if (value === null) {

    element.style.width = "0%";

    return;
  }

  const safeValue =
    Math.max(
      0,
      Math.min(100, value)
    );

  element.style.width =
    `${safeValue}%`;

}


function formatNumber(value) {

  if (value === null) {
    return "--";
  }

  return Number(value).toFixed(2);

}


function formatUptime(value) {

  if (
    value === undefined ||
    value === null
  ) {
    return "--";
  }

  if (
    typeof value === "string" &&
    value.includes(" ")
  ) {
    return value;
  }

  const seconds =
    Number(value);

  if (Number.isNaN(seconds)) {
    return value;
  }

  const days =
    Math.floor(seconds / 86400);

  const hours =
    Math.floor(
      (seconds % 86400) / 3600
    );

  const minutes =
    Math.floor(
      (seconds % 3600) / 60
    );

  return `${days}d ${hours}h ${minutes}m`;

}


function formatMemoryDetail(data) {

  if (!data) {
    return "--";
  }

  const used =
    data.used_gb ??
    data.used_mb;

  const total =
    data.total_gb ??
    data.total_mb;

  if (
    used !== undefined &&
    total !== undefined
  ) {

    const unit =
      data.used_gb !== undefined
        ? "GB"
        : "MB";

    return `${used} / ${total} ${unit}`;

  }

  return "--";

}


function formatDiskDetail(data) {

  if (!data) {
    return "--";
  }

  const used =
    data.used_gb ??
    data.used;

  const total =
    data.total_gb ??
    data.total;

  if (
    used !== undefined &&
    total !== undefined
  ) {

    return `${used} / ${total} GB`;

  }

  return "--";

}


function findHighestPercentage(data) {

  if (!data) {
    return null;
  }

  let highest = null;

  function inspect(value) {

    if (!value) {
      return;
    }

    if (
      typeof value === "object"
    ) {

      for (
        const [key, child] of Object.entries(value)
      ) {

        if (
          typeof child === "number" &&
          (
            key === "percent" ||
            key === "usage_percent" ||
            key === "percent_used"
          )
        ) {

          highest =
            highest === null
              ? child
              : Math.max(
                highest,
                child
              );

        } else if (
          typeof child === "object"
        ) {

          inspect(child);

        }

      }

    }

  }

  inspect(data);

  return highest;

}


// ============================================================
// Process UI
// ============================================================

function renderLinuxProcesses(
  processData,
  summary
) {

  const summaryData =
    summary || {};

  setText(
    "process-total",
    summaryData.total_processes ??
    summaryData.process_count ??
    "--"
  );

  setText(
    "process-running",
    summaryData.running ??
    summaryData.running_processes ??
    "--"
  );

  setText(
    "process-sleeping",
    summaryData.sleeping ??
    summaryData.sleeping_processes ??
    "--"
  );

  setText(
    "process-zombies",
    summaryData.zombie ??
    summaryData.zombies ??
    "--"
  );


  const processes =
    extractList(processData);

  if (!processes.length) {

    setHTML(
      "dashboard-processes",
      `<div class="empty-state">
        No process information available.
       </div>`
    );

    setHTML(
      "process-table",
      `<div class="empty-state">
        No process information available.
       </div>`
    );

    return;
  }


  const rows =
    processes
      .slice(0, 15)
      .map(p => {

        const pid =
          p.pid ?? "--";

        const name =
          p.name ??
          p.command ??
          "--";

        const user =
          p.username ??
          p.user ??
          "--";

        const cpu =
          p.cpu_percent ??
          p.cpu ??
          0;

        const memory =
          p.memory_percent ??
          p.mem_percent ??
          0;

        const status =
          p.status ??
          "--";

        return `
          <tr>
            <td>${escapeHTML(pid)}</td>
            <td><strong>${escapeHTML(name)}</strong></td>
            <td>${escapeHTML(user)}</td>
            <td>${formatNumber(Number(cpu))}%</td>
            <td>${formatNumber(Number(memory))}%</td>
            <td>${escapeHTML(status)}</td>
          </tr>
        `;

      })
      .join("");


  setHTML(
    "process-table",
    `
      <div class="table-scroll">

        <table>

          <thead>

            <tr>
              <th>PID</th>
              <th>Process</th>
              <th>User</th>
              <th>CPU</th>
              <th>Memory</th>
              <th>Status</th>
            </tr>

          </thead>

          <tbody>
            ${rows}
          </tbody>

        </table>

      </div>
    `
  );


  setHTML(
    "dashboard-processes",
    `
      <div class="mini-table">

        ${processes
      .slice(0, 5)
      .map(p => `
            <div class="mini-row">

              <strong>
                ${escapeHTML(
        p.name ??
        p.command ??
        "--"
      )}
              </strong>

              <span>
                ${formatNumber(
        Number(
          p.cpu_percent ??
          p.cpu ??
          0
        )
      )}%
              </span>

            </div>
          `)
      .join("")}

      </div>
    `
  );

}


// ============================================================
// Services
// ============================================================

function renderLinuxServices(data) {

  let services =
    extractList(data);

  setText(
    "service-count",
    `${services.length} failed`
  );

  if (!services.length) {

    const html =
      `<div class="success-state">
        ✓ No failed systemd services
       </div>`;

    setHTML(
      "services-table",
      html
    );

    setHTML(
      "dashboard-services",
      html
    );

    return;
  }


  const rows =
    services
      .slice(0, 30)
      .map(service => {

        const name =
          typeof service === "string"
            ? service
            : service.name ??
            service.service ??
            "--";

        return `
          <div class="service-row">

            <strong>
              ${escapeHTML(name)}
            </strong>

            <span class="severity-badge sev-critical">
              FAILED
            </span>

          </div>
        `;

      })
      .join("");


  setHTML(
    "services-table",
    rows
  );

  setHTML(
    "dashboard-services",
    services
      .slice(0, 5)
      .map(service => {

        const name =
          typeof service === "string"
            ? service
            : service.name ??
            service.service ??
            "--";

        return `
          <div class="service-row">

            <strong>
              ${escapeHTML(name)}
            </strong>

            <span class="severity-badge sev-critical">
              FAILED
            </span>

          </div>
        `;

      })
      .join("")
  );

}


// ============================================================
// Network
// ============================================================

function renderLinuxNetwork(
  interfaces,
  stats,
  ports
) {

  const interfaceList =
    extractList(interfaces);

  if (!interfaceList.length) {

    setHTML(
      "network-interfaces",
      `<div class="empty-state">
        No network interface data available.
       </div>`
    );

  } else {

    setHTML(
      "network-interfaces",
      `
        <div class="table-scroll">

          <table>

            <thead>

              <tr>
                <th>Interface</th>
                <th>State</th>
                <th>Address</th>
                <th>RX</th>
                <th>TX</th>
              </tr>

            </thead>

            <tbody>

              ${interfaceList
        .map(item => {

          const name =
            item.name ??
            item.interface ??
            item.iface ??
            "--";

          const state =
            item.state ??
            item.status ??
            "--";

          const address =
            item.address ??
            item.ip ??
            item.ip_address ??
            "--";

          return `
                    <tr>
                      <td>
                        <strong>
                          ${escapeHTML(name)}
                        </strong>
                      </td>

                      <td>
                        ${escapeHTML(state)}
                      </td>

                      <td>
                        ${escapeHTML(address)}
                      </td>

                      <td>
                        ${escapeHTML(
            item.rx_bytes ??
            item.rx ??
            "--"
          )}
                      </td>

                      <td>
                        ${escapeHTML(
            item.tx_bytes ??
            item.tx ??
            "--"
          )}
                      </td>
                    </tr>
                  `;

        })
        .join("")}

            </tbody>

          </table>

        </div>
      `
    );

  }


  const statsList =
    extractList(stats);

  if (!statsList.length) {

    setHTML(
      "network-stats",
      `<div class="empty-state">
        No network statistics available.
       </div>`
    );

  } else {

    setHTML(
      "network-stats",
      statsList
        .slice(0, 10)
        .map(item => {

          const name =
            item.name ??
            item.interface ??
            item.iface ??
            "--";

          return `
            <div class="network-stat-row">

              <strong>
                ${escapeHTML(name)}
              </strong>

              <span>
                RX:
                ${escapeHTML(
            item.rx_bytes ??
            "--"
          )}
              </span>

              <span>
                TX:
                ${escapeHTML(
            item.tx_bytes ??
            "--"
          )}
              </span>

            </div>
          `;

        })
        .join("")
    );

  }


  const portList =
    extractList(ports);

  if (!portList.length) {

    setHTML(
      "listening-ports",
      `<div class="empty-state">
        No listening ports found.
       </div>`
    );

  } else {

    setHTML(
      "listening-ports",
      `
        <div class="table-scroll">

          <table>

            <thead>
              <tr>
                <th>Protocol</th>
                <th>Address</th>
                <th>Port</th>
                <th>Process</th>
              </tr>
            </thead>

            <tbody>

              ${portList
        .slice(0, 50)
        .map(item => {

          return `
                    <tr>

                      <td>
                        ${escapeHTML(
            item.protocol ??
            item.proto ??
            "--"
          )}
                      </td>

                      <td>
                        ${escapeHTML(
            item.address ??
            item.local_address ??
            "--"
          )}
                      </td>

                      <td>
                        <strong>
                          ${escapeHTML(
            item.port ??
            "--"
          )}
                        </strong>
                      </td>

                      <td>
                        ${escapeHTML(
            item.process ??
            item.process_name ??
            "--"
          )}
                      </td>

                    </tr>
                  `;

        })
        .join("")}

            </tbody>

          </table>

        </div>
      `
    );

  }

}


// ============================================================
// Security
// ============================================================

function renderLinuxSecurity(
  selinux,
  firewall,
  failedLogins,
  users
) {

  const selinuxStatus =
    selinux?.status ??
    selinux?.mode ??
    (selinux?.enforcing
      ? "Enforcing"
      : "Permissive");

  const firewallStatus =
    firewall?.active === true
      ? "Active"
      : firewall?.active === false
        ? "Inactive"
        : firewall?.status ??
        "Unknown";

  const loginList =
    extractList(failedLogins);

  const userList =
    extractList(users);


  setText(
    "summary-selinux",
    selinuxStatus
  );

  setText(
    "summary-firewall",
    firewallStatus
  );

  setText(
    "summary-services",
    document.getElementById(
      "service-count"
    )?.textContent || "--"
  );

  setText(
    "summary-logins",
    loginList.length
  );


  setText(
    "detail-selinux",
    selinuxStatus
  );

  setText(
    "detail-firewall",
    firewallStatus
  );

  setText(
    "detail-failed-logins",
    loginList.length
  );

  setText(
    "detail-users",
    userList.length
  );

}


// ============================================================
// Events
// ============================================================

function renderLinuxEvents(
  journal,
  failedLogins
) {

  const journalList =
    extractList(journal);

  if (!journalList.length) {

    setHTML(
      "journal-events",
      `<div class="success-state">
        ✓ No recent journal errors reported
       </div>`
    );

  } else {

    setHTML(
      "journal-events",
      journalList
        .slice(0, 30)
        .map(item => {

          const text =
            typeof item === "string"
              ? item
              : item.message ??
              item.msg ??
              JSON.stringify(item);

          return `
            <div class="event-row">

              <span class="event-type">
                ERROR
              </span>

              <span>
                ${escapeHTML(text)}
              </span>

            </div>
          `;

        })
        .join("")
    );

  }


  const loginList =
    extractList(failedLogins);

  if (!loginList.length) {

    setHTML(
      "login-events",
      `<div class="success-state">
        ✓ No failed login events reported
       </div>`
    );

  } else {

    setHTML(
      "login-events",
      loginList
        .slice(0, 30)
        .map(item => {

          const text =
            typeof item === "string"
              ? item
              : item.message ??
              item.user ??
              JSON.stringify(item);

          return `
            <div class="event-row">

              <span class="event-type warning">
                AUTH
              </span>

              <span>
                ${escapeHTML(text)}
              </span>

            </div>
          `;

        })
        .join("")
    );

  }

}


// ============================================================
// Health Summary
// ============================================================

function renderHealthSummary(health) {

  const critical =
    health.critical || [];

  const warnings =
    health.warnings || [];

  let html = "";

  if (!critical.length && !warnings.length) {

    html = `
      <div class="success-state">
        ✓ Linux server is healthy
      </div>
    `;

  } else {

    critical.forEach(item => {

      html += `
        <div class="health-event critical">

          <span class="severity-badge sev-critical">
            CRITICAL
          </span>

          <span>
            ${escapeHTML(
        item.message || ""
      )}
          </span>

        </div>
      `;

    });


    warnings.forEach(item => {

      html += `
        <div class="health-event warning">

          <span class="severity-badge sev-warning">
            WARNING
          </span>

          <span>
            ${escapeHTML(
        item.message || ""
      )}
          </span>

        </div>
      `;

    });

  }

  setHTML(
    "health-summary",
    html
  );

}


// ============================================================
// Utility
// ============================================================

function extractList(data) {

  if (!data) {
    return [];
  }

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data.items)) {
    return data.items;
  }

  if (Array.isArray(data.processes)) {
    return data.processes;
  }

  if (Array.isArray(data.services)) {
    return data.services;
  }

  if (Array.isArray(data.ports)) {
    return data.ports;
  }

  if (Array.isArray(data.interfaces)) {
    return data.interfaces;
  }

  if (Array.isArray(data.events)) {
    return data.events;
  }

  return [];

}


function setHTML(id, html) {

  const element =
    document.getElementById(id);

  if (element) {
    element.innerHTML = html;
  }

}


function escapeHTML(value) {

  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

}


// ============================================================
// Navigation helper
// ============================================================

function switchTab(tabName) {

  document
    .querySelectorAll(".tab-btn")
    .forEach(btn => {

      btn.classList.toggle(
        "active",
        btn.dataset.tab === tabName
      );

    });


  document
    .querySelectorAll(".tab-panel")
    .forEach(panel => {

      panel.classList.toggle(
        "active",
        panel.id === `tab-${tabName}`
      );

    });

}


// ============================================================
// Replace existing tab handling with shared helper
// ============================================================

document
  .querySelectorAll(".tab-btn")
  .forEach(btn => {

    btn.addEventListener(
      "click",
      () => {

        switchTab(
          btn.dataset.tab
        );

      }
    );

  });


// ============================================================
// Initial Linux health load
// ============================================================

loadLinuxHealth();


// Refresh live Linux health every 15 seconds

setInterval(
  loadLinuxHealth,
  15000
);