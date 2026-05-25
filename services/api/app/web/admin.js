const state = {
  activeTab: "content",
  uploads: [],
  selectedUploadId: null,
  projects: [],
  providers: [],
};

const els = {
  tabs: document.querySelectorAll("[data-tab]"),
  contentTab: document.getElementById("content-tab"),
  ordersTab: document.getElementById("orders-tab"),
  uploadList: document.getElementById("upload-list"),
  pipelineDetail: document.getElementById("pipeline-detail"),
  orders: document.getElementById("orders"),
  projectSelect: document.getElementById("project-select"),
  uploadForm: document.getElementById("upload-form"),
  uploadFile: document.getElementById("upload-file"),
  uploadNotes: document.getElementById("upload-notes"),
  providerDiagnostics: document.getElementById("provider-diagnostics"),
  refreshPipeline: document.getElementById("refresh-pipeline"),
  refreshOrders: document.getElementById("refresh-orders"),
  logoutButton: document.getElementById("logout-button"),
};

const orderStatuses = ["confirmed", "preparing", "delivering", "completed", "cancelled"];

init().catch(showFatalError);

async function init() {
  bindChrome();
  await ensureAuth();
  await Promise.all([loadProjects(), loadUploads(), loadOrders(), loadProviderDiagnostics()]);
  if (state.uploads[0]) {
    await selectUpload(state.uploads[0].id);
  } else {
    renderEmptyPipeline();
  }
}

function bindChrome() {
  els.tabs.forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });
  els.refreshPipeline.addEventListener("click", () => refreshPipeline());
  els.refreshOrders.addEventListener("click", () => loadOrders());
  els.uploadForm.addEventListener("submit", handleUpload);
  els.logoutButton.addEventListener("click", logout);
}

async function ensureAuth() {
  const response = await fetch("/api/v1/auth/me", { cache: "no-store" });
  if (response.status === 401) {
    window.location.href = "/admin/login";
    return;
  }
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function logout() {
  await fetch("/api/v1/auth/logout", { method: "POST" });
  window.location.href = "/admin/login";
}

function switchTab(tab) {
  state.activeTab = tab;
  els.tabs.forEach((button) => button.classList.toggle("is-active", button.dataset.tab === tab));
  els.contentTab.classList.toggle("hidden", tab !== "content");
  els.ordersTab.classList.toggle("hidden", tab !== "orders");
}

async function loadProjects() {
  const projects = await requestJson("/api/v1/projects");
  state.projects = projects;
  els.projectSelect.innerHTML = projects
    .map((project) => `<option value="${project.id}">${escapeHtml(project.name)} / ${escapeHtml(project.slug)}</option>`)
    .join("");
}

async function loadUploads() {
  const payload = await requestJson("/api/v1/uploads?limit=40");
  state.uploads = payload.uploads;
  renderUploads();
}

async function loadProviderDiagnostics() {
  const payload = await requestJson("/api/v1/providers/diagnostics");
  state.providers = payload.providers;
  renderProviderDiagnostics();
}

function renderProviderDiagnostics() {
  if (!els.providerDiagnostics) return;
  if (!state.providers.length) {
    els.providerDiagnostics.innerHTML = "<p class='eyebrow'>Providers</p><p class='muted'>Нет данных.</p>";
    return;
  }
  els.providerDiagnostics.innerHTML = `
    <p class="eyebrow">Providers</p>
    ${state.providers
      .map((provider) => {
        const isReady = provider.production_ready || provider.configured || provider.fallback_enabled;
        const missing = provider.missing_env.length ? `<br><span class="muted">Missing: ${provider.missing_env.map(escapeHtml).join(", ")}</span>` : "";
        return `
          <p>
            <span class="pill ${isReady ? "good" : "warn"}">${escapeHtml(provider.area)}</span>
            <span class="pill">${escapeHtml(provider.selected_provider)} → ${escapeHtml(provider.effective_provider)}</span>
            ${provider.production_ready ? `<span class="pill good">production ready</span>` : `<span class="pill warn">dev/mock mode</span>`}
            ${missing}
          </p>
        `;
      })
      .join("")}
  `;
}

function renderUploads() {
  if (!state.uploads.length) {
    els.uploadList.innerHTML = "<div class='admin-card'><p class='muted'>Загрузок пока нет.</p></div>";
    return;
  }
  els.uploadList.innerHTML = state.uploads
    .map(
      (upload) => `
        <button class="upload-item ${upload.id === state.selectedUploadId ? "is-active" : ""}" type="button" data-upload-id="${upload.id}">
          <strong>${statusLabel(upload.status)}</strong>
          <span class="muted">${formatDate(upload.created_at)}</span>
          <small>${escapeHtml(upload.notes || upload.created_by)}</small>
        </button>
      `,
    )
    .join("");
  els.uploadList.querySelectorAll("[data-upload-id]").forEach((button) => {
    button.addEventListener("click", () => selectUpload(button.dataset.uploadId));
  });
}

async function selectUpload(uploadId) {
  state.selectedUploadId = uploadId;
  renderUploads();
  els.pipelineDetail.innerHTML = "<div class='admin-card'><p class='muted'>Загружаю pipeline...</p></div>";
  const summary = await requestJson(`/api/v1/uploads/${uploadId}/pipeline`);
  renderPipeline(summary);
}

async function refreshPipeline() {
  await Promise.all([loadUploads(), loadProviderDiagnostics()]);
  if (state.selectedUploadId) {
    await selectUpload(state.selectedUploadId);
  }
}

async function handleUpload(event) {
  event.preventDefault();
  const file = els.uploadFile.files[0];
  const projectId = els.projectSelect.value;
  if (!file || !projectId) return;

  const body = new FormData();
  body.append("project_id", projectId);
  body.append("created_by", "operator-dashboard");
  body.append("notes", els.uploadNotes.value || "dashboard upload");
  body.append("file", file);

  const upload = await requestJson("/api/v1/uploads", { method: "POST", body });
  els.uploadForm.reset();
  await loadUploads();
  await selectUpload(upload.id);
}

function renderEmptyPipeline() {
  els.pipelineDetail.innerHTML = `
    <div class="admin-card">
      <p class="eyebrow">Pipeline</p>
      <h2>Загрузите фото блюда</h2>
      <p class="muted">После загрузки здесь появятся analysis, drafts, assets, approval и publication tasks.</p>
    </div>
  `;
}

function renderPipeline(summary) {
  const approval = summary.approvals.at(-1);
  els.pipelineDetail.innerHTML = `
    <article class="admin-card">
      <div class="order-head">
        <div>
          <p class="eyebrow">Upload ${summary.upload.id.slice(0, 8)}</p>
          <h2>${statusLabel(summary.upload.status)}</h2>
          <p class="muted">${escapeHtml(summary.upload.notes || "Без комментария")}</p>
        </div>
        <span class="pill ${summary.upload.status === "completed" ? "good" : "warn"}">${escapeHtml(summary.upload.status)}</span>
      </div>
      <div class="status-row">
        <span class="pill">Analysis: ${summary.analysis_results.length}</span>
        <span class="pill">Drafts: ${summary.drafts.length}</span>
        <span class="pill">Assets: ${summary.assets.length}</span>
        <span class="pill">Publications: ${summary.publication_tasks.length}</span>
      </div>
      ${approval ? renderApproval(approval) : ""}
    </article>
    <div class="pipeline-grid">
      <article class="admin-card">${renderAnalysis(summary.analysis_results)}</article>
      <article class="admin-card">${renderTimeline(summary.timeline)}</article>
      <article class="admin-card wide">${renderDrafts(summary.drafts)}</article>
      <article class="admin-card wide">${renderAIVideo(summary.scene_plans || [], summary.drafts)}</article>
      <article class="admin-card wide">${renderPublications(summary.publication_tasks)}</article>
      <article class="admin-card wide">${renderAssets(summary.assets)}</article>
    </div>
  `;
  bindPipelineActions(summary);
}

function renderAIVideo(scenePlans, drafts) {
  const latest = scenePlans.at(0);
  if (!latest) {
    return `
      <p class="eyebrow">AI Video</p>
      <p class="muted">ScenePlan еще не создан. Старый template video pipeline при этом остается рабочим.</p>
      <div class="card-actions">
        <button type="button" data-ai-video-action="create-full-video" ${drafts.length ? "" : "disabled"}>Generate full AI video</button>
      </div>
    `;
  }
  return `
    <p class="eyebrow">AI Video</p>
    <div class="order-head">
      <div>
        <h3>ScenePlan ${latest.id.slice(0, 8)}</h3>
        <p class="muted">${escapeHtml(latest.status)} / ${escapeHtml(latest.aspect_ratio)} / ${latest.total_duration_sec}s</p>
      </div>
      <span class="pill">${latest.scenes.length} scenes</span>
    </div>
    <div class="asset-grid">
      ${latest.scenes
        .map(
          (scene) => `
            <div class="asset-card">
              <span class="pill ${scene.status === "generated" ? "good" : "warn"}">Scene ${scene.scene_number} / ${escapeHtml(scene.status)}</span>
              <span class="pill">${escapeHtml(scene.provider)}</span>
              <p>${escapeHtml(scene.subtitle_text || scene.visual_prompt)}</p>
              <p class="muted">${escapeHtml(scene.emotion || "")} ${scene.duration_sec}s</p>
              <div class="card-actions">
                <button type="button" data-ai-scene-id="${scene.id}">Regenerate scene</button>
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
    <div class="card-actions">
      <button type="button" data-ai-video-action="regenerate-plan" data-scene-plan-id="${latest.id}">Regenerate scene plan</button>
      <button type="button" data-ai-video-action="generate-scenes" data-scene-plan-id="${latest.id}">Generate scenes</button>
      <button type="button" data-ai-video-action="render-final" data-scene-plan-id="${latest.id}">Render final video</button>
      <button type="button" data-ai-video-action="generate-full-video" data-scene-plan-id="${latest.id}">Generate full AI video</button>
    </div>
  `;
}

function renderApproval(approval) {
  return `
    <div class="admin-card" style="margin-top:14px;margin-bottom:0">
      <p class="eyebrow">Approval</p>
      <div class="order-head">
        <strong>${statusLabel(approval.status)}</strong>
        <span class="muted">${formatDate(approval.created_at)}</span>
      </div>
      <div class="card-actions">
        <button type="button" data-approval-id="${approval.id}" data-decision="approved">Approve</button>
        <button type="button" data-approval-id="${approval.id}" data-decision="rejected">Reject</button>
        <button type="button" data-approval-id="${approval.id}" data-decision="regenerate_requested">Regenerate</button>
      </div>
    </div>
  `;
}

function renderAnalysis(results) {
  const latest = results.at(-1);
  if (!latest) return "<p class='eyebrow'>Analysis</p><p class='muted'>Нет анализа.</p>";
  return `
    <p class="eyebrow">Vision Analysis</p>
    <h3>${escapeHtml(latest.dish_name || "Без названия")}</h3>
    <span class="pill">${escapeHtml(latest.provider || "unknown-provider")}</span>
    <p class="muted">${escapeHtml(latest.visual_mood || "")} / ${escapeHtml(latest.plating_style || "")}</p>
    <p>${latest.ingredients.map(escapeHtml).join(", ")}</p>
  `;
}

function renderTimeline(events) {
  return `
    <p class="eyebrow">Timeline</p>
    ${events
      .slice(-8)
      .reverse()
      .map((event) => `<p><strong>${escapeHtml(event.event_type)}</strong><br><span class="muted">${formatDate(event.created_at)} / ${escapeHtml(event.actor)}</span></p>`)
      .join("")}
  `;
}

function renderDrafts(drafts) {
  if (!drafts.length) return "<p class='eyebrow'>Drafts</p><p class='muted'>Черновиков пока нет.</p>";
  return `
    <p class="eyebrow">Content Drafts</p>
    <div class="asset-grid">
      ${drafts
        .map(
          (draft) => `
            <div class="draft-card">
              <span class="pill">${escapeHtml(draft.platform)} / ${escapeHtml(draft.kind)}</span>
              <span class="pill">v${draft.version}</span>
              ${draft.metadata_json?.provider ? `<span class="pill">${escapeHtml(draft.metadata_json.provider)}</span>` : ""}
              <h3>${escapeHtml(draft.title || draft.platform)}</h3>
              <p>${escapeHtml(draft.caption)}</p>
              <p class="muted">${escapeHtml(draft.cta || "")}</p>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderPublications(tasks) {
  if (!tasks.length) return "<p class='eyebrow'>Publication Tasks</p><p class='muted'>Появятся после approve.</p>";
  return `
    <p class="eyebrow">Publication Tasks</p>
    <div class="publication-grid">
      ${tasks
        .map((task) => {
          const result = task.results.at(-1);
          const provider = result?.payload?.provider || result?.payload?.adapter || "not-run";
          const fallback = result?.payload?.fallback_reason;
          const isManualPackage = result?.payload?.mode === "manual_package";
          return `
            <div class="publication-card">
              <span class="pill ${task.status === "published" ? "good" : "warn"}">${escapeHtml(task.platform)} / ${escapeHtml(task.status)}</span>
              <span class="pill">${escapeHtml(provider)}</span>
              <p class="muted">Attempts: ${task.attempt_count}</p>
              ${fallback ? `<p class="muted">Fallback: ${escapeHtml(fallback)}</p>` : ""}
              ${result?.error_message ? `<p class="muted">Error: ${escapeHtml(result.error_message)}</p>` : ""}
              ${result?.remote_url ? `<a class="button" href="${escapeAttr(result.remote_url)}" target="_blank" rel="noreferrer">${isManualPackage ? "Manual package" : "Remote URL"}</a>` : ""}
              <div class="card-actions">
                <button type="button" data-publication-id="${task.id}" ${task.status === "published" ? "disabled" : ""}>Run publish</button>
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderAssets(assets) {
  if (!assets.length) return "<p class='eyebrow'>Assets</p><p class='muted'>Ассетов пока нет.</p>";
  return `
    <p class="eyebrow">Assets</p>
    <div class="asset-grid">
      ${assets
        .map(
          (asset) => `
            <div class="asset-card">
              <span class="pill">${escapeHtml(asset.kind)}</span>
              ${asset.metadata_json?.provider ? `<span class="pill">${escapeHtml(asset.metadata_json.provider)}</span>` : ""}
              ${asset.metadata_json?.requested_provider ? `<span class="pill">fallback from ${escapeHtml(asset.metadata_json.requested_provider)}</span>` : ""}
              <h3>${escapeHtml(asset.file_name)}</h3>
              <p class="muted">${escapeHtml(asset.platform || "source")} ${asset.duration_seconds ? `/ ${asset.duration_seconds}s` : ""}</p>
              <a class="button" href="${escapeAttr(asset.download_url)}" target="_blank" rel="noreferrer">Открыть</a>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function bindPipelineActions() {
  els.pipelineDetail.querySelectorAll("[data-approval-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await requestJson(`/api/v1/approval-tasks/${button.dataset.approvalId}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: button.dataset.decision,
          actor: "operator-dashboard",
          note: "Dashboard action",
          via: "dashboard",
        }),
      });
      await refreshPipeline();
    });
  });
  els.pipelineDetail.querySelectorAll("[data-publication-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      await requestJson(`/api/v1/publication-tasks/${button.dataset.publicationId}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ actor: "operator-dashboard" }),
      });
      window.setTimeout(refreshPipeline, 900);
    });
  });
  els.pipelineDetail.querySelectorAll("[data-ai-video-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      const action = button.dataset.aiVideoAction;
      const scenePlanId = button.dataset.scenePlanId;
      if (action === "create-full-video") {
        const plan = await requestJson(`/api/v1/uploads/${state.selectedUploadId}/scene-plans`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        await requestJson(`/api/v1/scene-plans/${plan.id}/generate-scenes`, { method: "POST" });
        await requestJson(`/api/v1/scene-plans/${plan.id}/render-final-video`, { method: "POST" });
      } else if (action === "regenerate-plan") {
        await requestJson(`/api/v1/scene-plans/${scenePlanId}/regenerate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "Dashboard action" }),
        });
      } else if (action === "generate-scenes") {
        await requestJson(`/api/v1/scene-plans/${scenePlanId}/generate-scenes`, { method: "POST" });
      } else if (action === "render-final") {
        await requestJson(`/api/v1/scene-plans/${scenePlanId}/render-final-video`, { method: "POST" });
      } else if (action === "generate-full-video") {
        await requestJson(`/api/v1/scene-plans/${scenePlanId}/generate-scenes`, { method: "POST" });
        await requestJson(`/api/v1/scene-plans/${scenePlanId}/render-final-video`, { method: "POST" });
      }
      await refreshPipeline();
    });
  });
  els.pipelineDetail.querySelectorAll("[data-ai-scene-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      await requestJson(`/api/v1/scenes/${button.dataset.aiSceneId}/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: "Dashboard action" }),
      });
      await refreshPipeline();
    });
  });
}

async function loadOrders() {
  const payload = await requestJson("/api/v1/store/orders");
  renderOrders(payload.orders);
}

function renderOrders(orders) {
  if (!orders.length) {
    els.orders.innerHTML = "<div class='order-card'><p>Заказов пока нет.</p></div>";
    return;
  }
  els.orders.innerHTML = orders
    .map((order) => {
      const items = order.items_json.map((item) => `<li>${escapeHtml(item.title)} × ${item.quantity} — ${item.line_total} ₽</li>`).join("");
      const actions = orderStatuses
        .map((status) => `<button type="button" data-order-id="${order.id}" data-status="${status}">${statusLabel(status)}</button>`)
        .join("");
      return `
        <article class="order-card">
          <div class="order-head">
            <div>
              <p class="eyebrow">Заказ</p>
              <h3>${escapeHtml(order.customer_name)}</h3>
            </div>
            <strong>${order.total_amount} ${escapeHtml(order.currency)}</strong>
          </div>
          <div class="order-meta">
            <span>${escapeHtml(order.customer_phone)}</span>
            <span>${escapeHtml(order.delivery_address)}</span>
            <span>Статус: <strong>${statusLabel(order.status)}</strong></span>
            <span>Оплата: <strong>${paymentLabel(order.payment_method)}</strong></span>
          </div>
          <ul class="order-items">${items}</ul>
          <div class="card-actions">${actions}</div>
        </article>
      `;
    })
    .join("");
  els.orders.querySelectorAll("[data-order-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await requestJson(`/api/v1/store/orders/${button.dataset.orderId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: button.dataset.status }),
      });
      await loadOrders();
    });
  });
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    if (response.status === 401) {
      window.location.href = "/admin/login";
      throw new Error("Authentication required");
    }
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function showFatalError(error) {
  console.error(error);
  els.pipelineDetail.innerHTML = `<div class="admin-card"><p>Ошибка: ${escapeHtml(error.message)}</p></div>`;
}

function statusLabel(status) {
  return {
    new: "Новый",
    queued: "В очереди",
    processing: "В обработке",
    needs_review: "На согласовании",
    completed: "Готово",
    failed: "Ошибка",
    pending: "Ожидает",
    dispatched: "Отправлено",
    approved: "Approved",
    rejected: "Rejected",
    regenerate_requested: "Regenerate",
    confirmed: "Подтвержден",
    preparing: "Готовится",
    delivering: "В пути",
    cancelled: "Отменен",
    published: "Опубликовано",
    publishing: "Публикуется",
    scheduled: "Запланировано",
  }[status] || status;
}

function paymentLabel(method) {
  return {
    cash: "Наличными",
    card_on_delivery: "Картой при получении",
    online: "Онлайн",
  }[method] || method;
}

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

function escapeAttr(value) {
  return escapeHtml(value || "#");
}
