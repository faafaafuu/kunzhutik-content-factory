from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app.core.config import settings

logger = logging.getLogger(__name__)


def notify_new_order(order_number: str, order_summary: str) -> None:
    if not settings.telegram_bot_token:
        return

    recipient_ids = sorted(settings.telegram_allowed_user_ids)
    if not recipient_ids:
        return

    try:
        asyncio.run(_send_order_notifications(recipient_ids, order_number, order_summary))
    except Exception:
        logger.exception("Failed to send Telegram notifications for order %s", order_number)


async def _send_order_notifications(recipient_ids: list[str], order_number: str, order_summary: str) -> None:
    bot = Bot(token=settings.telegram_bot_token)
    try:
        for recipient_id in recipient_ids:
            await bot.send_message(
                chat_id=recipient_id,
                text=f"Новый заказ {order_number}\n\n{order_summary}",
            )
    finally:
        await bot.session.close()
