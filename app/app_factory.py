import logging
from contextlib import asynccontextmanager

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv
from environs import Env
from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.routes import register_routes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Загрузка переменных окружения
    load_dotenv()
    env = Env()
    env.read_env(".env")

    # Настройка логики ошибок
    # setup_exception_handlers(app)


    bot_token = env.str("BOT_TOKEN")

    # Конфигурация переменных
    manager_ids = env.list("MANAGER_IDS", subcast=int)
    admin_ids = env.list("ADMIN_IDS", subcast=int)
    app.state.admin_ids = admin_ids
    app.state.manager_ids = manager_ids
    app.state.bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    app.state.elena_targetova_bot_url = f"http://{env.str('ELENA_TARGETOVA_BOT_URL')}:{env.int('ELENA_TARGETOVA_BOT_PORT')}"

    register_routes(app)

    logger.info("Lifespan init completed")
    yield
    logger.info("Lifespan shutdown started")


async def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, root_path="/api")


    app.add_middleware(
        CORSMiddleware,
        allow_origins=[# "http://localhost:8005",
                       # "http://127.0.0.1:8005",
                       "https://elena_targetova.ru",
                       "https://www.elena_targetova.ru"],
        allow_credentials=True,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )
    app.add_middleware(SlowAPIMiddleware)

    return app
