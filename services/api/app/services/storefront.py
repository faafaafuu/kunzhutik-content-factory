from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.store_order import StoreOrder
from app.services.notifications import notify_new_order
from app.store.catalog import BUSINESS_PROFILE, CATEGORIES, FEATURES, MENU_ITEMS, PROMOS, STORE_CURRENCY

CATALOG_BY_ID = {item["id"]: item for item in MENU_ITEMS}


def get_storefront_payload() -> dict:
    return {
        "brand_name": BUSINESS_PROFILE["brand_name"],
        "business": BUSINESS_PROFILE,
        "currency": STORE_CURRENCY,
        "categories": CATEGORIES,
        "features": FEATURES,
        "promos": PROMOS,
        "items": MENU_ITEMS,
    }


def create_store_order(
    db: Session,
    *,
    customer_name: str,
    customer_phone: str,
    delivery_address: str,
    delivery_slot: str | None,
    payment_method: str,
    comment: str | None,
    customer_profile: dict | None,
    items: list[dict],
) -> tuple[StoreOrder, str]:
    normalized_items: list[dict] = []
    total_amount = Decimal("0.00")

    for requested_item in items:
        catalog_item = CATALOG_BY_ID.get(requested_item["item_id"])
        if not catalog_item:
            raise HTTPException(status_code=400, detail=f"Unknown item: {requested_item['item_id']}")
        quantity = requested_item["quantity"]
        line_total = Decimal(str(catalog_item["price"])) * quantity
        normalized_items.append(
            {
                "item_id": catalog_item["id"],
                "title": catalog_item["title"],
                "price": catalog_item["price"],
                "quantity": quantity,
                "line_total": float(line_total),
                "category_id": catalog_item["category_id"],
            }
        )
        total_amount += line_total

    order = StoreOrder(
        customer_name=customer_name.strip(),
        customer_phone=customer_phone.strip(),
        delivery_address=delivery_address.strip(),
        delivery_slot=delivery_slot.strip() if delivery_slot else None,
        payment_method=payment_method,
        comment=comment.strip() if comment else None,
        status="new",
        currency=STORE_CURRENCY,
        total_amount=total_amount.quantize(Decimal("0.01")),
        items_json=normalized_items,
        source_json={
            "channel": "web_storefront",
            "customer_profile": _sanitize_customer_profile(customer_profile),
        },
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    order_number = build_order_number(order)
    notify_new_order(order_number, build_order_notification_summary(order))
    return order, order_number


def build_order_number(order: StoreOrder) -> str:
    return f"KUN-{order.created_at.strftime('%d%m')}-{str(order.id)[:8].upper()}"


def list_store_orders(db: Session) -> list[StoreOrder]:
    return db.query(StoreOrder).order_by(StoreOrder.created_at.desc()).all()


def update_store_order_status(db: Session, order_id, status: str) -> StoreOrder:
    order = db.query(StoreOrder).filter(StoreOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = status
    db.commit()
    db.refresh(order)
    return order


def build_order_notification_summary(order: StoreOrder) -> str:
    item_lines = "\n".join(f"- {item['title']} × {item['quantity']}" for item in order.items_json)
    customer_profile = order.source_json.get("customer_profile") if isinstance(order.source_json, dict) else None
    profile_line = _format_customer_profile(customer_profile)
    return (
        f"Заведение: {BUSINESS_PROFILE['brand_name']}\n"
        f"Адрес: {BUSINESS_PROFILE['address']}\n"
        f"Клиент: {order.customer_name}\n"
        f"Телефон: {order.customer_phone}\n"
        f"{profile_line}"
        f"Адрес доставки: {order.delivery_address}\n"
        f"Оплата: {order.payment_method}\n"
        f"Сумма: {order.total_amount} {order.currency}\n\n"
        f"{item_lines}"
    )


def _sanitize_customer_profile(customer_profile: dict | None) -> dict:
    if not customer_profile:
        return {}
    allowed_keys = {"provider", "id", "username", "first_name", "last_name", "language_code"}
    return {
        key: str(value)[:160]
        for key, value in customer_profile.items()
        if key in allowed_keys and value is not None
    }


def _format_customer_profile(customer_profile: dict | None) -> str:
    if not customer_profile:
        return ""
    provider = customer_profile.get("provider")
    username = customer_profile.get("username")
    profile_id = customer_profile.get("id")
    parts = [str(provider)] if provider else []
    if username:
        parts.append(f"@{username}")
    if profile_id:
        parts.append(f"id:{profile_id}")
    return f"Профиль: {' '.join(parts)}\n" if parts else ""
