import asyncio
import json
import logging
import os
import random
import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = "7296978470:AAFJSKyDEn32_vKHBTsNW1jvyGRtHhCkRVc"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DATA_FILE = "users.json"
user_data = {}
pending_captcha = {}

# --- Загрузка и сохранение ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_data, f)

user_data = load_data()

# --- Главное меню ---
def main_menu(user_id):
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="💰 Баланс", callback_data="balance")
    keyboard.button(text="⛏️ Майнинг", callback_data="mine")
    keyboard.button(text="👥 Рефералка", callback_data="ref")
    keyboard.button(text="🛒 Купить майнера", callback_data="buy_miner")
    return keyboard.as_markup()

# --- Капча ---
async def send_captcha(user_id, message, referrer_id=None):
    a = random.randint(1, 5)
    b = random.randint(1, 5)
    answer = a + b
    options = [answer, answer + 1, answer - 1]
    random.shuffle(options)

    pending_captcha[str(user_id)] = {
        "answer": answer,
        "referrer_id": referrer_id
    }

    kb = InlineKeyboardBuilder()
    for opt in options:
        kb.button(text=str(opt), callback_data=f"captcha:{opt}")

    await message.answer(
        f"🤖 Подтвердите, что вы не бот:\nСколько будет {a} + {b}?",
        reply_markup=kb.as_markup()
    )

# --- Обработка капчи ---
@dp.callback_query(F.data.startswith("captcha:"))
async def handle_captcha(callback: CallbackQuery):
    user_id = str(callback.from_user.id)
    selected = int(callback.data.split(":")[1])

    if user_id not in pending_captcha:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("⚠️ Капча не найдена. Введите /start заново.", reply_markup=main_menu(user_id))
        return

    correct = pending_captcha[user_id]["answer"]

    if selected == correct:
        ref_id = pending_captcha[user_id]["referrer_id"]
        del pending_captcha[user_id]

        if user_id not in user_data:
            user_data[user_id] = {
                "balance": 0,
                "status": "idle",
                "invited_by": None,
                "referrals": [],
                "miner_until": None
            }

        if ref_id and user_id != ref_id and user_data[user_id]["invited_by"] is None:
            user_data[user_id]["invited_by"] = ref_id
            user_data[user_id]["balance"] += 50

            if ref_id not in user_data:
                user_data[ref_id] = {
                    "balance": 0,
                    "status": "idle",
                    "invited_by": None,
                    "referrals": [],
                    "miner_until": None
                }

            user_data[ref_id]["referrals"].append(user_id)
            user_data[ref_id]["balance"] += 35

        save_data()

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("✅ Капча пройдена! Добро пожаловать!", reply_markup=main_menu(user_id))
        await callback.message.answer(
            "🚫 *Правила проекта Kivo:*\n\n"
            "🔸 Запрещены фейковые аккаунты, боты и любая форма накрутки.\n"
            "🔸 Один человек — один аккаунт.\n"
            "🔸 Нарушители будут *заблокированы без предупреждения*.\n\n"
            "📢 Участвуйте честно и уважайте других.",
            parse_mode="Markdown",
            reply_markup=main_menu(user_id)
        )
    else:
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer("❌ Неверно. Попробуйте снова: /start", reply_markup=main_menu(user_id))

    await callback.answer()

# --- Команда /start ---
@dp.message(F.text.startswith("/start"))
async def start(message: Message):
    user_id = str(message.from_user.id)
    args = message.text.split()
    referrer_id = str(args[1]) if len(args) > 1 else None
    await send_captcha(user_id, message, referrer_id)

# --- Баланс ---
@dp.callback_query(F.data == "balance")
async def show_balance(callback):
    user_id = str(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    balance = user_data.get(user_id, {}).get("balance", 0)
    await callback.message.answer(f"💰 Ваш текущий баланс: {balance} Kivo", reply_markup=main_menu(user_id))
    await callback.answer()

# --- Майнинг ---
@dp.callback_query(F.data == "mine")
async def start_mining(callback):
    user_id = str(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)

    status = user_data.get(user_id, {}).get("status", "idle")
    if status == "mining":
        await callback.message.answer("⛏️ Уже майните! Подождите...", reply_markup=main_menu(user_id))
        await callback.answer()
        return

    now = datetime.datetime.utcnow().timestamp()
    miner_until = user_data.get(user_id, {}).get("miner_until")

    if not miner_until or now > miner_until:
        reward = random.randint(1, 5)
        user_data[user_id]["balance"] += reward
        save_data()
        await callback.message.answer(f"⛏️ Вы намайнили {reward} Kivo без майнера.", reply_markup=main_menu(user_id))
        await callback.answer()
        return

    await callback.message.answer("🚀 Майнинг начался... ⛏️", reply_markup=main_menu(user_id))
    user_data[user_id]["status"] = "mining"
    save_data()

    await bot.send_chat_action(callback.message.chat.id, ChatAction.TYPING)
    await asyncio.sleep(3)

    reward = 350
    user_data[user_id]["balance"] += reward
    user_data[user_id]["status"] = "idle"
    save_data()

    await callback.message.answer(f"✅ Вы намайнили {reward} Kivo!", reply_markup=main_menu(user_id))
    await callback.answer()

# --- Рефералка ---
@dp.callback_query(F.data == "ref")
async def show_ref(callback):
    user_id = str(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    bot_username = (await bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    referrals = user_data.get(user_id, {}).get("referrals", [])
    total_refs = len(referrals)

    await callback.message.answer(
        f"👥 Ваша реферальная ссылка:\n{ref_link}\n\n"
        f"🏱 Приглашённые получают: 50 Kivo\n"
        f"👤 Вы получаете: 35 Kivo за каждого друга\n"
        f"📈 Приглашено: {total_refs} человек(а).",
        reply_markup=main_menu(user_id)
    )
    await callback.answer()

# --- Купить майнера ---
@dp.callback_query(F.data == "buy_miner")
async def show_miner_options(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Купить майнера (30 дней)", callback_data="buy_30")
    await callback.message.answer("🛒 Выберите майнера для покупки:", reply_markup=keyboard.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "buy_30")
async def handle_buy_30(callback: CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        "✅ Вы выбрали: *30 дней / 19.5 USDT*\n\n"
        "💳 Чтобы оплатить, используйте форму ниже:\n\n"
        "<b>Ссылка для оплаты:</b> <a href=\"https://nowpayments.io/payment/?iid=6238356498\">Нажмите здесь</a>",
        parse_mode="HTML",
        reply_markup=main_menu(str(callback.from_user.id))
    )
    await callback.answer()

# --- Неизвестные команды ---
@dp.message()
async def unknown(message: Message):
    user_id = str(message.from_user.id)
    await message.answer("❓ Неизвестная команда. Используйте меню ниже:", reply_markup=main_menu(user_id))

# --- Запуск ---
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
