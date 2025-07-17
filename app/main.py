import asyncio

import uvicorn
from environs import Env
from fastapi import FastAPI

from app.app_factory import create_app
from app.app_logger import logger


async def main():
    """
    Асинхронный запуск FastAPI-приложения с lifespan.
    Это безопасный и чистый способ запуска при наличии async инициализации.
    """
    app: FastAPI = await create_app()

    env = Env()
    env.read_env(".env")
    elena_targetova_bot_port = env.int("ELENA_TARGETOVA_BOT_PORT")
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=elena_targetova_bot_port,
        log_level="info",
        reload=False  # Включи True в разработке (если не в Docker)
    )

    server = uvicorn.Server(config)
    logger.info("Запуск микросервиса")
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
