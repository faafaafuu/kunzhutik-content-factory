import asyncio
import hashlib
import hmac
import json
import logging
from urllib.parse import urlencode
from uuid import UUID

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.approval_task import ApprovalTask
from app.models.store_order import StoreOrder
from app.services.approvals import apply_approval_decision
from app.services.notifications import ORDER_STATUS_LABELS, build_order_status_keyboard
from app.services.storefront import build_order_number, update_store_order_status
from app.store.catalog import BUSINESS_PROFILE, CATEGORIES, MENU_ITEMS
from shared.enums import ApprovalStatus, ApprovalTrigger

logging.basicConfig(level=settings.log_level)
router = Router()


def storefront_url() -> str:
    return f"{(settings.telegram_approval_base_url or settings.app_base_url).rstrip('/')}/tg"


def storefront_keyboard(user=None) -> InlineKeyboardMarkup:
    url = storefront_url()
    if user:
        url = _with_signed_telegram_profile(url, user)
    if url.startswith("https://"):
        button = InlineKeyboardButton(text="Открыть заказ в Telegram", web_app=WebAppInfo(url=url))
    else:
        button = InlineKeyboardButton(text="Открыть заказ", url=url)
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def is_allowed_user(user_id: int) -> bool:
    allowed_user_ids = settings.telegram_allowed_user_ids
    if not allowed_user_ids:
        return True
    return str(user_id) in allowed_user_ids


async def reject_if_forbidden(message: Message | None = None, callback: CallbackQuery | None = None) -> bool:
    user_id = callback.from_user.id if callback else message.from_user.id
    if is_allowed_user(user_id):
        return False

    text = "Доступ к approval-функциям бота ограничен allowlist."
    if callback:
        await callback.answer(text, show_alert=True)
    if message:
        await message.answer(text)
    return True


@router.message(CommandStart())
async def start(message: Message) -> None:
    mode = "открытый многопользовательский режим" if settings.telegram_open_access else "режим фиксированного approval-чата"
    await message.answer(
        f"{BUSINESS_PROFILE['brand_name']} bot активен.\n"
        f"Режим: {mode}.\n"
        "Команды: /menu, /contacts.\n"
        "Нажмите кнопку ниже, чтобы открыть меню и оформить заказ.",
        reply_markup=storefront_keyboard(message.from_user),
    )


@router.message(F.text == "/contacts")
async def contacts(message: Message) -> None:
    await message.answer(
        f"{BUSINESS_PROFILE['brand_name']}\n"
        f"{BUSINESS_PROFILE['city']}, {BUSINESS_PROFILE['address']}\n"
        f"Телефон: {BUSINESS_PROFILE['phone']}\n"
        f"График: {BUSINESS_PROFILE['hours']}\n\n"
        f"Яндекс.Карты: {BUSINESS_PROFILE['map_url']}\n"
        f"Instagram: {BUSINESS_PROFILE['instagram_url']}\n"
        f"VK: {BUSINESS_PROFILE['vk_url']}"
    )


@router.message(F.text == "/menu")
async def menu(message: Message) -> None:
    category_titles = {category["id"]: category["title"] for category in CATEGORIES}
    lines = [f"Меню {BUSINESS_PROFILE['brand_name']}:"]
    for category in CATEGORIES[:6]:
        items = [item for item in MENU_ITEMS if item["category_id"] == category["id"]][:4]
        if not items:
            continue
        lines.append("")
        lines.append(category_titles[category["id"]])
        for item in items:
            lines.append(f"- {item['title']} — {item['price']} ₽, {item['weight']}")
    lines.append("")
    lines.append("Полное меню доступно на сайте.")
    await message.answer("\n".join(lines), reply_markup=storefront_keyboard(message.from_user))


@router.message(F.text == "/orders")
async def orders(message: Message) -> None:
    if await reject_if_forbidden(message=message):
        return

    db: Session = SessionLocal()
    try:
        active_orders = (
            db.query(StoreOrder)
            .filter(StoreOrder.status.in_(["new", "confirmed", "preparing", "delivering"]))
            .order_by(StoreOrder.created_at.desc())
            .limit(8)
            .all()
        )
        if not active_orders:
            await message.answer("Активных заказов нет.")
            return

        for order in active_orders:
            await message.answer(
                _format_store_order_message(order),
                reply_markup=build_order_status_keyboard(str(order.id)),
            )
    finally:
        db.close()


@router.message(F.web_app_data)
async def web_app_data(message: Message) -> None:
    try:
        payload = json.loads(message.web_app_data.data)
    except (TypeError, json.JSONDecodeError):
        return
    if payload.get("type") == "store_order_created" and payload.get("order_number"):
        await message.answer(f"Заказ {payload['order_number']} принят. Кунжутик уже передал его оператору.")


def _with_signed_telegram_profile(url: str, user) -> str:
    if not settings.telegram_bot_token:
        return url
    payload = {
        "tg_id": str(user.id),
        "tg_username": user.username or "",
        "tg_first_name": user.first_name or "",
        "tg_last_name": user.last_name or "",
    }
    payload["tg_sig"] = _sign_telegram_profile(payload)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(payload)}"


def _sign_telegram_profile(payload: dict[str, str]) -> str:
    message = "\n".join(
        [
            payload.get("tg_id", ""),
            payload.get("tg_username", ""),
            payload.get("tg_first_name", ""),
            payload.get("tg_last_name", ""),
        ]
    )
    return hmac.new(settings.telegram_bot_token.encode(), message.encode(), hashlib.sha256).hexdigest()


@router.message(F.text == "/pending")
async def pending(message: Message) -> None:
    if await reject_if_forbidden(message=message):
        return

    if not settings.telegram_open_access and settings.telegram_approval_chat_id:
        if str(message.chat.id) != settings.telegram_approval_chat_id:
            await message.answer("Этот бот принимает approval только в настроенном чате.")
            return

    db: Session = SessionLocal()
    try:
        tasks = (
            db.query(ApprovalTask)
            .filter(ApprovalTask.status.in_([ApprovalStatus.pending, ApprovalStatus.dispatched]))
            .order_by(ApprovalTask.created_at.desc())
            .limit(5)
            .all()
        )
        if not tasks:
            await message.answer("Ожидающих задач нет.")
            return
        for task in tasks:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="Approve", callback_data=f"approve:{task.id}"),
                        InlineKeyboardButton(text="Reject", callback_data=f"reject:{task.id}"),
                        InlineKeyboardButton(text="Regenerate", callback_data=f"regenerate:{task.id}"),
                    ]
                ]
            )
            await message.answer(
                _format_approval_task_message(task),
                reply_markup=keyboard,
            )
        if settings.telegram_open_access:
            await message.answer("Открытый режим включён: решения из этого чата доступны всем пользователям бота.")
    finally:
        db.close()


@router.callback_query(F.data.startswith(("approve:", "reject:", "regenerate:")))
async def decision_callback(callback: CallbackQuery) -> None:
    if await reject_if_forbidden(callback=callback):
        return

    action, approval_task_id = callback.data.split(":", maxsplit=1)
    decision_map = {
        "approve": "approved",
        "reject": "rejected",
        "regenerate": "regenerate_requested",
    }
    db: Session = SessionLocal()
    try:
        task = db.query(ApprovalTask).filter(ApprovalTask.id == UUID(approval_task_id)).first()
        if not task:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        apply_approval_decision(
            db=db,
            task=task,
            decision=decision_map[action],
            actor=_format_actor(callback),
            note="Telegram callback",
            via=ApprovalTrigger.telegram,
        )
        await callback.answer(f"Решение сохранено: {decision_map[action]}")
        await callback.message.edit_text(f"ApprovalTask {approval_task_id}\nРешение: {decision_map[action]}")
    finally:
        db.close()


@router.callback_query(F.data.startswith("order_status:"))
async def order_status_callback(callback: CallbackQuery) -> None:
    if await reject_if_forbidden(callback=callback):
        return

    try:
        _, order_id, status = callback.data.split(":", maxsplit=2)
    except ValueError:
        await callback.answer("Некорректная команда", show_alert=True)
        return

    if status not in ORDER_STATUS_LABELS:
        await callback.answer("Неподдерживаемый статус", show_alert=True)
        return

    db: Session = SessionLocal()
    try:
        order = update_store_order_status(db, UUID(order_id), status, actor=_format_actor(callback))
        await callback.answer(f"Статус: {ORDER_STATUS_LABELS[status]}")
        if callback.message:
            await callback.message.edit_text(
                _format_store_order_message(order),
                reply_markup=build_order_status_keyboard(str(order.id)),
            )
    finally:
        db.close()


async def main() -> None:
    if not settings.telegram_bot_token:
        logging.getLogger(__name__).warning("TELEGRAM_BOT_TOKEN is empty; bot will not start")
        return
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


def _format_actor(callback: CallbackQuery) -> str:
    user = callback.from_user
    username = f"@{user.username}" if user.username else "no-username"
    return f"telegram:{user.id}:{username}"


def _format_store_order_message(order: StoreOrder) -> str:
    item_lines = "\n".join(f"- {item['title']} × {item['quantity']}" for item in order.items_json)
    status_label = ORDER_STATUS_LABELS.get(order.status, order.status)
    comment_line = f"\n\nКомментарий: {order.comment}" if order.comment else ""
    return (
        f"Заказ {build_order_number(order)}\n"
        f"Статус: {status_label}\n"
        f"Клиент: {order.customer_name}\n"
        f"Телефон: {order.customer_phone}\n"
        f"Адрес: {order.delivery_address}\n"
        f"Время: {order.delivery_slot or 'как можно скорее'}\n"
        f"Оплата: {order.payment_method}\n"
        f"Сумма: {order.total_amount} {order.currency}\n\n"
        f"{item_lines}"
        f"{comment_line}"
    )


def _format_approval_task_message(task: ApprovalTask) -> str:
    payload = task.preview_payload or {}
    lines = [
        f"ApprovalTask {task.id}",
        f"Статус: {task.status.value}",
        f"Upload: {task.upload_id}",
        f"Блюдо: {payload.get('dish_name', 'без названия')}",
        "",
    ]
    for draft in (payload.get("drafts") or [])[:4]:
        lines.append(f"[{draft.get('platform')}/{draft.get('kind')}]")
        lines.append(str(draft.get("caption") or ""))
        if draft.get("cta"):
            lines.append(f"CTA: {draft['cta']}")
        lines.append("")
    return "\n".join(lines).strip()


if __name__ == "__main__":
    asyncio.run(main())
