const tokenInput = document.getElementById("token");
const projectSelect = document.getElementById("project-key");
const promptInput = document.getElementById("prompt");
const submitStatus = document.getElementById("submit-status");
const runsBody = document.getElementById("runs-body");
const detailSection = document.getElementById("detail");
const detailRunId = document.getElementById("detail-run-id");
const detailLog = document.getElementById("detail-log");

tokenInput.value = localStorage.getItem("rc_token") || "";
document.getElementById("save-token").addEventListener("click", () => {
  localStorage.setItem("rc_token", tokenInput.value.trim());
  submitStatus.textContent = "token 已保存到本地浏览器";
});

function authHeaders() {
  const token = localStorage.getItem("rc_token") || tokenInput.value.trim();
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

async function loadProjects() {
  const res = await fetch("/config/projects", { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();
  projectSelect.innerHTML = data.projects.map((p) => `<option value="${p}">${p}</option>`).join("");
}

async function loadRuns() {
  const res = await fetch("/triggers", { headers: authHeaders() });
  if (!res.ok) {
    runsBody.innerHTML = `<tr><td colspan="5">加载失败(${res.status})——检查 token</td></tr>`;
    return;
  }
  const runs = await res.json();
  runsBody.innerHTML = runs
    .map(
      (r) => `
      <tr>
        <td>${r.run_id}</td>
        <td>${r.project_key}</td>
        <td class="status-${r.status}">${r.status}</td>
        <td>${new Date(r.created_at * 1000).toLocaleString()}</td>
        <td><button data-run="${r.run_id}" class="view-btn">查看</button></td>
      </tr>`
    )
    .join("");

  document.querySelectorAll(".view-btn").forEach((btn) => {
    btn.addEventListener("click", () => showDetail(btn.dataset.run));
  });
}

async function showDetail(runId) {
  detailSection.hidden = false;
  detailRunId.textContent = runId;
  const res = await fetch(`/triggers/${runId}/log`, { headers: authHeaders() });
  detailLog.textContent = res.ok ? await res.text() : `加载失败(${res.status})`;
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
});

document.getElementById("refresh-runs").addEventListener("click", loadRuns);

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {
    // 注册失败不影响核心功能(触发/查看仍然可用),静默忽略。
  });
}

loadProjects();
loadRuns();
setInterval(loadRuns, 5000);
