const DEMO_UPLOAD_ID = "60a63bfc-1cd4-48a2-bf5d-5b6c692ccef0";

const state = {
  menu: null,
  cart: new Map(),
  demoAssets: [],
};

const els = {
  topnav: document.getElementById("topnav"),
  features: document.getElementById("features"),
  promos: document.getElementById("promos"),
  categoryTabs: document.getElementById("category-tabs"),
  menuGrid: document.getElementById("menu-grid"),
  demoGrid: document.getElementById("demo-grid"),
  cartDrawer: document.getElementById("cart-drawer"),
  cartItems: document.getElementById("cart-items"),
  cartTotal: document.getElementById("cart-total"),
  cartCount: document.getElementById("cart-count"),
  cartPill: document.getElementById("cart-pill"),
  cartClose: document.getElementById("cart-close"),
  checkoutForm: document.getElementById("checkout-form"),
  checkoutStatus: document.getElementById("checkout-status"),
};

bootstrap().catch((error) => {
  console.error(error);
  els.checkoutStatus.textContent = "Не удалось загрузить storefront.";
});

async function bootstrap() {
  const [menuResponse, demoResponse] = await Promise.all([
    fetch("/api/v1/store/menu"),
    fetch(`/api/v1/uploads/${DEMO_UPLOAD_ID}/assets`),
  ]);

  state.menu = await menuResponse.json();
  state.demoAssets = demoResponse.ok ? await demoResponse.json() : { assets: [] };

  renderTopnav();
  renderFeatures();
  renderPromos();
  renderCategories();
  renderMenu();
  renderDemo();
  renderCart();
  bindEvents();
}

function bindEvents() {
  els.cartPill.addEventListener("click", () => els.cartDrawer.classList.add("open"));
  els.cartClose.addEventListener("click", () => els.cartDrawer.classList.remove("open"));
  els.checkoutForm.addEventListener("submit", submitOrder);
}

function renderTopnav() {
  const links = [
    { href: "#demo", label: "Demo" },
    { href: "#menu", label: "Меню" },
    { href: "#delivery", label: "Сервис" },
  ];
  els.topnav.innerHTML = links.map((link) => `<a href="${link.href}">${link.label}</a>`).join("");
}

function renderFeatures() {
  els.features.innerHTML = state.menu.features
    .map(
      (feature) => `
        <article>
          <strong>${feature.title}</strong>
          <p>${feature.text}</p>
        </article>
      `,
    )
    .join("");
}

function renderPromos() {
  els.promos.innerHTML = `
    <p class="eyebrow">Current Offers</p>
    <div class="promo-list">
      ${state.menu.promos
        .map(
          (promo) => `
            <article>
              <strong>${promo.title}</strong>
              <p>${promo.text}</p>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderCategories() {
  els.categoryTabs.innerHTML = state.menu.categories.map((category) => `<a href="#cat-${category.id}">${category.title}</a>`).join("");
}

function renderMenu() {
  const grouped = new Map(state.menu.categories.map((category) => [category.id, []]));
  for (const item of state.menu.items) {
    grouped.get(item.category_id)?.push(item);
  }

  els.menuGrid.innerHTML = state.menu.categories
    .map((category) => {
      const cards = (grouped.get(category.id) || []).map(renderItemCard).join("");
      return `
        <section id="cat-${category.id}">
          <div class="section-head">
            <p class="eyebrow">${category.title}</p>
          </div>
          <div class="menu-group-grid">${cards}</div>
        </section>
      `;
    })
    .join("");

  els.menuGrid.querySelectorAll("[data-add-item]").forEach((button) => {
    button.addEventListener("click", () => addToCart(button.dataset.addItem));
  });
}

function renderItemCard(item) {
  return `
    <article class="menu-card" style="--card-accent:${item.accent}">
      <div class="menu-art"></div>
      <div class="menu-meta">
        <span class="tag">${item.tag}</span>
        ${item.badge ? `<span class="menu-badge">${item.badge}</span>` : ""}
      </div>
      <div class="menu-copy">
        <h3>${item.title}</h3>
        <p>${item.description}</p>
      </div>
      <div class="menu-footer">
        <div>
          <strong>${formatPrice(item.price)}</strong>
          <small>${item.weight}</small>
        </div>
        <button class="add-button" type="button" data-add-item="${item.id}">Добавить</button>
      </div>
    </article>
  `;
}

function renderDemo() {
  const assets = Array.isArray(state.demoAssets.assets) ? state.demoAssets.assets : [];
  const videos = assets.filter((asset) => asset.kind === "video");
  const previews = new Map(assets.filter((asset) => asset.kind === "preview").map((asset) => [asset.draft_kind, asset]));

  if (!videos.length) {
    els.demoGrid.innerHTML = "<article class='demo-card'><div class='demo-copy'><p>Demo assets пока не готовы.</p></div></article>";
    return;
  }

  els.demoGrid.innerHTML = videos
    .map((video) => {
      const preview = previews.get(video.draft_kind);
      return `
        <article class="demo-card">
          <div class="demo-video">
            <video controls muted playsinline preload="metadata" poster="${preview?.download_url || ""}">
              <source src="${video.download_url}" type="video/mp4" />
            </video>
          </div>
          <div class="demo-copy">
            <div class="demo-meta">
              <span>${labelDraft(video.draft_kind)}</span>
              <span>${labelPlatform(video.platform)}</span>
            </div>
            <h3>${demoTitle(video.draft_kind)}</h3>
            <p class="section-note">Актуальный render pipeline: mascот overlay, вертикальный motion и отдельная композиция под тип social-креатива.</p>
            <div class="demo-actions">
              <a class="demo-link" href="${video.download_url}" target="_blank" rel="noreferrer">Открыть mp4</a>
              ${preview ? `<a class="demo-link" href="${preview.download_url}" target="_blank" rel="noreferrer">Открыть preview</a>` : ""}
            </div>
          </div>
        </article>
      `;
    })
    .join("");
}

function addToCart(itemId) {
  const current = state.cart.get(itemId) || 0;
  state.cart.set(itemId, current + 1);
  renderCart();
  els.cartDrawer.classList.add("open");
}

function renderCart() {
  const items = state.menu ? state.menu.items.filter((item) => state.cart.has(item.id)) : [];
  const totalCount = [...state.cart.values()].reduce((sum, quantity) => sum + quantity, 0);
  const total = items.reduce((sum, item) => sum + item.price * state.cart.get(item.id), 0);
  els.cartCount.textContent = String(totalCount);
  els.cartTotal.textContent = formatPrice(total);

  if (!items.length) {
    els.cartItems.innerHTML = "<p class='form-note'>Корзина пустая. Добавь позиции из меню, чтобы оформить заказ.</p>";
    return;
  }

  els.cartItems.innerHTML = items
    .map(
      (item) => `
        <div class="cart-line">
          <div>
            <strong>${item.title}</strong>
            <small>${item.weight}</small>
          </div>
          <div>
            <strong>${state.cart.get(item.id)} × ${formatPrice(item.price)}</strong>
          </div>
        </div>
      `,
    )
    .join("");
}

async function submitOrder(event) {
  event.preventDefault();
  const items = [...state.cart.entries()].map(([item_id, quantity]) => ({ item_id, quantity }));
  if (!items.length) {
    els.checkoutStatus.textContent = "Сначала добавь что-нибудь в корзину.";
    return;
  }

  const formData = new FormData(els.checkoutForm);
  const payload = {
    customer_name: formData.get("customer_name"),
    customer_phone: formData.get("customer_phone"),
    delivery_address: formData.get("delivery_address"),
    delivery_slot: formData.get("delivery_slot"),
    payment_method: formData.get("payment_method"),
    comment: formData.get("comment"),
    items,
  };

  els.checkoutStatus.textContent = "Отправляю заказ...";

  const response = await fetch("/api/v1/store/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Ошибка оформления заказа" }));
    els.checkoutStatus.textContent = typeof error.detail === "string" ? error.detail : "Не удалось оформить заказ.";
    return;
  }

  const result = await response.json();
  state.cart.clear();
  els.checkoutForm.reset();
  renderCart();
  els.checkoutStatus.textContent = `Заказ ${result.order_number} сохранён.`;
}

function formatPrice(price) {
  return new Intl.NumberFormat("ru-RU").format(price) + " ₽";
}

function labelDraft(value) {
  return {
    post: "Post Video",
    story: "Story Video",
    news: "Local News Video",
  }[value] || value;
}

function labelPlatform(value) {
  return {
    instagram: "Instagram",
    vk: "VK",
    yandex_maps: "Yandex Maps",
  }[value] || value;
}

function demoTitle(value) {
  return {
    post: "Продуктовый ролик с hero-подачей",
    story: "Вертикальная story-версия для быстрого просмотра",
    news: "Спокойный локальный формат для карточек и новостей",
  }[value] || "Demo video";
}
