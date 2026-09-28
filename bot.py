from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from keyboards.client_keyboard import kbcl, markup
from aiogram.types import ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher import filters
import conf
import datetime
from aiogram.dispatcher.middlewares import BaseMiddleware
from bd.bdnew import BotBDnew
from loguru import logger
from aiogram.utils.executor import start_webhook

TEST_MODE = False

# if conf.VPS:
#     TEST_MODE = False

##------------------Блок ініціалізації-----------------##
if TEST_MODE:
    API_Token = conf.API_TOKEN_Test
else:
    API_Token = conf.TOKEN

ADMIN_ID = conf.ADMIN_ID
bot = Bot(token=API_Token)  # os.getenv('TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
botbdnew = BotBDnew()
logger.add("debug.txt")
# webhook settings
WEBHOOK_HOST = 'https://orxid.in.ua'
WEBHOOK_PATH = '/prod_orxmstat'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# webserver settings
WEBAPP_HOST = '0.0.0.0'  # or ip 127.0.0.1
WEBAPP_PORT = 3004


##--------------Машини станів----------------------------##
class FSMzapAM(StatesGroup):
    vuruhka = State()


class FSMzapPM(StatesGroup):
    vuruhka = State()


class FSMzapCredet(StatesGroup):
    cash = State()
    description = State()


##---------------------Midelware-------------------------------##
class MidlWare(BaseMiddleware):
    async def on_process_update(self, update: types.Update, date: dict):
        logger.debug(update)
        logger.debug(update.message.from_user.id)
        if update.message.from_user.id not in ADMIN_ID:
            logger.debug(f"Хтось лівий зайшов {update.message.from_user.id}")
            raise CancelHandler()


##-------------------handlers--------------------------------------##
@dp.message_handler(commands=['start', 'help'], state=None)
async def send_welcome(message: types.Message):
    await message.reply("Вітаю! Щоб розпочати натисніть кнопку внизу!", reply_markup=markup)


##--------------------------до обіду виручка------------------------##
# @dp.message_handler(commands=['Виручка_до_обіду'],state=None)
@dp.message_handler(filters.Text(equals="Виручка до обіду 💵"), state=None)
async def cash_toAM(message: types.Message):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    await FSMzapAM.vuruhka.set()
    await message.answer("Напишіть вашу обідню виручку💵:", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(content_types=[types.ContentType.TEXT], state=FSMzapAM.vuruhka)
async def f_cash(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    async with state.proxy() as data:
        data['viruhka'] = message.text
    logger.debug(f"Виручка - {message.text}")
    BotBDnew.recAM(data['viruhka'])
    await bot.send_message(conf.ADMIN_ULIA, f"Виручку {data['viruhka']}грн внесено!", reply_markup=markup)
    await bot.send_message(conf.ADMIN_SERG, f"Виручку {data['viruhka']}грн внесено!", reply_markup=markup)
    # await message.answer(f"Виручку {data['viruhka']}грн внесено!",reply_markup=markup)
    await state.finish()


##--------------------------після обіду виручка------------------------##
@dp.message_handler(filters.Text(equals="Виручка після обіду 💶"), state=None)
async def cash_afterPM(message: types.Message):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    await FSMzapPM.vuruhka.set()
    await message.answer("Напишіть вашу виручку в кінці дня:", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(content_types=[types.ContentType.TEXT], state=FSMzapPM.vuruhka)
async def get_pokaznik(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    async with state.proxy() as data:
        data['viruhka'] = message.text
    logger.debug(f"Виручка - {message.text}")
    BotBDnew.recPM(data['viruhka'])
    await bot.send_message(conf.ADMIN_ULIA, f"Виручку {data['viruhka']}грн внесено!", reply_markup=markup)
    await bot.send_message(conf.ADMIN_SERG, f"Виручку {data['viruhka']}грн внесено!", reply_markup=markup)
    # await message.answer(f"Виручку {data['viruhka']}грн внесено!",reply_markup=markup)
    await state.finish()


##--------------------------видатки-----------------------##
@dp.message_handler(filters.Text(equals="Видатки"), state=None)
async def credet(message: types.Message):
    await FSMzapCredet.cash.set()
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    await message.answer("Напишіть суму:", reply_markup=ReplyKeyboardRemove())


@dp.message_handler(content_types=[types.ContentType.TEXT], state=FSMzapCredet.cash)
async def getcash(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    async with state.proxy() as data:
        data['viruhka'] = message.text
    logger.debug(f"Витрати - {message.text}")
    await message.answer(f"Опишіть за що саме:")
    await FSMzapCredet.next()


@dp.message_handler(content_types=[types.ContentType.TEXT], state=FSMzapCredet.description)
async def description(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    async with state.proxy() as data:
        data['desr'] = message.text
    logger.debug(f"Опис - {message.text}")
    BotBDnew.recCredet(data['viruhka'], data["desr"])
    await message.answer(f"Витрати {data['desr']} {data['viruhka']} внесено", reply_markup=markup)
    await state.finish()


##----------------------Статистика------------------------##
@dp.message_handler(filters.Text(equals="Статистика за місяць 📊"), state=None)
async def month_statistic(message: types.Message):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    now = datetime.datetime.now()
    te = BotBDnew.statOfMonth(month=now.month, year=now.year)
    doc = open('testplor.png', 'rb')
    await message.answer(te)
    await message.reply_photo(doc)


@dp.message_handler(filters.Text(equals="Минулий місяць"), state=None)
async def month_statistic(message: types.Message):
    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    now = datetime.datetime.now()
    month = now.month
    year = now.year
    if month > 1:
        month = now.month - 1
    else:
        year = now.year - 1
        month =12

    te = BotBDnew.statOfMonth(month=month, year=year)
    doc = open('testplor.png', 'rb')
    await message.answer(te)
    await message.reply_photo(doc)


@dp.message_handler(filters.Text(equals="Рік"), state=None)
async def month_statistic(message: types.Message):
    now = datetime.datetime.now()
    month = now.month
    year = now.year
    for month in range(1, month + 1):
        await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
        te = BotBDnew.statOfMonth(month=month, year=year)
        try:
            doc = open('testplor.png', 'rb')
            # await message.answer(te)
            await message.reply_photo(doc)
        except:
            pass

    await bot.send_chat_action(chat_id=message.from_user.id, action="typing")
    te = BotBDnew.statAllYear(year=year)
    doc = open('testplor.png', 'rb')
    await message.answer(te)
    # await message.reply_photo(doc)


##----------------------------Різне----------------------##
@dp.message_handler()
async def echo(message: types.Message):
    if message.text == "Файл12":
        doc = open('debug.txt', 'rb')
        await message.reply_document(doc)
    elif message.text == "req":
        pass
    else:
        await message.answer("Не розумію", reply_markup=markup)


##-------------------Запуск бота-------------------------##
if TEST_MODE:
    print("Bot running")
    dp.middleware.setup(MidlWare())
    executor.start_polling(dp, skip_updates=True)
else:
    async def on_startup(dp):
        await bot.set_webhook(WEBHOOK_URL)
        logger.debug("Бот запущено")


    async def on_shutdown(dp):
        logger.debug('Зупиняюся..')
        await bot.delete_webhook()
        await dp.storage.close()
        await dp.storage.wait_closed()


    if __name__ == '__main__':
        dp.middleware.setup(MidlWare())
        start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )
