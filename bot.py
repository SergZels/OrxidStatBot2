from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from keyboards.client_keyboard import kbcl
from aiogram.types import ReplyKeyboardRemove
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.handler import CancelHandler
import conf 
from aiogram.dispatcher.middlewares import BaseMiddleware
from bd.bd import botBD
from loguru import logger

ADMIN_ID = conf.ADMIN_ID

bot = Bot(token=conf.TOKEN)#os.getenv('TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(bot,storage=storage)
botBD = botBD()
logger.add("debug.txt")

class FSMzap(StatesGroup):
    vuruhka = State()

class MidlWare(BaseMiddleware):
    async def on_process_update(self,update: types.Update,date: dict):
        #logger.debug(update)
        logger.debug(update.message.from_user.id)
        if update.message.from_user.id not in ADMIN_ID:
            logger.debug(f"Хтось лівий зайшов {update.message.from_user.id}")
            raise CancelHandler()
  
@dp.message_handler(commands=['start', 'help'],state= None)
async def send_welcome(message: types.Message):
    await message.reply("Вітаю! Щоб розпочати натисніть кнопку внизу!",reply_markup=kbcl )

@dp.message_handler(commands=['Внести_виручку'],state=None)
async def echo(message : types.Message):
    await FSMzap.vuruhka.set()
    await message.answer("Напишіть вашу виручку:",reply_markup=ReplyKeyboardRemove())

@dp.message_handler(commands=['Місяць'],state=None)
async def echo(message : types.Message):
    te=botBD.stat()
    doc = open('testplor.png', 'rb')
    await message.answer(te)
    await message.reply_photo(doc)
 
@dp.message_handler(content_types=[types.ContentType.TEXT],state=FSMzap.vuruhka)
async def get_pokaznik(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['viruhka'] = message.text
    logger.debug(f"Виручка - {message.text}")
    botBD.rec(data['viruhka'])
    await message.answer(f"Виручку {data['viruhka']}грн внесено!",reply_markup=kbcl)
    await state.finish()

@dp.message_handler()
async def echo(message : types.Message):
    if message.text == "Файл12":
        doc = open('debug.txt', 'rb')
        await message.reply_document(doc)
    else:
        await message.answer("Не розумію",reply_markup=kbcl)
    
print("Bot running")
dp.middleware.setup(MidlWare())
executor.start_polling(dp,skip_updates=True)