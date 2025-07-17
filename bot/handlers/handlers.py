from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

echo_router = Router()


@echo_router.message(Command("get_my_id"))
async def echo(message: Message):
    await message.answer(f"Ваш ID: {message.from_user.id}")


@echo_router.message()
async def echo(message: Message):
    await message.answer("Бот сейчас работает только на приём заявок 💬")
