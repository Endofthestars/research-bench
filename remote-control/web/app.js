const tokenInput = document.getElementById("token");
const projectSelect = document.getElementById("project-key");
const promptInput = document.getElementById("prompt");
const submitStatus = document.getElementById("submit-status");
const runsBody = document.getElementById("runs-body");
const detailSection = document.getElementById("detail");
const detailRunId = document.getElementById("detail-run-id");
const detailStatus = document.getElementById("detail-status");
const detailChain = document.getElementById("detail-chain");
const detailLog = document.getElementById("detail-log");
const continueBox = document.getElementById("continue-box");
const continuePrompt = document.getElementById("continue-prompt");
const continueStatus = document.getElementById("continue-status");

tokenInput.value = localStorage.getItem("rc_token") || "";
document.getElementById("save-token").addEventListener("click", () => {
  localStorage.setItem("rc_token", tokenInput.value.trim());
  submitStatus.textContent = "token 已保存到本地浏览器";
});

function authHeaders() {
  const token = localStorage.getItem("rc_token") || tokenInput.value.trim();
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

function fmtDuration(seconds) {
  if (seconds == null) return "—";
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m${String(s % 60).padStart(2, "0")}s`;
}

function runDuration(r) {
  if (r.duration_seconds != null) return fmtDuration(r.duration_seconds);
  if (r.status === "running" && r.started_at) return fmtDuration(Date.now() / 1000 - r.started_at) + "…";
  return "—";
}

async function loadProjects() {
  const res = await fetch("/config/projects", { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();
  projectSelect.innerHTML = data.projects.map((p) => `<option value="${p}">${p}</option>`).join("");
}

async function loadPresets() {
  const box = document.getElementById("presets");
  const res = await fetch("/config/presets", { headers: authHeaders() });
  if (!res.ok) return;
  const { presets } = await res.json();
  box.innerHTML = "";
  (presets || []).forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "preset-btn";
    btn.textContent = p.label;
    btn.title = p.prompt;
    // 只填充输入框、不直接提交,保留人工确认一步。
    btn.addEventListener("click", () => {
      promptInput.value = p.prompt;
      promptInput.focus();
    });
    box.appendChild(btn);
  });
}

async function loadProbes() {
  const section = document.getElementById("probes");
  const body = document.getElementById("probes-body");
  const res = await fetch("/probes", { headers: authHeaders() });
  if (!res.ok) return;
  const { probes } = await res.json();
  if (!probes || probes.length === 0) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  body.innerHTML = probes
    .map((p) => {
      if (p.error) {
        return `<div class="probe probe-error"><b>${p.name}</b>: ${p.error}</div>`;
      }
      const age = fmtDuration(p.age_seconds);
      const cls = p.stale ? "probe-stale" : "probe-fresh";
      const json = JSON.stringify(p.data, null, 2)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;");
      return `<div class="probe ${cls}"><b>${p.name}</b> <span class="probe-age">${age} 前</span><pre>${json}</pre></div>`;
    })
    .join("");
}

async function loadRuns() {
  const res = await fetch("/triggers", { headers: authHeaders() });
  if (!res.ok) {
    runsBody.innerHTML = `<tr><td colspan="6">加载失败(${res.status})——检查 token</td></tr>`;
    return;
  }
  const runs = await res.json();
  runsBody.innerHTML = runs
    .map((r) => {
      const active = r.status === "queued" || r.status === "running";
      const stopBtn = active ? ` <button data-run="${r.run_id}" class="stop-btn">停止</button>` : "";
      const cost = r.total_cost_usd != null ? ` · $${r.total_cost_usd.toFixed(2)}` : "";
      const chainMark = r.parent_run_id ? " ↩" : "";
      return `
      <tr>
        <td>${r.run_id}${chainMark}</td>
        <td>${r.project_key}</td>
        <td class="status-${r.status}">${r.status}</td>
        <td>${new Date(r.created_at * 1000).toLocaleString()}</td>
        <td>${runDuration(r)}${cost}</td>
        <td><button data-run="${r.run_id}" class="view-btn">查看</button>${stopBtn}</td>
      </tr>`;
    })
    .join("");

  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.addEventListener("click", () => showDetail(btn.dataset.run));
  });
  document.querySelectorAll(".stop-btn").forEach((btn) => {
    btn.addEventListener("click", () => stopRun(btn.dataset.run));
  });
}

async function stopRun(runId) {
  if (!confirm(`停止 run ${runId}?`)) return;
  const res = await fetch(`/triggers/${runId}/stop`, { method: "POST", headers: authHeaders() });
  submitStatus.textContent = res.ok
    ? `已请求停止 ${runId}`
    : `停止失败(${res.status}):${await res.text()}`;
  loadRuns();
}

// ---- transcript 结构化渲染 ------------------------------------------------
// 新日志每行一个 JSON 事件(字段约定见 server/runner.py _events_from_message);
// 旧 run 的日志是 repr 纯文本行——JSON.parse 失败就按纯文本渲染,向后兼容。

function appendBlock(className, label, text) {
  const div = document.createElement("div");
  div.className = `blk ${className}`;
  if (label) {
    const tag = document.createElement("span");
    tag.className = "blk-label";
    tag.textContent = label;
    div.appendChild(tag);
  }
  div.appendChild(document.createTextNode(text));
  const atBottom = detailLog.scrollTop + detailLog.clientHeight >= detailLog.scrollHeight - 8;
  detailLog.appendChild(div);
  if (atBottom) detailLog.scrollTop = detailLog.scrollHeight;
}

function renderLogLine(line) {
  if (!line.trim()) return;
  let ev = null;
  try {
    ev = JSON.parse(line);
  } catch {
    appendBlock("blk-plain", "", line); // 旧格式(repr)兜底
    return;
  }
  if (!ev || typeof ev !== "object") {
    appendBlock("blk-plain", "", line);
    return;
  }
  switch (ev.type) {
    case "text":
      if (ev.role === "user") appendBlock("blk-user", "user", ev.text || "");
      else appendBlock("blk-assistant", "assistant", ev.text || "");
      break;
    case "thinking":
      appendBlock("blk-thinking", "thinking", ev.text || "");
      break;
    case "tool_use":
      appendBlock("blk-tool", `⚙ ${ev.tool_name || "tool"}`, ev.input || "");
      break;
    case "tool_result":
      appendBlock(ev.is_error ? "blk-tool-result blk-error" : "blk-tool-result", "↳ result", ev.text || "");
      break;
    case "system":
      appendBlock(
        "blk-system",
        `[${ev.subtype || "system"}]`,
        ev.subtype === "init" ? `session=${ev.session_id || "?"} model=${ev.model || "?"}` : ""
      );
      break;
    case "result": {
      const cost = ev.total_cost_usd != null ? ` · $${ev.total_cost_usd.toFixed(4)}` : "";
      const turns = ev.num_turns != null ? ` · ${ev.num_turns} turns` : "";
      const dur = ev.duration_ms != null ? ` · ${(ev.duration_ms / 1000).toFixed(1)}s` : "";
      appendBlock(
        ev.is_error ? "blk-result blk-error" : "blk-result",
        "■ result",
        `${ev.subtype || ""}${cost}${turns}${dur}`
      );
      break;
    }
    case "approval_request":
      renderApprovalCard(ev);
      break;
    case "approval_decision":
      settleApprovalCard(ev.approval_id, ev.status);
      break;
    default:
      appendBlock("blk-plain", "", ev.text || line);
  }
}

// ---- 权限确认卡片 -----------------------------------------------------------
// approval_request/approval_decision 都是 run 日志里的事件(经 SSE 到达,回放也有),
// 所以历史 run 的详情会重现"请求→裁决"的闭环;仍 pending 且未过期的才显示按钮。

let approvalCards = {}; // approval_id → {card, actions} (showDetail 时重置)

function renderApprovalCard(ev) {
  const card = document.createElement("div");
  card.className = "blk blk-approval";
  const tag = document.createElement("span");
  tag.className = "blk-label";
  tag.textContent = `⏳ 待确认 ⚙ ${ev.tool_name || "tool"}`;
  card.appendChild(tag);
  card.appendChild(document.createTextNode(ev.input || ""));

  const actions = document.createElement("div");
  actions.className = "approval-actions";
  if (ev.expires_at && ev.expires_at * 1000 > Date.now()) {
    const allowBtn = document.createElement("button");
    allowBtn.textContent = "允许";
    allowBtn.className = "approve-btn";
    const denyBtn = document.createElement("button");
    denyBtn.textContent = "拒绝";
    denyBtn.className = "deny-btn";
    allowBtn.addEventListener("click", () => decideApproval(ev.approval_id, "allow"));
    denyBtn.addEventListener("click", () => decideApproval(ev.approval_id, "deny"));
    actions.appendChild(allowBtn);
    actions.appendChild(denyBtn);
  } else {
    actions.textContent = "已过期(默认拒绝)";
  }
  card.appendChild(actions);
  approvalCards[ev.approval_id] = { card, actions };

  const atBottom = detailLog.scrollTop + detailLog.clientHeight >= detailLog.scrollHeight - 8;
  detailLog.appendChild(card);
  if (atBottom) detailLog.scrollTop = detailLog.scrollHeight;
}

function settleApprovalCard(approvalId, status) {
  const entry = approvalCards[approvalId];
  const text = { allowed: "✔ 已允许", denied: "✘ 已拒绝", expired: "⏱ 超时(默认拒绝)" }[status] || status;
  if (!entry) {
    appendBlock("blk-system", "[approval]", `${approvalId} ${text}`);
    return;
  }
  entry.actions.textContent = text;
  entry.card.classList.add(status === "allowed" ? "approval-allowed" : "approval-denied");
}

async function decideApproval(approvalId, decision) {
  const res = await fetch(`/approvals/${approvalId}`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ decision }),
  });
  if (!res.ok && res.status !== 409) {
    submitStatus.textContent = `裁决失败(${res.status}):${await res.text()}`;
  }
  // 成功(或 409 已被别处裁决)后不直接改卡片——approval_decision 事件马上经 SSE 到达,
  // 由它统一收口,避免两条路径打架。
}

// ---- 对话链导航 + 继续对话 -------------------------------------------------

function renderChain(run) {
  detailChain.innerHTML = "";
  const parts = [];
  if (run.parent_run_id) parts.push({ id: run.parent_run_id, label: `↰ 上一段 ${run.parent_run_id}` });
  (run.children || []).forEach((c) => parts.push({ id: c, label: `↳ 后续 ${c}` }));
  parts.forEach((p) => {
    const btn = document.createElement("button");
    btn.className = "chain-btn";
    btn.textContent = p.label;
    btn.addEventListener("click", () => showDetail(p.id));
    detailChain.appendChild(btn);
  });
}

let currentDetailId = null;

async function refreshDetailMeta(runId) {
  const res = await fetch(`/triggers/${runId}`, { headers: authHeaders() });
  if (!res.ok) return;
  const run = await res.json();
  if (currentDetailId !== runId) return; // 已切到别的 run,别动 UI
  renderChain(run);
  const canContinue = ["completed", "failed", "stopped"].includes(run.status) && !!run.session_id;
  continueBox.hidden = !canContinue;
}

document.getElementById("continue-submit").addEventListener("click", async () => {
  const prompt = continuePrompt.value.trim();
  if (!prompt || !currentDetailId) {
    continueStatus.textContent = "prompt 不能为空";
    return;
  }
  continueStatus.textContent = "提交中...";
  const res = await fetch(`/triggers/${currentDetailId}/continue`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    continueStatus.textContent = `续聊失败(${res.status}):${await res.text()}`;
    return;
  }
  const data = await res.json();
  continueStatus.textContent = "";
  continuePrompt.value = "";
  loadRuns();
  showDetail(data.run_id);
});

// ---- 详情视图(SSE 增量渲染) ----------------------------------------------

let eventSource = null;

async function showDetail(runId) {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  currentDetailId = runId;
  detailSection.hidden = false;
  detailRunId.textContent = runId;
  detailStatus.textContent = "连接中…";
  detailChain.innerHTML = "";
  detailLog.innerHTML = "";
  approvalCards = {};
  continueBox.hidden = true;
  continueStatus.textContent = "";

  refreshDetailMeta(runId);

  // EventSource 不能带 Authorization 头,所以先用 token 换一张短时一次性 ticket,
  // 只有 ticket(60s 过期、用一次即作废、绑定这个 run)出现在 URL 里,长期 token
  // 不进浏览器历史 / 反代 access log。
  const ticketRes = await fetch(`/triggers/${runId}/stream-ticket`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!ticketRes.ok) {
    detailStatus.textContent = `获取流凭证失败(${ticketRes.status})`;
    return;
  }
  const { ticket } = await ticketRes.json();

  const es = new EventSource(`/triggers/${runId}/stream?ticket=${encodeURIComponent(ticket)}`);
  eventSource = es;
  detailStatus.textContent = "streaming";

  es.addEventListener("log", (e) => {
    if (currentDetailId === runId) renderLogLine(e.data);
  });

  es.addEventListener("end", (e) => {
    es.close();
    if (eventSource === es) eventSource = null;
    if (currentDetailId === runId) {
      detailStatus.textContent = `结束(${e.data})`;
      refreshDetailMeta(runId); // run 结束后刷新链与「继续对话」框
    }
    loadRuns();
  });

  es.onerror = () => {
    // ticket 是一次性的,EventSource 自动重连必然 401;直接关掉并提示手动重开。
    es.close();
    if (eventSource === es) {
      eventSource = null;
      if (currentDetailId === runId) detailStatus.textContent = "连接断开——点「查看」重新连接";
    }
  };
}

document.getElementById("submit-trigger").addEventListener("click", async () => {
  const prompt = promptInput.value.trim();
  const project_key = projectSelect.value;
  if (!prompt || !project_key) {
    submitStatus.textContent = "prompt 和项目都不能为空";
    return;
  }
  submitStatus.textContent = "提交中...";
  const res = await fetch("/triggers", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ prompt, project_key }),
  });
  if (!res.ok) {
    submitStatus.textContent = `触发失败(${res.status}):${await res.text()}`;
    return;
  }
  const data = await res.json();
  submitStatus.textContent = `已触发 run_id=${data.run_id}`;
  promptInput.value = "";
  loadRuns();
  showDetail(data.run_id);
});

document.getElementById("refresh-runs").addEventListener("click", loadRuns);
document.getElementById("refresh-probes").addEventListener("click", loadProbes);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {
    // 注册失败不影响核心功能(触发/查看仍然可用),静默忽略。
  });
}

// ---- Web Push 订阅 -----------------------------------------------------------

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

document.getElementById("enable-push").addEventListener("click", async () => {
  try {
    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      submitStatus.textContent = "此浏览器不支持 Web Push";
      return;
    }
    const cfgRes = await fetch("/push/config", { headers: authHeaders() });
    if (!cfgRes.ok) {
      submitStatus.textContent = `获取推送配置失败(${cfgRes.status})——检查 token`;
      return;
    }
    const cfg = await cfgRes.json();
    if (!cfg.enabled) {
      submitStatus.textContent = "服务端未配置 VAPID,推送功能未启用";
      return;
    }
    const perm = await Notification.requestPermission();
    if (perm !== "granted") {
      submitStatus.textContent = "通知权限被拒绝";
      return;
    }
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(cfg.public_key),
    });
    const res = await fetch("/push/subscriptions", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(sub.toJSON()),
    });
    submitStatus.textContent = res.ok ? "已订阅通知(完成/失败/待确认)" : `订阅失败(${res.status})`;
  } catch (e) {
    submitStatus.textContent = `订阅出错:${e && e.message ? e.message : e}`;
  }
});

loadProjects();
loadPresets();
loadRuns();
loadProbes();
setInterval(loadRuns, 5000);
setInterval(loadProbes, 15000);

// 从推送通知点进来:/?run=<id> 直达详情。
const bootRun = new URLSearchParams(location.search).get("run");
if (bootRun) showDetail(bootRun);
