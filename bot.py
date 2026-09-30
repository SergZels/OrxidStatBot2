"""Telegram webhook for the Orxid statistics bot."""

import asyncio
import datetime
import os
from zoneinfo import ZoneInfo

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, ReplyKeyboardRemove
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from loguru import logger

from bd.bdnew import BotBDnew, Credet, Stat, db
from keyboards.client_keyboard import markup

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_IDS = {int(value) for value in os.environ["ADMIN_IDS"].split(",")}
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://orxid.in.ua/prod_orxmstat")
WEBHOOK_PATH = "/" + WEBHOOK_URL.split("/", 3)[-1].lstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET") or None
WEBAPP_PORT = int(os.getenv("PORT", "3004"))
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://192.168.1.10:3005/").rstrip("/") + "/"
KYIV = ZoneInfo("Europe/Kyiv")
reminder_task = None

router = Router()
dp = Dispatcher()
dp.include_router(router)


class RevenueAM(StatesGroup):
    amount = State()


class RevenuePM(StatesGroup):
    amount = State()


class Expense(StatesGroup):
    amount = State()
    description = State()


class AdminOnlyMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: types.Message, data: dict):
        if event.from_user and event.from_user.id in ADMIN_IDS:
            return await handler(event, data)
        logger.warning("Unauthorized user: {}", event.from_user.id if event.from_user else None)
        return None


router.message.middleware(AdminOnlyMiddleware())


@router.message(Command("start", "help"), StateFilter(None))
async def send_welcome(message: types.Message):
    await message.reply(
        "Вітаю! Щоб розпочати натисніть кнопку внизу!\n"
        f"Графіки: {DASHBOARD_URL} (доступно лише в локальній мережі).",
        reply_markup=markup,
    )


@router.message(F.text == "🌐 Веб-панель", StateFilter(None))
async def dashboard_link(message: types.Message):
    await message.answer(
        f"Панель із графіками: {DASHBOARD_URL}\n"
        "Відкрийте посилання з пристрою в локальній мережі.",
        reply_markup=markup,
    )


@router.message(F.text.in_({"Оборот до обіду 💵", "Виручка до обіду 💵"}), StateFilter(None))
async def cash_to_am(message: types.Message, state: FSMContext):
    await state.set_state(RevenueAM.amount)
    await message.answer("Напишіть оборот до обіду 💵:", reply_markup=ReplyKeyboardRemove())


@router.message(RevenueAM.amount, F.text)
async def save_am(message: types.Message, state: FSMContext, bot: Bot):
    BotBDnew.recAM(message.text)
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"Оборот {message.text} грн внесено!", reply_markup=markup)
    await state.clear()


@router.message(F.text.in_({"Оборот після обіду 💶", "Виручка після обіду 💶"}), StateFilter(None))
async def cash_after_pm(message: types.Message, state: FSMContext):
    await state.set_state(RevenuePM.amount)
    await message.answer("Напишіть оборот після обіду 💶:", reply_markup=ReplyKeyboardRemove())


@router.message(RevenuePM.amount, F.text)
async def save_pm(message: types.Message, state: FSMContext, bot: Bot):
    BotBDnew.recPM(message.text)
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"Оборот {message.text} грн внесено!", reply_markup=markup)
    await state.clear()


@router.message(F.text == "Видатки", StateFilter(None))
async def expense_start(message: types.Message, state: FSMContext):
    await state.set_state(Expense.amount)
    await message.answer("Напишіть суму:", reply_markup=ReplyKeyboardRemove())


@router.message(Expense.amount, F.text)
async def expense_amount(message: types.Message, state: FSMContext):
    await state.update_data(amount=message.text)
    await state.set_state(Expense.description)
    await message.answer("Опишіть за що саме:")


@router.message(Expense.description, F.text)
async def expense_description(message: types.Message, state: FSMContext):
    data = await state.get_data()
    BotBDnew.recCredet(data["amount"], message.text)
    await message.answer(f"Витрати {message.text} {data['amount']} внесено", reply_markup=markup)
    await state.clear()


async def send_month(message: types.Message, month: int, year: int):
    report, image = BotBDnew.statOfMonth(month=month, year=year)
    await message.answer(report)
    if image:
        await message.reply_photo(BufferedInputFile(image, filename="statistics.png"))


@router.message(F.text == "Статистика за місяць 📊", StateFilter(None))
async def current_month(message: types.Message):
    today = datetime.date.today()
    await send_month(message, today.month, today.year)


@router.message(F.text == "Минулий місяць", StateFilter(None))
async def previous_month(message: types.Message):
    first_day = datetime.date.today().replace(day=1)
    previous = first_day - datetime.timedelta(days=1)
    await send_month(message, previous.month, previous.year)


@router.message(F.text == "Рік", StateFilter(None))
async def year_statistics(message: types.Message):
    today = datetime.date.today()
    for month in range(1, today.month + 1):
        _, image = BotBDnew.statOfMonth(month=month, year=today.year)
        if image:
            await message.reply_photo(BufferedInputFile(image, filename=f"{month}.png"))
    await message.answer(BotBDnew.statAllYear(year=today.year))


@router.message(StateFilter(None))
async def echo(message: types.Message):
    await message.answer("Не розумію", reply_markup=markup)


async def on_startup(bot: Bot):
    global reminder_task
    await bot.set_webhook(
        WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        allowed_updates=dp.resolve_used_update_types(),
    )
    reminder_task = asyncio.create_task(reminder_loop(bot))
    logger.info("Webhook configured: {}", WEBHOOK_URL)


async def on_shutdown(**kwargs):
    if reminder_task:
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass


def next_reminder(now: datetime.datetime) -> datetime.datetime:
    for day_offset in range(8):
        day = now.date() + datetime.timedelta(days=day_offset)
        if day.weekday() >= 6:
            continue
        for hour in (12, 17):
            candidate = datetime.datetime.combine(
                day, datetime.time(hour, 50), tzinfo=KYIV
            )
            if candidate > now:
                return candidate
    raise RuntimeError("Could not find the next reminder")


async def reminder_loop(bot: Bot):
    while True:
        now = datetime.datetime.now(KYIV)
        scheduled = next_reminder(now)
        await asyncio.sleep(max(0, (scheduled - now).total_seconds()))
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, "Нагадування — запишіть оборот 💶!")
            except Exception:
                logger.exception("Failed to send reminder to {}", admin_id)


async def health(request: web.Request):
    return web.Response(text="ok")


def main():
    db.connect(reuse_if_open=True)
    db.create_tables([Stat, Credet])
    bot = Bot(token=TOKEN)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    app = web.Application()
    app.router.add_get("/health", health)
    SimpleRequestHandler(
        dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET
    ).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    web.run_app(app, host="0.0.0.0", port=WEBAPP_PORT)


if __name__ == "__main__":
    main()
