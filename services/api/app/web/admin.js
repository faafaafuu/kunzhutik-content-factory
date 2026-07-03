const state = {
  activeTab: "content",
  uploads: [],
  selectedUploadId: null,
  projects: [],
  providers: [],
  pollTimer: null,
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
  fileDropLabel: document.getElementById("file-drop-label"),
  fileDrop: document.getElementById("file-drop"),
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
  els.uploadFile.addEventListener("change", () => {
    const file = els.uploadFile.files[0];
    els.fileDropLabel.textContent = file ? file.name : "Выберите фото блюда";
    els.fileDrop.classList.toggle("has-file", Boolean(file));
  });
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
    .map((project) => `<option value="${project.id}">${escapeHtml(project.name)}</option>`)
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
    els.providerDiagnostics.innerHTML = "<p class='section-title'>Провайдеры</p><p class='muted small'>Нет данных.</p>";
    return;
  }
  const areaNames = {
    vision: "Анализ фото",
    text_generation: "Тексты",
    tts: "Озвучка",
    video_render: "Сборка видео",
    ai_video: "AI-видео",
    publishing: "Публикация",
  };
  els.providerDiagnostics.innerHTML = `
    <p class="section-title">Провайдеры</p>
    ${state.providers
      .map((provider) => {
        const real = provider.production_ready;
        const missing = provider.missing_env.length
          ? `<span class="muted small">нужен ${provider.missing_env.map(escapeHtml).join(", ")}</span>`
          : "";
        return `
          <div class="provider-row">
            <span class="small" style="font-weight:700;min-width:110px">${escapeHtml(areaNames[provider.area] || provider.area)}</span>
            <span class="chip ${real ? "good" : "warn"}">${escapeHtml(provider.effective_provider)}</span>
            ${missing}
          </div>
        `;
      })
      .join("")}
  `;
}

function renderUploads() {
  if (!state.uploads.length) {
    els.uploadList.innerHTML = "<p class='muted small'>Загрузок пока нет — начните с фото блюда.</p>";
    return;
  }
  els.uploadList.innerHTML = state.uploads
    .map(
      (upload) => `
        <button class="upload-item ${upload.id === state.selectedUploadId ? "is-active" : ""}" type="button" data-upload-id="${upload.id}">
          <span class="row">
            <span class="chip ${statusTone(upload.status)}">${statusLabel(upload.status)}</span>
            <span class="muted small">${formatDate(upload.created_at)}</span>
          </span>
          <span class="muted small">${escapeHtml(upload.notes || upload.created_by)}</span>
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
  const summary = await requestJson(`/api/v1/uploads/${uploadId}/pipeline`);
  renderPipeline(summary);
  schedulePoll(summary);
}

function schedulePoll(summary) {
  if (state.pollTimer) {
    window.clearTimeout(state.pollTimer);
    state.pollTimer = null;
  }
  const busy = ["queued", "processing"].includes(summary.upload.status);
  if (busy) {
    state.pollTimer = window.setTimeout(() => refreshPipeline(), 5000);
  }
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
  els.fileDropLabel.textContent = "Выберите фото блюда";
  els.fileDrop.classList.remove("has-file");
  await loadUploads();
  await selectUpload(upload.id);
}

function renderEmptyPipeline() {
  els.pipelineDetail.innerHTML = `
    <div class="card empty">
      <h2>Загрузите фото блюда</h2>
      <p class="muted">Конвейер сам подготовит тексты и сценарий, а видео сгенерируется только после вашего одобрения.</p>
    </div>
  `;
}

/* ---------- pipeline rendering ---------- */

function renderPipeline(summary) {
  const analysis = summary.analysis_results.at(-1);
  const plan = summary.scene_plans.at(0);
  const approvals = summary.approvals || [];
  const contentApproval = approvals.filter((a) => a.stage === "content").at(-1);
  const videoApproval = approvals.filter((a) => a.stage === "video").at(-1);
  const pendingApproval = approvals.filter((a) => ["pending", "dispatched"].includes(a.status)).at(-1);
  const finalVideo = findFinalVideo(summary.assets);
  const busy = ["queued", "processing"].includes(summary.upload.status);

  els.pipelineDetail.innerHTML = `
    <article class="card">
      <div class="review-head">
        <div>
          <h2>${escapeHtml(analysis?.dish_name || "Обработка фото…")}</h2>
          <p class="muted small">${escapeHtml(summary.upload.notes || "")} · ${formatDate(summary.upload.created_at)}</p>
        </div>
        <span class="chip ${statusTone(summary.upload.status)}">${statusLabel(summary.upload.status)}</span>
      </div>
      ${renderSteps(summary, contentApproval, videoApproval, finalVideo)}
      ${busy ? `<p class="muted" style="margin-top:12px">${summary.upload.status === "processing" && contentApproval?.status === "approved" && !finalVideo ? "Генерируем видео — это платный шаг, займёт несколько минут…" : "Конвейер работает…"}</p>` : ""}
    </article>
    ${pendingApproval ? renderReview(pendingApproval, summary, plan, finalVideo) : ""}
    <div class="grid-2">
      <article class="card">${renderDrafts(summary.drafts)}</article>
      <article class="card">${renderScenario(plan, pendingApproval)}</article>
      <article class="card">${renderPublications(summary.publication_tasks)}</article>
      <article class="card">${renderTimeline(summary.timeline)}</article>
    </div>
    <article class="card" style="margin-top:14px">${renderAssets(summary.assets)}${renderTools(plan)}</article>
  `;
  bindPipelineActions(summary);
}

function renderSteps(summary, contentApproval, videoApproval, finalVideo) {
  const hasPlanOrDrafts = summary.drafts.length > 0;
  const published = summary.publication_tasks.some((task) => task.status === "published");
  const steps = [
    { label: "Фото", done: true },
    { label: "Тексты и сценарий", done: hasPlanOrDrafts, current: !hasPlanOrDrafts },
    {
      label: "Согласование сценария",
      done: contentApproval?.status === "approved",
      current: Boolean(contentApproval && ["pending", "dispatched"].includes(contentApproval.status)),
    },
    {
      label: "Видео",
      done: Boolean(finalVideo),
      current: contentApproval?.status === "approved" && !finalVideo,
    },
    {
      label: "Согласование ролика",
      done: videoApproval?.status === "approved",
      current: Boolean(videoApproval && ["pending", "dispatched"].includes(videoApproval.status)),
    },
    {
      label: "Публикация",
      done: published,
      current: videoApproval?.status === "approved" && !published,
    },
  ];
  return `
    <div class="steps">
      ${steps
        .map(
          (step, index) => `
            ${index ? '<span class="step-sep"></span>' : ""}
            <span class="step ${step.done ? "done" : ""} ${step.current ? "current" : ""}">
              <span class="dot">${step.done ? "✓" : index + 1}</span>
              <span class="lbl">${step.label}</span>
            </span>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderReview(approval, summary, plan, finalVideo) {
  if (approval.stage === "content") {
    const scenes = plan?.scenes?.length ? plan.scenes : approval.preview_payload?.scenes || [];
    return `
      <article class="card review-card">
        <p class="review-kicker">Шаг 1 из 2 · Согласование сценария</p>
        <h2>Проверьте тексты и сценарий</h2>
        <p class="muted">Видео ещё не генерировалось — правки сейчас бесплатны. После одобрения запустится платная генерация ролика.</p>
        <div class="scene-list">
          ${scenes
            .map(
              (scene) => `
                <div class="scene-row">
                  <span class="num">${scene.scene_number}</span>
                  <div>
                    <p style="margin:0;font-weight:600">${escapeHtml(scene.subtitle_text || scene.voice_text || "")}</p>
                    <p class="muted small" style="margin:4px 0 0">${escapeHtml(scene.visual_prompt || "")}</p>
                  </div>
                  <div class="meta">
                    <span class="chip">${Number(scene.duration_sec)} сек</span>
                    ${scene.emotion ? `<span class="muted small">${escapeHtml(scene.emotion)}</span>` : ""}
                  </div>
                </div>
              `,
            )
            .join("")}
        </div>
        <div class="actions">
          <button class="btn success" type="button" data-approval-id="${approval.id}" data-decision="approved">Одобрить и создать видео</button>
          ${plan ? `<button class="btn" type="button" data-ai-video-action="regenerate-plan" data-scene-plan-id="${plan.id}">Перегенерировать сценарий</button>` : ""}
          <button class="btn danger" type="button" data-approval-id="${approval.id}" data-decision="rejected">Отклонить</button>
        </div>
      </article>
    `;
  }
  return `
    <article class="card review-card">
      <p class="review-kicker">Шаг 2 из 2 · Согласование ролика</p>
      <h2>Готовый ролик</h2>
      ${finalVideo
        ? `<div class="video-frame"><video controls preload="metadata" src="${escapeAttr(finalVideo.download_url)}"></video></div>`
        : "<p class='muted'>Финальное видео не найдено среди файлов.</p>"}
      ${approval.preview_payload?.caption ? `<p style="margin-top:12px">${escapeHtml(approval.preview_payload.caption)}</p>` : ""}
      ${approval.preview_payload?.cta ? `<p class="muted">${escapeHtml(approval.preview_payload.cta)}</p>` : ""}
      <div class="actions">
        <button class="btn success" type="button" data-approval-id="${approval.id}" data-decision="approved">Одобрить и отправить в публикацию</button>
        <button class="btn danger" type="button" data-approval-id="${approval.id}" data-decision="rejected">Отклонить</button>
      </div>
    </article>
  `;
}

function renderScenario(plan, pendingApproval) {
  if (!plan) return "<p class='section-title'>Сценарий</p><p class='muted small'>Сценарий появится после анализа фото.</p>";
  const isReviewing = pendingApproval?.stage === "content";
  return `
    <p class="section-title">Сценарий</p>
    <div class="chip-row">
      <span class="chip ${statusTone(plan.status)}">${statusLabel(plan.status)}</span>
      <span class="chip">${plan.scenes.length} сцен</span>
      <span class="chip">${Number(plan.total_duration_sec)} сек</span>
      <span class="chip info">${escapeHtml(plan.metadata_json?.provider || "")}</span>
    </div>
    ${isReviewing
      ? "<p class='muted small' style='margin-top:10px'>Полный текст сцен — в блоке согласования выше.</p>"
      : `<div class="timeline" style="margin-top:10px">${plan.scenes
          .map((scene) => `<div class="evt"><span><strong>${scene.scene_number}.</strong> ${escapeHtml(scene.subtitle_text || scene.voice_text || "")}</span></div>`)
          .join("")}</div>`}
  `;
}

function renderDrafts(drafts) {
  if (!drafts.length) return "<p class='section-title'>Тексты</p><p class='muted small'>Подписи появятся после анализа фото.</p>";
  const platformNames = { instagram: "Instagram", vk: "ВКонтакте", yandex_maps: "Яндекс Карты" };
  return `
    <p class="section-title">Тексты для площадок</p>
    <div class="timeline">
      ${drafts
        .map(
          (draft) => `
            <div class="evt">
              <div>
                <span class="chip accent">${escapeHtml(platformNames[draft.platform] || draft.platform)}</span>
                <p style="margin:6px 0 0">${escapeHtml(draft.caption)}</p>
                ${draft.cta ? `<p class="muted small" style="margin:2px 0 0">${escapeHtml(draft.cta)}</p>` : ""}
              </div>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderPublications(tasks) {
  if (!tasks.length) return "<p class='section-title'>Публикации</p><p class='muted small'>Появятся после одобрения ролика.</p>";
  const platformNames = { instagram: "Instagram", vk: "ВКонтакте", yandex_maps: "Яндекс Карты" };
  return `
    <p class="section-title">Публикации</p>
    <div class="timeline">
      ${tasks
        .map((task) => {
          const result = task.results.at(-1);
          return `
            <div class="evt">
              <div>
                <span class="chip ${statusTone(task.status)}">${escapeHtml(platformNames[task.platform] || task.platform)} · ${statusLabel(task.status)}</span>
                ${result?.error_message ? `<p class="muted small">Ошибка: ${escapeHtml(result.error_message)}</p>` : ""}
                ${result?.remote_url ? `<p class="small"><a href="${escapeAttr(result.remote_url)}" target="_blank" rel="noreferrer">Открыть публикацию →</a></p>` : ""}
                ${task.status !== "published" ? `<p class="small" style="margin-top:6px"><button class="btn subtle" type="button" data-publication-id="${task.id}">Опубликовать</button></p>` : ""}
              </div>
            </div>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderTimeline(events) {
  return `
    <p class="section-title">История</p>
    <div class="timeline">
      ${events
        .slice(-8)
        .reverse()
        .map((event) => `<div class="evt"><span class="small"><strong>${escapeHtml(eventLabel(event.event_type))}</strong> <span class="muted">· ${formatDate(event.created_at)}</span></span></div>`)
        .join("")}
    </div>
  `;
}

function renderAssets(assets) {
  if (!assets.length) return "<p class='section-title'>Файлы</p><p class='muted small'>Файлов пока нет.</p>";
  const kindNames = { source_photo: "Исходное фото", video: "Видео", voice: "Озвучка", preview: "Превью", derived_image: "Изображение" };
  return `
    <p class="section-title">Файлы</p>
    <div class="tile-grid">
      ${assets
        .map(
          (asset) => `
            <div class="tile">
              <span class="chip">${escapeHtml(kindNames[asset.kind] || asset.kind)}</span>
              <span class="small" style="font-weight:600;word-break:break-all">${escapeHtml(asset.file_name)}</span>
              ${asset.duration_seconds ? `<span class="muted small">${Number(asset.duration_seconds)} сек</span>` : ""}
              <a class="small" href="${escapeAttr(asset.download_url)}" target="_blank" rel="noreferrer">Открыть →</a>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderTools(plan) {
  if (!plan) return "";
  return `
    <details class="tools">
      <summary>Инструменты (ручной перезапуск шагов)</summary>
      <div class="actions" style="margin-top:4px">
        <button class="btn subtle" type="button" data-ai-video-action="regenerate-plan" data-scene-plan-id="${plan.id}">Перегенерировать сценарий</button>
        <button class="btn subtle" type="button" data-ai-video-action="generate-scenes" data-scene-plan-id="${plan.id}">Сгенерировать сцены</button>
        <button class="btn subtle" type="button" data-ai-video-action="render-final" data-scene-plan-id="${plan.id}">Пересобрать финальное видео</button>
      </div>
      <div class="tile-grid">
        ${plan.scenes
          .map(
            (scene) => `
              <div class="tile">
                <span class="chip ${scene.status === "generated" ? "good" : ""}">Сцена ${scene.scene_number} · ${statusLabel(scene.status)}</span>
                <span class="muted small">${escapeHtml(scene.provider)}</span>
                <button class="btn subtle" type="button" data-ai-scene-id="${scene.id}">Перегенерировать сцену</button>
              </div>
            `,
          )
          .join("")}
      </div>
    </details>
  `;
}

function findFinalVideo(assets) {
  return (
    assets.find((asset) => asset.kind === "video" && asset.metadata_json?.provider === "ai-video-final-render") ||
    null
  );
}

function bindPipelineActions() {
  els.pipelineDetail.querySelectorAll("[data-approval-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
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
      if (action === "regenerate-plan") {
        await requestJson(`/api/v1/scene-plans/${scenePlanId}/regenerate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ reason: "Dashboard action" }),
        });
      } else if (action === "generate-scenes") {
        await requestJson(`/api/v1/scene-plans/${scenePlanId}/generate-scenes`, { method: "POST" });
      } else if (action === "render-final") {
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

/* ---------- orders ---------- */

async function loadOrders() {
  const payload = await requestJson("/api/v1/store/orders");
  renderOrders(payload.orders);
}

function renderOrders(orders) {
  if (!orders.length) {
    els.orders.innerHTML = "<div class='card empty'><p>Заказов пока нет.</p></div>";
    return;
  }
  els.orders.innerHTML = orders
    .map((order) => {
      const items = order.items_json.map((item) => `<li>${escapeHtml(item.title)} × ${item.quantity} — ${item.line_total} ₽</li>`).join("");
      const actions = orderStatuses
        .map((status) => `<button class="btn subtle" type="button" data-order-id="${order.id}" data-status="${status}">${statusLabel(status)}</button>`)
        .join("");
      return `
        <article class="card">
          <div class="order-head">
            <h3>${escapeHtml(order.customer_name)}</h3>
            <strong>${order.total_amount} ${escapeHtml(order.currency)}</strong>
          </div>
          <div class="order-meta">
            <span>${escapeHtml(order.customer_phone)}</span>
            <span>${escapeHtml(order.delivery_address)}</span>
            <span class="chip ${statusTone(order.status)}">${statusLabel(order.status)}</span>
            <span>${paymentLabel(order.payment_method)}</span>
          </div>
          <ul class="order-items">${items}</ul>
          <div class="actions">${actions}</div>
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

/* ---------- shared helpers ---------- */

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
  els.pipelineDetail.innerHTML = `<div class="card"><p>Ошибка: ${escapeHtml(error.message)}</p></div>`;
}

function statusLabel(status) {
  return {
    new: "Новый",
    queued: "В очереди",
    processing: "Генерация",
    needs_review: "Ждёт решения",
    completed: "Готово",
    failed: "Ошибка",
    pending: "Ожидает",
    dispatched: "Отправлено",
    approved: "Одобрено",
    rejected: "Отклонено",
    regenerate_requested: "На перегенерацию",
    confirmed: "Подтверждён",
    preparing: "Готовится",
    delivering: "В пути",
    cancelled: "Отменён",
    published: "Опубликовано",
    publishing: "Публикуется",
    scheduled: "Запланировано",
    draft: "Черновик",
    ready_for_render: "Готов к генерации",
    ready_for_review: "Готов к проверке",
    rendering: "Собирается",
    generated: "Готова",
  }[status] || status;
}

function statusTone(status) {
  if (["completed", "published", "approved", "generated", "confirmed"].includes(status)) return "good";
  if (["failed", "rejected", "cancelled"].includes(status)) return "bad";
  if (["needs_review", "pending", "dispatched", "ready_for_review"].includes(status)) return "warn";
  if (["processing", "publishing", "rendering", "queued"].includes(status)) return "info";
  return "";
}

function eventLabel(eventType) {
  return {
    "pipeline.started": "Конвейер запущен",
    "analysis.completed": "Фото проанализировано",
    "content_drafts.completed": "Тексты готовы",
    "scenario.ready_for_review": "Сценарий на согласовании",
    "scene_plan.created": "Сценарий создан",
    "scene_plan.regenerated": "Сценарий перегенерирован",
    "creative_render.completed": "Медиа сгенерировано",
    "approval.created": "Создана задача согласования",
    "approval.approved": "Одобрено",
    "approval.rejected": "Отклонено",
    "approval.dispatched": "Отправлено в Telegram",
    "video_stage.enqueued": "Генерация видео запущена",
    "video_stage.started": "Генерация видео началась",
    "ai_video_final.rendered": "Финальное видео собрано",
    "voice_asset.created": "Озвучка готова",
    "publication_tasks.ready": "Публикации подготовлены",
    "publication_task.created": "Задача публикации создана",
    "publication_task.enqueued": "Публикация в очереди",
    "publication_task.publishing": "Публикуется",
    "publication_task.published": "Опубликовано",
    "publication_task.failed": "Ошибка публикации",
    "upload.created": "Фото загружено",
    "upload.status_updated": "Статус обновлён",
  }[eventType] || eventType;
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
