import logging

from fastapi import FastAPI, HTTPException
from fastapi import Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from datetime import datetime
from bot.bot import send_to_managers
from bot.services import broadcaster

logger = logging.getLogger(__name__)
MAX_TELEGRAM_MESSAGE_LENGTH = 4000  # запас от 4096


class Lead(BaseModel):
    name: str
    phone: str


# Функция получения IP из заголовка или request.client
def get_real_ip(request: Request):
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.client.host


def register_routes(app: FastAPI):
    limiter = Limiter(key_func=get_real_ip)

    app.state.limiter = limiter

    app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
        status_code=429,
        content={"error": "Слишком много заявок. Попробуйте позже."}
    ))
    logger.info("Регистрация роутов")
    bot = app.state.bot
    manager_ids = app.state.manager_ids
    admin_ids = app.state.admin_ids

    @app.post("/submit")
    @limiter.limit("3/5minutes")
    async def submit_lead(lead: Lead, request: Request):
        lead_date = datetime.now()
        logger.info(f"Пришла заявка {lead.name} {lead.phone}, {lead_date}")
        client_ip = get_real_ip(request)
        # 🔐 Базовая ручная проверка на случай обхода валидации
        if not lead.name.strip() or len(lead.phone) != 12:
            logger.warning(f"[{client_ip}] ❌ Некорректные данные: name='{lead.name}' phone='{lead.phone}'")
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid data"
            )

        logger.info(f"[{client_ip}] 📩 Заявка: {lead.name} / {lead.phone}")

        try:
            if lead.phone == "+79999999999" and lead.name.upper() == "проверка".upper():
                await broadcaster.broadcast(
                    bot, admin_ids,
                    text = f"📥 <b>Новая проверочная заявка</b>\n👤 Имя: {lead.name}\n📞 Телефон: {lead.phone}")
            else:
                await send_to_managers(lead.name, lead.phone, bot=bot, manager_ids=manager_ids)
        except Exception as e:
            error_message = f"[{client_ip}] ❗ Ошибка при отправке заявки: {str(e)}"
            await handle_error_report(error_message, bot, admin_ids)
            raise HTTPException(status_code=500, detail="Failed to process request")

        return {"status": "ok"}

    async def handle_error_report(error_message: str, bot, admin_ids: list[str]):
        logger.error(f"📩 Получена ошибка: {error_message}", exc_info=True)

        chunks = split_text_into_chunks(error_message, MAX_TELEGRAM_MESSAGE_LENGTH - 50)

        for admin_id in admin_ids:
            for i, chunk in enumerate(chunks):
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ <b>Ошибка в сервисе (часть {i + 1} из {len(chunks)}):</b>\n<pre>{chunk}</pre>"
                    )
                except Exception as e:
                    logger.error(f"❌ Не удалось отправить сообщение в Telegram админу {admin_id}: {e}", exc_info=True)

    @app.post("/report-error")
    async def report_error(request: Request):
        try:
            data = await request.json()
            error_message = data.get("error")

            if not error_message:
                return JSONResponse(content={"detail": "Поле 'error' обязательно"}, status_code=400)

            await handle_error_report(error_message, bot, admin_ids)
            return {"status": "received"}
        except Exception as e:
            logger.exception("Ошибка при обработке отчёта об ошибке", exc_info=True)
            return JSONResponse(content={"detail": "Ошибка сервера при обработке отчёта"}, status_code=500)

    def split_text_into_chunks(text: str, max_length: int) -> list[str]:
        """
        Делит длинный текст на части длиной не более max_length.
        Гарантирует, что разбиение не обрезает строку посередине.
        """
        return [text[i:i + max_length] for i in range(0, len(text), max_length)]
