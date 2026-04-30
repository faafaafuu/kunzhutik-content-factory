const container = document.getElementById("orders");
const statuses = ["confirmed", "preparing", "delivering", "completed", "cancelled"];

loadOrders().catch((error) => {
  console.error(error);
  container.innerHTML = "<p>Не удалось загрузить заказы.</p>";
});

async function loadOrders() {
  const response = await fetch("/api/v1/store/orders");
  const payload = await response.json();
  renderOrders(payload.orders);
}

function renderOrders(orders) {
  if (!orders.length) {
    container.innerHTML = "<div class='order-card'><p>Заказов пока нет.</p></div>";
    return;
  }

  container.innerHTML = orders
    .map((order) => {
      const items = order.items_json.map((item) => `<li>${item.title} × ${item.quantity} — ${item.line_total} ₽</li>`).join("");
      const actions = statuses
        .map((status) => `<button type="button" data-order-id="${order.id}" data-status="${status}">${label(status)}</button>`)
        .join("");
      return `
        <article class="order-card">
          <div class="order-head">
            <div>
              <p class="eyebrow">Заказ</p>
              <h3>${order.customer_name}</h3>
            </div>
            <strong>${order.total_amount} ${order.currency}</strong>
          </div>
          <div class="order-meta">
            <span>${order.customer_phone}</span>
            <span>${order.delivery_address}</span>
            <span>Статус: <strong>${label(order.status)}</strong></span>
            <span>Оплата: <strong>${paymentLabel(order.payment_method)}</strong></span>
          </div>
          <ul class="order-items">${items}</ul>
          <div class="status-actions">${actions}</div>
        </article>
      `;
    })
    .join("");

  container.querySelectorAll("[data-order-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const orderId = button.dataset.orderId;
      const status = button.dataset.status;
      await fetch(`/api/v1/store/orders/${orderId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      await loadOrders();
    });
  });
}

function label(status) {
  return {
    new: "Новый",
    confirmed: "Подтвержден",
    preparing: "Готовится",
    delivering: "В пути",
    completed: "Завершен",
    cancelled: "Отменен",
  }[status] || status;
}

function paymentLabel(method) {
  return {
    cash: "Наличными",
    card_on_delivery: "Картой при получении",
    online: "Онлайн",
  }[method] || method;
}
