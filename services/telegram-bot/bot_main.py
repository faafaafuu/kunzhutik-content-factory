import asyncio
import logging
from uuid import UUID

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.approval_task import ApprovalTask
from app.services.approvals import apply_approval_decision
from app.store.catalog import BUSINESS_PROFILE, CATEGORIES, MENU_ITEMS
from shared.enums import ApprovalStatus, ApprovalTrigger

logging.basicConfig(level=settings.log_level)
router = Router()


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
    if await reject_if_forbidden(message=message):
        return

    mode = "открытый многопользовательский режим" if settings.telegram_open_access else "режим фиксированного approval-чата"
    await message.answer(
        f"{BUSINESS_PROFILE['brand_name']} bot активен.\n"
        f"Режим: {mode}.\n"
        "Команды: /menu, /contacts, /pending."
    )


@router.message(F.text == "/contacts")
async def contacts(message: Message) -> None:
    if await reject_if_forbidden(message=message):
        return

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
    if await reject_if_forbidden(message=message):
        return

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
    await message.answer("\n".join(lines))


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
                f"ApprovalTask {task.id}\nСтатус: {task.status.value}\nUpload: {task.upload_id}",
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


if __name__ == "__main__":
    asyncio.run(main())
