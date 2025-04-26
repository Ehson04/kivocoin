from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
import asyncio
import os

app = FastAPI()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

@app.get("/")
async def root():
    return {"message": "Bot is running"}

@dp.message()
async def echo(message: types.Message):
    await message.answer("Привет! Я работаю!")

async def start_bot():
    await dp.start_polling(bot)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(start_bot())
