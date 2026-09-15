/* DBA AI Agent — lightweight enterprise dashboard frontend */
"use strict";

const API = "/api";
let trendChart = null;
let metricsChart = null;
let activeRange = "24h";
const cache = {};

const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>'"]/g, c => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;"
}[c]));

function on(id, event, handler) {
  const el = $(id);
  if (el) el.addEventListener(event, handler);
  return el;
}

function toast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

const search = $("global-search");
document.addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); search.focus(); } });
on("global-search", "keydown", e => { if (e.key !== "Enter") return; const q = e.target.value.trim().toLowerCase(); if (!q) return; const match = ["oracle", "linux", "oscap", "security", "compliance", "vapt", "network", "process", "service", "report", "metric", "event", "log", "ai"].find(x => q.includes(x)); navigate(match === "ai" ? "ai" : match || "dashboard"); });

function setRing(id, value) { const el = $(id); if (!el) return; const v = Math.max(0, Math.min(100, Number(value) || 0)); el.style.background = `conic-gradient(var(--blue) ${v * 3.6}deg,#e8eef5 0deg)`; el.querySelector("span").textContent = `${v.toFixed(0)}%`; }
function fmtUptime(sec) { sec = Number(sec) || 0; const d = Math.floor(sec / 86400); sec %= 86400; const h = Math.floor(sec / 3600); sec %= 3600; const m = Math.floor(sec / 60); return `${d}d ${h}h ${m}m`; }
function statusClass(s) { return String(s || "").toLowerCase().includes("critical") ? "critical" : String(s || "").toLowerCase().includes("warn") ? "warning" : "ok"; }
function healthItem(status, message) { const cls = statusClass(status); const icon = cls === "critical" ? "!" : cls === "warning" ? "!" : "✓"; return `<div class="health-item ${cls}"><b>${icon}</b><span>${esc(message)}</span></div>`; }

async function getJSON(path, options = {}) { const res = await fetch(API + path, options); let data = {}; try { data = await res.json() } catch { } if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`); return data; }

async function loadLatest() { try { const data = await getJSON("/metrics/latest"); if (!data.ok) return; const s = data.sample || {}; const cpu = Number(s.cpu_percent) || 0, mem = Number(s.mem_percent) || 0, swap = Number(s.swap_percent) || 0, disk = Number(s.disk?.["/"]?.percent) || 0; $("m-cpu").textContent = cpu.toFixed(1) + "%"; $("m-mem").textContent = mem.toFixed(1) + "%"; $("m-disk").textContent = disk.toFixed(1) + "%"; setRing("cpu-ring", cpu); setRing("mem-ring", mem); setRing("disk-ring", disk); $("cpu-detail").textContent = `${s.cpu_cores_logical || "--"} logical cores`; $("mem-detail").textContent = s.mem_total_gb ? `${s.mem_total_gb.toFixed(1)} GB total` : `${mem.toFixed(1)}% used`; $("disk-detail").textContent = "Persistent root filesystem"; cache.latest = s; return s } catch (e) { return null } }

function chartOptions() { return { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: "index", intersect: false }, plugins: { legend: { display: false }, tooltip: { padding: 10, displayColors: true } }, scales: { x: { grid: { color: "rgba(120,140,165,.10)" }, ticks: { maxTicksLimit: 9, color: "#7c8ca1", font: { size: 9 } } }, y: { beginAtZero: true, max: 100, grid: { color: "rgba(120,140,165,.13)" }, ticks: { color: "#7c8ca1", font: { size: 9 }, callback: v => v + "%" } } } } }
function buildTrend(labels, cpu, mem, swap) { const ctx = $("trend-chart"); if (!ctx) return; const datasets = [{ label: "CPU", data: cpu, borderColor: "#1769e0", backgroundColor: "rgba(23,105,224,.10)", fill: true, tension: .35, pointRadius: 0, borderWidth: 2 }, { label: "Memory", data: mem, borderColor: "#16a46a", backgroundColor: "rgba(22,164,106,.07)", fill: true, tension: .35, pointRadius: 0, borderWidth: 2 }, { label: "Swap", data: swap, borderColor: "#df3c4f", backgroundColor: "rgba(223,60,79,.04)", fill: true, tension: .35, pointRadius: 0, borderWidth: 1.5 }]; if (trendChart) { trendChart.data.labels = labels; trendChart.data.datasets = datasets; trendChart.update("none"); return } trendChart = new Chart(ctx, { type: "line", data: { labels, datasets }, options: chartOptions() }); }

async function loadHistory() { try { const limit = activeRange === "7d" ? 500 : activeRange === "6h" ? 180 : activeRange === "1h" ? 60 : 300; const data = await getJSON(`/metrics/history?limit=${limit}`); if (!data.ok || !data.samples?.length) return; const samples = data.samples; const labels = samples.map(s => new Date(s.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })); buildTrend(labels, samples.map(s => Number(s.cpu_percent) || 0), samples.map(s => Number(s.mem_percent) || 0), samples.map(s => Number(s.swap_percent) || 0)); if (metricsChart) buildMetricsChart(samples); else if ($("metrics-chart")?.closest(".tab-panel")?.classList.contains("active")) buildMetricsChart(samples); cache.history = samples } catch (e) { console.debug(e) } }

function buildMetricsChart(samples) { const ctx = $("metrics-chart"); if (!ctx) return; const labels = samples.map(s => new Date(s.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })); const datasets = [{ label: "CPU", data: samples.map(s => +s.cpu_percent || 0), borderColor: "#1769e0", backgroundColor: "rgba(23,105,224,.09)", fill: true, tension: .3, pointRadius: 0, borderWidth: 2 }, { label: "Memory", data: samples.map(s => +s.mem_percent || 0), borderColor: "#16a46a", backgroundColor: "rgba(22,164,106,.06)", fill: true, tension: .3, pointRadius: 0, borderWidth: 2 }]; if (metricsChart) { metricsChart.data.labels = labels; metricsChart.data.datasets = datasets; metricsChart.update("none"); return } metricsChart = new Chart(ctx, { type: "line", data: { labels, datasets }, options: chartOptions() }); }
on("range-tabs", "click", e => { const b = e.target.closest("button"); if (!b) return; activeRange = b.dataset.range; document.querySelectorAll("#range-tabs button").forEach(x => x.classList.toggle("active", x === b)); loadHistory(); });

async function loadHealth() { try { const d = await getJSON("/linux/health"); const h = d.health || {}; $("health-summary").innerHTML = [...(h.critical || []).map(x => healthItem("critical", x.message || x)), ...(h.warnings || []).map(x => healthItem("warning", x.message || x)), ...(h.critical?.length || h.warnings?.length ? [] : [healthItem("ok", "Linux health checks are currently clear")])].slice(0, 5).join(""); const status = h.status || "unknown"; $("global-status").textContent = status === "critical" ? "Critical" : status === "warning" ? "Attention" : "Operational"; const cls = statusClass(status); $("global-status").style.color = cls === "critical" ? "var(--red)" : cls === "warning" ? "var(--amber)" : "var(--green)"; $("m-alerts").textContent = (h.critical_count || 0) + (h.warning_count || 0); $("alert-detail").textContent = `${h.critical_count || 0} critical · ${h.warning_count || 0} warning`; const s = d.data?.system || {}; $("m-uptime").textContent = s.uptime_human || fmtUptime(s.uptime_seconds); $("uptime-detail").textContent = s.hostname || "System availability"; cache.linux = d; renderLinux(d); return d } catch (e) { $("health-summary").innerHTML = healthItem("critical", e.message); } }
function renderLinux(d) { const x = d.data || {}, s = x.system || {}, c = x.cpu || {}, m = x.memory || {}, sw = x.swap || {}, disk = (x.disk?.filesystems || []).find(f => f.mountpoint === "/") || {}; $("linux-health-body").innerHTML = `<div class="data-card"><span>CPU</span><b>${(c.usage_percent ?? 0).toFixed(1)}%</b></div><div class="data-card"><span>Memory</span><b>${(m.usage_percent ?? 0).toFixed(1)}%</b></div><div class="data-card"><span>Swap</span><b>${(sw.usage_percent ?? 0).toFixed(1)}%</b></div><div class="data-card"><span>Root disk</span><b>${(disk.percent ?? 0).toFixed(1)}%</b></div><div class="data-card"><span>Load 1m</span><b>${c.load_1m ?? x.load?.load_1m ?? "--"}</b></div><div class="data-card"><span>SELinux</span><b>${esc(x.selinux?.mode || x.selinux?.status || "--")}</b></div>`; $("linux-system-info").innerHTML = `<div class="kv-list">${[["Hostname", s.hostname], ["Operating system", `${s.distribution || "Linux"} ${s.distribution_version || ""}`], ["Kernel", s.kernel], ["Architecture", s.architecture], ["CPU cores", `${s.cpu_cores_physical || "--"} physical / ${s.cpu_cores_logical || "--"} logical`], ["Uptime", s.uptime_human]].map(r => `<div class="kv"><span>${r[0]}</span><b>${esc(r[1] || "--")}</b></div>`).join("")}</div>`; }

async function loadOracle() { try { const d = await getJSON("/oracle/health"); cache.oracle = d; const h = d.health || {}, data = d.data || {}; const db = data.database || {}, inst = data.instance || {}, conn = data.connection || {}; $("oracle-health-body").innerHTML = `<div class="data-card"><span>Status</span><b>${esc(h.status || "unknown").toUpperCase()}</b></div><div class="data-card"><span>Database</span><b>${esc(db.db_name || db.name || "--")}</b></div><div class="data-card"><span>Instance</span><b>${esc(inst.instance_name || "--")}</b></div><div class="data-card"><span>Connection</span><b>${conn.connected === true ? "Connected" : "Unavailable"}</b></div><div class="data-card"><span>Critical</span><b>${h.critical_count || 0}</b></div><div class="data-card"><span>Warnings</span><b>${h.warning_count || 0}</b></div>`; $("oracle-summary").innerHTML = `<div class="kv-list">${[["Database", db.db_name || "--"], ["Open mode", db.open_mode || "--"], ["Instance", inst.instance_name || "--"], ["Instance status", inst.status || "--"], ["Service", conn.service_name || "--"], ["PDBs", (data.pdbs || []).length || "--"]].map(r => `<div class="kv"><span>${r[0]}</span><b>${esc(r[1])}</b></div>`).join("")}</div>`; return d } catch (e) { $("oracle-health-body").innerHTML = `<div class="error">${esc(e.message)}</div>`; } }

async function loadOSCAP() { try { const d = await getJSON("/security/content"); cache.oscap = d; $("oscap-content").innerHTML = `<div class="kv-list">${Object.entries(d.content || d || {}).slice(0, 12).map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><b>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</b></div>`).join("")}</div>`; if (!Object.keys(d.content || d || {}).length) $("oscap-content").innerHTML = `<div class="empty-state"><b>Configured content unavailable</b><p>Check the OpenSCAP configuration on the host.</p></div>`; loadCompliance(); } catch (e) { $("oscap-content").innerHTML = `<div class="error">${esc(e.message)}</div>`; } }
async function loadCompliance() { try { const d = await getJSON("/security/findings"); const items = d.findings || d.items || []; $("compliance-body").innerHTML = items.length ? items.slice(0, 60).map(f => `<div class="finding"><strong>${esc(f.rule_id || f.rule || f.title || "Finding")}</strong><small>${esc(f.title || f.message || f.severity || "")}</small></div>`).join("") : `<div class="empty-state"><b>No stored findings</b><p>Run an OpenSCAP assessment to populate compliance evidence.</p></div>`; cache.findings = d; } catch (e) { $("compliance-body").innerHTML = `<div class="error">${esc(e.message)}</div>`; } }

function renderSecurity() { const h = cache.linux?.health || {}; const items = [...(h.critical || []).map(x => ["critical", x.message]), ...(h.warnings || []).map(x => ["warning", x.message])]; $("security-posture").innerHTML = items.length ? items.map(x => healthItem(x[0], x[1])).join("") : `${healthItem("ok", "No Linux health warnings currently reported")}`; }

async function runScan() { const btn = $("scan-btn"); btn.disabled = true; $("scan-body").innerHTML = `<div class="loading"></div>`; try { const d = await getJSON("/security/scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }); if (!d.ok) throw new Error(d.error || "Unable to start scan"); pollScan(d.scan_id); } catch (e) { $("scan-body").innerHTML = `<div class="error">${esc(e.message)}</div>` } finally { btn.disabled = false } }
on("scan-btn", "click", runScan);
async function pollScan(id) { let tries = 0; const timer = setInterval(async () => { tries++; try { const d = await getJSON(`/security/scan/${encodeURIComponent(id)}`); renderScan(d); if (d.status === "done" || d.status === "error" || tries > 180) clearInterval(timer) } catch (e) { clearInterval(timer); $("scan-body").innerHTML = `<div class="error">${esc(e.message)}</div>` } }, 3000) }
function renderScan(d) { const s = d.summary || {}, p = d.parsed || {}, c = p.counts || {}; let html = `<div class="scan-summary"><div class="data-card"><span>Overall risk</span><b>${esc((s.overall_risk || d.status || "unknown").toUpperCase())}</b></div><div class="data-card"><span>Rules checked</span><b>${p.total_rules_checked || 0}</b></div><div class="data-card"><span>Status</span><b>${esc(d.status || "--")}</b></div></div><p class="muted">${esc(s.summary || "")}</p>`; if (Object.keys(c).length) html += `<div class="kv-list">${Object.entries(c).map(([k, v]) => `<div class="kv"><span>${esc(k)}</span><b>${v}</b></div>`).join("")}</div>`; if (s.priorities?.length) html += `<h3 style="font-size:12px;margin:16px 0 7px">Priorities</h3>${s.priorities.slice(0, 10).map(x => `<div class="finding"><strong>${esc(x.rule_id || x.title)}</strong><small>${esc(x.why_it_matters || x.title || "")}</small></div>`).join("")}`; if (d.report_html_path) html += `<p><a href="/api/security/report/${encodeURIComponent(d.scan_id || d._scan_id || "")}" target="_blank">View full HTML report</a></p>`; $("scan-body").innerHTML = html; }

async function loadSystemHealth() { try { const d = await getJSON("/system/health"); cache.system = d; $("system-health-body").innerHTML = `<div class="data-card"><span>Overall</span><b>${esc(d.health?.status || d.status || "unknown").toUpperCase()}</b></div><div class="data-card"><span>Critical</span><b>${d.health?.critical_count ?? d.critical_count ?? 0}</b></div><div class="data-card"><span>Warnings</span><b>${d.health?.warning_count ?? d.warning_count ?? 0}</b></div><div class="data-card"><span>Linux</span><b>${esc(cache.linux?.health?.status || "--")}</b></div><div class="data-card"><span>Oracle</span><b>${esc(cache.oracle?.health?.status || "--")}</b></div>`; renderSecurity(); return d } catch (e) { $("system-health-body").innerHTML = `<div class="error">${esc(e.message)}</div>`; } }

const PAGE_META = {
  dashboard: ["Operations dashboard", "Linux operations · Oracle DBA · Security · All in one platform"],
  ai: ["AI Operations Assistant", "Domain-routed local AI using Ollama and Llama 3.2:3b"],
  linux: ["Linux health", "Host-level deterministic health checks"],
  oracle: ["Oracle Database", "Oracle 19c read-only health telemetry"],
  oscap: ["OpenSCAP", "Compliance assessment and findings"],
  network: ["Network", "Interfaces, traffic, and listening ports"],
  health: ["System health center", "Linux + Oracle + security health in one view"],
  metrics: ["Metrics & trends", "Historical resource telemetry collected by the agent"],
  events: ["Events & logs", "Operational events available from current APIs"],
  security: ["Security posture", "Current security controls and warnings"],
  vapt: ["VAPT analysis", "Security testing workspace"],
  compliance: ["Compliance center", "OpenSCAP findings and rule history"],
  tools: ["Tool registry", "Explicit deterministic tools available to the platform"],
  processes: ["Processes", "Read-only process visibility"],
  services: ["Services", "Service inventory and controlled actions"],
  reports: ["Reports", "Analysis and security report history"],
  settings: ["Platform settings", "Current runtime configuration"],
  about: ["About", "DataPatro Technologies DBA AI Agent"]
};

function navigate(tab) {
  if (!PAGE_META[tab]) {
    tab = "dashboard";
  }

  document.querySelectorAll(".tab-panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === `tab-${tab}`);
  });

  document.querySelectorAll("[data-tab]").forEach(button => {
    button.classList.toggle(
      "active",
      button.dataset.tab === tab && button.classList.contains("nav-item")
    );
  });

  const meta = PAGE_META[tab];
  const title = document.getElementById("page-title");
  const subtitle = document.getElementById("page-subtitle");

  if (title) {
    title.textContent = meta[0];
  }

  if (subtitle) {
    subtitle.textContent = meta[1];
  }

  loadTab(tab);

  const sidebar = document.getElementById("sidebar");
  if (sidebar) {
    sidebar.classList.remove("open");
  }
}

async function loadEvents() { try { const d = await getJSON("/reports"); const reports = d.reports || []; const rows = reports.slice(0, 12).map(r => `<tr><td>${esc(new Date(r.ts).toLocaleString())}</td><td>${esc(r.issue || "Analysis")}</td><td><span class="severity ${esc(r.severity || "info")}">${esc((r.severity || "info").toUpperCase())}</span></td></tr>`).join(""); const html = rows ? `<table class="events-table"><thead><tr><th>Time</th><th>Event</th><th>Severity</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty-state"><b>No report events</b><p>Events will appear as the agent records operational analysis.</p></div>`; $("events-body").innerHTML = html; $("recent-events").innerHTML = html; cache.reports = d } catch (e) { $("events-body").innerHTML = `<div class="error">${esc(e.message)}</div>`; } }
async function loadReports() { try { const d = cache.reports || await getJSON("/reports"); const rows = (d.reports || []).map(r => `<tr><td>${esc(new Date(r.ts).toLocaleString())}</td><td>${esc(r.issue || "")}</td><td><span class="severity ${esc(r.severity || "info")}">${esc((r.severity || "info").toUpperCase())}</span></td></tr>`).join(""); $("reports-body").innerHTML = rows ? `<table class="data-table"><thead><tr><th>Time</th><th>Issue</th><th>Severity</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty-state"><b>No reports yet</b><p>Run an analysis to create the first report.</p></div>` } catch (e) { $("reports-body").innerHTML = `<div class="error">${esc(e.message)}</div>` } }

async function loadTools() { try { const d = await getJSON("/tools"); const tools = d.tools || []; $("tools-body").innerHTML = tools.length ? `<table class="tool-table"><thead><tr><th>Tool</th><th>Category</th><th>Access</th></tr></thead><tbody>${tools.map(t => `<tr><td><b>${esc(t.name || t.tool || "")}</b></td><td><span class="tool-category">${esc(t.category || "general")}</span></td><td>${t.read_only === false ? "Controlled" : "Read-only"}</td></tr>`).join("")}</tbody></table>` : `<div class="empty-state">No registered tools returned.</div>` } catch (e) { $("tools-body").innerHTML = `<div class="error">${esc(e.message)}</div>` } }

async function tool(name) { return getJSON(`/tools/${name}`) }
async function loadProcesses() { try { const d = await tool("linux.top_processes"); const rows = (d.data || d.processes || d.items || []).slice(0, 20).map((p, i) => `<tr><td>${i + 1}</td><td>${esc(p.name || p.command || "--")}</td><td>${p.cpu_percent ?? p.cpu ?? "--"}</td><td>${p.memory_percent ?? p.mem_percent ?? "--"}</td><td>${p.pid ?? "--"}</td></tr>`).join(""); $("processes-body").innerHTML = rows ? `<table class="data-table"><thead><tr><th>#</th><th>Process</th><th>CPU %</th><th>Memory %</th><th>PID</th></tr></thead><tbody>${rows}</tbody></table>` : `<div class="empty-state">No process data returned.</div>` } catch (e) { $("processes-body").innerHTML = `<div class="error">${esc(e.message)}</div>` } }
async function loadNetwork() { try { const [i, p] = await Promise.all([tool("linux.network_interfaces"), tool("linux.listening_ports")]); const ifaces = i.data || i.interfaces || []; const ports = p.data || p.ports || []; $("network-body").innerHTML = `<div class="section-grid two"><div><h3 style="font-size:12px">Interfaces</h3><table class="data-table"><thead><tr><th>Interface</th><th>Address</th><th>Status</th></tr></thead><tbody>${ifaces.slice(0, 20).map(x => `<tr><td>${esc(x.name || x.interface || "--")}</td><td>${esc(x.address || x.ip || "--")}</td><td>${esc(x.state || x.status || "--")}</td></tr>`).join("")}</tbody></table></div><div><h3 style="font-size:12px">Listening ports</h3><table class="data-table"><thead><tr><th>Address</th><th>Port</th><th>Process</th></tr></thead><tbody>${ports.slice(0, 30).map(x => `<tr><td>${esc(x.address || x.local_address || "--")}</td><td>${esc(x.port || x.local_port || "--")}</td><td>${esc(x.process || x.name || "--")}</td></tr>`).join("")}</tbody></table></div></div>` } catch (e) { $("network-body").innerHTML = `<div class="error">${esc(e.message)}</div>` } }
async function loadServices() { try { const d = await getJSON("/services"); const list = d.services || d.items || d || []; $("services-body").innerHTML = Array.isArray(list) && list.length ? `<table class="data-table"><thead><tr><th>Service</th><th>State</th></tr></thead><tbody>${list.map(s => `<tr><td>${esc(typeof s === "string" ? s : s.name || s.service || "--")}</td><td>${esc(typeof s === "string" ? "available" : s.state || s.status || "--")}</td></tr>`).join("")}</tbody></table>` : `<div class="empty-state"><b>No service inventory returned</b><p>Use the API service endpoint to query an individual service.</p></div>` } catch (e) { $("services-body").innerHTML = `<div class="error">${esc(e.message)}</div>` } }

function addMessage(role, text) { const d = document.createElement("div"); d.className = `msg msg-${role}`; d.textContent = text; $("chat-log").appendChild(d); $("chat-log").scrollTop = $("chat-log").scrollHeight; return d }
function setAIBusy(busy) {
  const badge = $("ai-status-badge");
  if (!badge) return;
  badge.textContent = busy ? "Busy" : "Online";
  badge.className = busy ? "badge neutral busy" : "badge neutral online";
  const input = $("chat-input");
  if (input) input.disabled = busy;
}

function renderToolSteps(toolCalls) {
  if (!toolCalls || !toolCalls.length) return null;
  const wrap = document.createElement("div");
  wrap.className = "tool-steps";
  wrap.innerHTML = toolCalls.map(t =>
    `<span class="tool-step">✓ ${esc(t.name)}</span>`
  ).join("");
  return wrap;
}

async function sendChat(text) {
  if (!text) return;
  addMessage("user", text);
  $("chat-input").value = "";
  const waiting = addMessage("assistant", "Thinking…");
  setAIBusy(true);
  try {
    const d = await getJSON("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });
    waiting.remove();
    if (d.ok) {
      const r = d.result || d;
      const msg = addMessage("assistant", r.reply || JSON.stringify(r, null, 2));
      const steps = renderToolSteps(r.tool_calls);
      if (steps) msg.appendChild(steps);
    } else {
      addMessage("assistant", d.error || d.result?.error || "AI request failed.");
    }
  } catch (e) {
    waiting.textContent = `AI request failed: ${e.message}`;
  } finally {
    setAIBusy(false);
  }
}
on("chat-form", "submit", e => { e.preventDefault(); sendChat($("chat-input").value.trim()) });
on("dashboard-ai-send", "click", () => sendChat($("dashboard-ai-input").value.trim()));
on("dashboard-ai-input", "keydown", e => { if (e.key === "Enter") sendChat(e.target.value.trim()) });
async function loadAIStatus() { try { await getJSON("/ai/status"); setAIBusy(false) } catch (e) { const badge = $("ai-status-badge"); if (badge) { badge.textContent = "Offline"; badge.className = "badge neutral offline" } } }

const loaders = { dashboard: async () => { await Promise.all([loadLatest(), loadHistory(), loadHealth(), loadEvents()]); }, ai: loadAIStatus, linux: loadHealth, oracle: loadOracle, oscap: loadOSCAP, security: async () => { if (!cache.linux) await loadHealth(); renderSecurity() }, compliance: loadCompliance, health: async () => { await Promise.all([loadHealth(), loadOracle()]); await loadSystemHealth() }, metrics: async () => { if (!cache.history) await loadHistory(); if (cache.history) buildMetricsChart(cache.history) }, events: loadEvents, tools: loadTools, processes: loadProcesses, network: loadNetwork, services: loadServices, reports: loadReports };
async function loadTab(tab) { try { if (loaders[tab]) await loaders[tab]() } catch (e) { console.debug(`tab ${tab}`, e) } }

on("refresh-linux", "click", loadHealth); on("refresh-oracle", "click", loadOracle); on("refresh-all", "click", async () => { await Promise.all([loadLatest(), loadHealth(), loadOracle(), loadSystemHealth()]); toast("Health refreshed") }); on("refresh-events", "click", loadEvents); on("refresh-processes", "click", loadProcesses); on("refresh-network", "click", loadNetwork); on("refresh-services", "click", loadServices);

function applyTheme(night) {
  document.body.classList.toggle("night", night);
  const button = $("theme-btn");
  if (!button) return;
  button.textContent = night ? "☼" : "☾";
  button.title = night ? "Switch to light mode" : "Switch to dark mode";
  button.setAttribute("aria-label", button.title);
}

const savedTheme = localStorage.getItem("os-agent-theme");
applyTheme(savedTheme ? savedTheme === "night" : document.body.classList.contains("night"));
on("theme-btn", "click", () => {
  const night = !document.body.classList.contains("night");
  applyTheme(night);
  localStorage.setItem("os-agent-theme", night ? "night" : "light");
});

loadTab("dashboard");
setInterval(loadLatest, 10000); setInterval(() => { if (document.querySelector("#tab-dashboard.active")) loadHistory() }, 30000); setInterval(() => { if (document.querySelector("#tab-dashboard.active")) loadHealth() }, 20000);


/* ============================================================
   GLOBAL NAVIGATION
   Handles sidebar, quick actions and navigation buttons.
============================================================ */

document.addEventListener("click", function (event) {

  const button = event.target.closest(
    "[data-tab], [data-page], .nav-item, .quick-action, .sidebar-link"
  );

  if (!button) {
    return;
  }

  /*
   * Do not interfere with normal buttons that already have
   * their own click handlers.
   */
  const tab =
    button.dataset.tab ||
    button.dataset.page ||
    button.getAttribute("data-target");

  if (!tab) {
    return;
  }

  event.preventDefault();
  event.stopPropagation();

  /*
   * Support both navigation functions used by the different
   * frontend sections.
   */
  if (typeof navigate === "function") {
    navigate(tab);
    return;
  }

  if (typeof showPage === "function") {
    showPage(tab);
    return;
  }

  console.warn("No navigation function available for:", tab);
});