from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


markup = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Виручка до обіду 💵"), KeyboardButton(text="Виручка після обіду 💶")],
        [KeyboardButton(text="Статистика за місяць 📊"), KeyboardButton(text="Видатки")],
        [KeyboardButton(text="Минулий місяць"), KeyboardButton(text="Рік")],
        [KeyboardButton(text="🌐 Веб-панель")],
    ],
    resize_keyboard=True,
)
