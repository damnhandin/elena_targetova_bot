import logging
from typing import List

from aiogram import Bot

logger = logging.getLogger(__name__)

async def send_to_managers(text: str, bot: Bot, manager_ids: List[int]):
    for manager_id in manager_ids:
        try:
            await bot.send_message(manager_id, text)
        except Exception as e:
            logger.exception(f"❌ Ошибка отправки менеджеру {manager_id}: {e}", exc_info=True)
            continue
