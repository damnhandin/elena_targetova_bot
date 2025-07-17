import logging
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi import Request
from pydantic import BaseModel, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

from bot.bot import send_to_managers
from bot.services import broadcaster

logger = logging.getLogger(__name__)
MAX_TELEGRAM_MESSAGE_LENGTH = 4000  # запас от 4096


class Lead(BaseModel):
    name: str
    contactMethod: Literal["telegram", "email", "phone"]
    contactValue: str
    message: str = ""

    @field_validator("contactValue")
    def validate_contact_value(cls, value, info):
        method = info.data.get("contactMethod")
        if method == "email":
            if "@" not in value or "." not in value:
                raise ValueError("Неверный Email")
        elif method == "phone":
            if not value.startswith("+7") or len(value) != 12:
                raise ValueError("Неверный номер телефона")
        elif method == "telegram":
            if len(value) < 2:
                raise ValueError("Неверный Telegram username")
        return value


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
        logger.info(f"Пришла заявка {lead.name} {lead.contactValue}, {lead_date}")
        client_ip = get_real_ip(request)
        logger.info(f"[{client_ip}] 📩 Заявка: {lead.name} / {lead.contactValue}")

        logger.info((
            f"📥 Заявка от {client_ip} | Время: {lead_date}"
            f"Имя: {lead.name}"
            f"Способ связи: {lead.contactMethod}"
            f"Контакт: {lead.contactValue}"
            f"Сообщение: {lead.message}"))

        try:
            if lead.name.upper() == "проверка".upper():
                await broadcaster.broadcast(
                    bot, admin_ids,
                    text=(
                        f"📥 <b>Новая проверочная заявка</b>\n"
                        f"👤 <b>Имя:</b> {lead.name}\n"
                        f"📡 <b>Способ связи:</b> {lead.contactMethod}\n"
                        f"📲 <b>Контакт:</b> {lead.contactValue}\n"
                        f"💬 <b>Сообщение:</b> {lead.message or '—'}"
                    ))
            else:
                await send_to_managers(
                    text=(
                        f"📥 <b>Новая заявка</b>\n"
                        f"👤 <b>Имя:</b> {lead.name}\n"
                        f"📡 <b>Способ связи:</b> {lead.contactMethod}\n"
                        f"📲 <b>Контакт:</b> {lead.contactValue}\n"
                        f"💬 <b>Сообщение:</b> {lead.message or '—'}"
                    ), bot=bot, manager_ids=manager_ids)
        except Exception as e:
            error_message = f"[{client_ip}] ❗ Ошибка при отправке заявки: {str(e)}"
            logger.exception(f"Ошибка: {e}", exc_info=True)
            await handle_error_report(error_message, bot, admin_ids)
            raise HTTPException(status_code=500, detail="Failed to process request")

        return {"status": "ok"}
        #
        # lead_date = datetime.now()
        # client_ip = request.client.host  # или свой get_real_ip()
        #
        # # Пример логирования
        # print(f"[{client_ip}] Новая заявка: {lead.name} через {lead.contactMethod}: {lead.contactValue}")
        #
        # # Пример отправки данных дальше:
        # try:
        #     await send_to_managers(lead.name, lead.contactValue)
        # except Exception as e:
        #     print(f"Ошибка: {e}")
        #     raise HTTPException(status_code=500, detail="Ошибка отправки")
        #
        # return {"status": "ok"}

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
