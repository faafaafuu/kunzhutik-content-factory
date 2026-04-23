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
from shared.enums import ApprovalStatus, ApprovalTrigger

logging.basicConfig(level=settings.log_level)
router = Router()


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer("Кунжутик approval bot активен.")


@router.message(F.text == "/pending")
async def pending(message: Message) -> None:
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
    finally:
        db.close()


@router.callback_query(F.data.startswith(("approve:", "reject:", "regenerate:")))
async def decision_callback(callback: CallbackQuery) -> None:
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
            actor=str(callback.from_user.id),
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


if __name__ == "__main__":
    asyncio.run(main())
