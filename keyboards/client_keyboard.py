from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


markup = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Оборот до обіду 💵"), KeyboardButton(text="Оборот після обіду 💶")],
        [KeyboardButton(text="Статистика за місяць 📊"), KeyboardButton(text="Видатки")],
        [KeyboardButton(text="Минулий місяць"), KeyboardButton(text="Рік")],
        [KeyboardButton(text="🌐 Веб-панель")],
    ],
    resize_keyboard=True,
)
