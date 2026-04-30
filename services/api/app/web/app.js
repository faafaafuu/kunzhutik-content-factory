const state = {
  menu: null,
  activeCategoryId: null,
  cart: new Map(),
};

const els = {
  topnav: document.getElementById("topnav"),
  features: document.getElementById("features"),
  heroTags: document.getElementById("hero-tags"),
  brandName: document.getElementById("brand-name"),
  brandAddress: document.getElementById("brand-address"),
  mapLink: document.getElementById("map-link"),
  contactAddress: document.getElementById("contact-address"),
  contactPhone: document.getElementById("contact-phone"),
  contactHours: document.getElementById("contact-hours"),
  contactLinks: document.getElementById("contact-links"),
  categoryTabs: document.getElementById("category-tabs"),
  activeCategoryTitle: document.getElementById("active-category-title"),
  menuGrid: document.getElementById("menu-grid"),
  cartDrawer: document.getElementById("cart-drawer"),
  cartReview: document.getElementById("cart-review"),
  cartItems: document.getElementById("cart-items"),
  cartTotal: document.getElementById("cart-total"),
  cartCount: document.getElementById("cart-count"),
  cartPill: document.getElementById("cart-pill"),
  cartBar: document.getElementById("cart-bar"),
  cartBarCount: document.getElementById("cart-bar-count"),
  cartBarTotal: document.getElementById("cart-bar-total"),
  openCart: document.getElementById("open-cart"),
  cartClose: document.getElementById("cart-close"),
  checkoutNext: document.getElementById("checkout-next"),
  checkoutBack: document.getElementById("checkout-back"),
  checkoutForm: document.getElementById("checkout-form"),
  checkoutStatus: document.getElementById("checkout-status"),
  authStatus: document.getElementById("auth-status"),
  cartTitle: document.getElementById("cart-title"),
  stepCart: document.getElementById("step-cart"),
  stepCheckout: document.getElementById("step-checkout"),
};

bootstrap().catch((error) => {
  console.error(error);
  els.menuGrid.innerHTML = "<p class='empty-state'>Не удалось загрузить меню.</p>";
});

async function bootstrap() {
  const response = await fetch("/api/v1/store/menu", { cache: "no-store" });
  state.menu = await response.json();
  state.activeCategoryId = state.menu.categories[0]?.id || null;

  setupTelegramTheme();
  renderBusinessProfile();
  renderTopnav();
  renderHeroTags();
  renderFeatures();
  renderCategories();
  renderMenu();
  renderCart();
  bindEvents();
}

function bindEvents() {
  els.cartPill.addEventListener("click", openCartReview);
  els.openCart.addEventListener("click", openCartReview);
  els.cartClose.addEventListener("click", closeCart);
  els.checkoutNext.addEventListener("click", showCheckout);
  els.checkoutBack.addEventListener("click", showCartReview);
  els.checkoutForm.addEventListener("submit", submitOrder);
  document.querySelectorAll("[data-auth]").forEach((button) => {
    button.addEventListener("click", () => applyQuickAuth(button.dataset.auth));
  });
}

function setupTelegramTheme() {
  if (!window.Telegram?.WebApp) {
    return;
  }
  window.Telegram.WebApp.ready();
  window.Telegram.WebApp.expand();
  prefillTelegramUser({ silent: true });
}

function renderTopnav() {
  const links = [
    { href: "#menu", label: "Меню" },
    { href: "#contacts", label: "Контакты" },
  ];
  els.topnav.innerHTML = links.map((link) => `<a href="${link.href}">${link.label}</a>`).join("");
}

function renderHeroTags() {
  const business = state.menu.business || {};
  const tags = [
    business.hours || "ежедневно с 10:00 до 22:00",
    business.phone || "+7 (916) 498-39-09",
    "заказ в Telegram",
  ];
  els.heroTags.innerHTML = tags.map((tag) => `<span>${tag}</span>`).join("");
}

function renderBusinessProfile() {
  const business = state.menu.business || {};
  const links = [
    business.map_url ? { href: business.map_url, label: "Карты" } : null,
    business.instagram_url ? { href: business.instagram_url, label: "Instagram" } : null,
    business.vk_url ? { href: business.vk_url, label: "VK" } : null,
  ].filter(Boolean);

  els.brandName.textContent = state.menu.brand_name || business.brand_name || "Кунжут";
  els.brandAddress.textContent = business.address || "ул. Дзержинского, 18";
  els.contactAddress.textContent = `${business.city || "Солнечногорск"}, ${business.address || "ул. Дзержинского, 18"}`;
  els.contactPhone.textContent = business.phone || "";
  els.contactHours.textContent = business.hours || "";

  if (business.map_url) {
    els.mapLink.href = business.map_url;
  }

  els.contactLinks.innerHTML = links
    .map((link) => `<a href="${link.href}" target="_blank" rel="noreferrer">${link.label}</a>`)
    .join("");
}

function renderFeatures() {
  els.features.innerHTML = state.menu.features
    .map(
      (feature) => `
        <article>
          <strong>${feature.title}</strong>
          <span>${feature.text}</span>
        </article>
      `,
    )
    .join("");
}

function renderCategories() {
  els.categoryTabs.innerHTML = state.menu.categories
    .map(
      (category) => `
        <button class="${category.id === state.activeCategoryId ? "active" : ""}" type="button" data-category="${category.id}">
          ${category.title}
        </button>
      `,
    )
    .join("");

  els.categoryTabs.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeCategoryId = button.dataset.category;
      renderCategories();
      renderMenu();
    });
  });
}

function renderMenu() {
  const category = state.menu.categories.find((item) => item.id === state.activeCategoryId);
  const items = state.menu.items.filter((item) => item.category_id === state.activeCategoryId);
  els.activeCategoryTitle.textContent = category?.title || "Меню";

  els.menuGrid.innerHTML = items.map(renderItemCard).join("");
  els.menuGrid.querySelectorAll("[data-add-item]").forEach((button) => {
    button.addEventListener("click", () => addToCart(button.dataset.addItem));
  });
}

function renderItemCard(item) {
  return `
    <article class="menu-card" style="--card-accent:${item.accent}">
      <div class="menu-art">
        ${item.image_url ? `<img src="${item.image_url}" alt="${item.title}" loading="lazy" />` : ""}
      </div>
      <div class="menu-copy">
        <div class="menu-meta">
          <span>${item.tag}</span>
          ${item.badge ? `<strong>${item.badge}</strong>` : ""}
        </div>
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

function addToCart(itemId) {
  state.cart.set(itemId, (state.cart.get(itemId) || 0) + 1);
  renderCart();
  pulseCartBar();
}

function changeQuantity(itemId, delta) {
  const next = (state.cart.get(itemId) || 0) + delta;
  if (next <= 0) {
    state.cart.delete(itemId);
  } else {
    state.cart.set(itemId, next);
  }
  renderCart();
}

function renderCart() {
  const items = getCartItems();
  const totalCount = [...state.cart.values()].reduce((sum, quantity) => sum + quantity, 0);
  const total = getCartTotal(items);

  els.cartCount.textContent = String(totalCount);
  els.cartTotal.textContent = formatPrice(total);
  els.cartBarCount.textContent = formatItemsCount(totalCount);
  els.cartBarTotal.textContent = formatPrice(total);
  els.cartBar.hidden = totalCount === 0;
  els.checkoutNext.disabled = totalCount === 0;

  if (!items.length) {
    els.cartItems.innerHTML = "<p class='empty-state'>Корзина пустая. Добавьте блюдо из меню.</p>";
    return;
  }

  els.cartItems.innerHTML = items
    .map(
      ({ item, quantity }) => `
        <div class="cart-line">
          <div>
            <strong>${item.title}</strong>
            <small>${formatPrice(item.price)} · ${item.weight}</small>
          </div>
          <div class="qty-control">
            <button type="button" data-qty="${item.id}" data-delta="-1">−</button>
            <span>${quantity}</span>
            <button type="button" data-qty="${item.id}" data-delta="1">+</button>
          </div>
        </div>
      `,
    )
    .join("");

  els.cartItems.querySelectorAll("[data-qty]").forEach((button) => {
    button.addEventListener("click", () => changeQuantity(button.dataset.qty, Number(button.dataset.delta)));
  });
}

function openCartReview() {
  showCartReview();
  els.cartDrawer.classList.add("open");
  els.cartDrawer.setAttribute("aria-hidden", "false");
}

function closeCart() {
  els.cartDrawer.classList.remove("open");
  els.cartDrawer.setAttribute("aria-hidden", "true");
}

function showCartReview() {
  els.cartTitle.textContent = "Проверьте корзину";
  els.cartReview.hidden = false;
  els.checkoutForm.hidden = true;
  els.stepCart.classList.add("active");
  els.stepCheckout.classList.remove("active");
}

function showCheckout() {
  if (!state.cart.size) {
    return;
  }
  els.cartTitle.textContent = "Оформление";
  els.cartReview.hidden = true;
  els.checkoutForm.hidden = false;
  els.stepCart.classList.remove("active");
  els.stepCheckout.classList.add("active");
  prefillTelegramUser();
}

function applyQuickAuth(provider) {
  if (provider === "telegram") {
    const didPrefill = prefillTelegramUser();
    const text = didPrefill
      ? "Telegram-данные подставлены в заказ."
      : "Telegram не передал данные. Откройте сайт кнопкой из бота.";
    els.authStatus.textContent = text;
    els.checkoutStatus.textContent = text;
    return;
  }
  if (provider === "phone") {
    els.checkoutForm.customer_phone.focus();
    els.authStatus.textContent = "Телефон Telegram/VK/Google не отдают автоматически. Введите номер вручную.";
    els.checkoutStatus.textContent = "Введите телефон, оператор свяжется для подтверждения.";
    return;
  }
  els.authStatus.textContent = `${provider.toUpperCase()} требует серверную OAuth-интеграцию. Сейчас доступен Telegram WebApp-профиль.`;
  els.checkoutStatus.textContent = els.authStatus.textContent;
}

function prefillTelegramUser(options = {}) {
  const user = window.Telegram?.WebApp?.initDataUnsafe?.user;
  if (!user) {
    if (!options.silent && els.authStatus) {
      els.authStatus.textContent = "Telegram-данные недоступны в обычном браузере.";
    }
    return false;
  }
  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  if (name && !els.checkoutForm.customer_name.value) {
    els.checkoutForm.customer_name.value = name;
  }
  if (els.authStatus) {
    const username = user.username ? `@${user.username}` : `id ${user.id}`;
    els.authStatus.textContent = `Подтянут Telegram-профиль: ${username}.`;
  }
  return true;
}

async function submitOrder(event) {
  event.preventDefault();
  const items = [...state.cart.entries()].map(([item_id, quantity]) => ({ item_id, quantity }));
  if (!items.length) {
    els.checkoutStatus.textContent = "Сначала добавьте блюдо в корзину.";
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
    customer_profile: getCustomerProfile(),
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
  els.checkoutStatus.textContent = `Заказ ${result.order_number} принят.`;

  if (window.Telegram?.WebApp) {
    window.Telegram.WebApp.HapticFeedback?.notificationOccurred("success");
    window.Telegram.WebApp.MainButton.setText(`Заказ ${result.order_number} принят`);
    window.Telegram.WebApp.MainButton.show();
  }
}

function getCustomerProfile() {
  const user = window.Telegram?.WebApp?.initDataUnsafe?.user;
  if (!user) {
    return null;
  }
  return {
    provider: "telegram",
    id: user.id,
    username: user.username || null,
    first_name: user.first_name || null,
    last_name: user.last_name || null,
    language_code: user.language_code || null,
  };
}

function getCartItems() {
  if (!state.menu) {
    return [];
  }
  return state.menu.items
    .filter((item) => state.cart.has(item.id))
    .map((item) => ({ item, quantity: state.cart.get(item.id) }));
}

function getCartTotal(items) {
  return items.reduce((sum, { item, quantity }) => sum + item.price * quantity, 0);
}

function pulseCartBar() {
  els.cartBar.classList.remove("pulse");
  requestAnimationFrame(() => els.cartBar.classList.add("pulse"));
}

function formatPrice(price) {
  return new Intl.NumberFormat("ru-RU").format(price) + " ₽";
}

function formatItemsCount(count) {
  if (count % 10 === 1 && count % 100 !== 11) {
    return `${count} позиция`;
  }
  if ([2, 3, 4].includes(count % 10) && ![12, 13, 14].includes(count % 100)) {
    return `${count} позиции`;
  }
  return `${count} позиций`;
}
