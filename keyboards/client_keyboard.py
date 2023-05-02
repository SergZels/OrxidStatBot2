from aiogram.types import KeyboardButton, ReplyKeyboardMarkup



b1 = KeyboardButton("/Виручка_до_обіду")
b2 = KeyboardButton("/Виручка_після_обіду")
b3=KeyboardButton("/Стат_Місяць")
b4=KeyboardButton("/Стат_Рік")

kbcl = ReplyKeyboardMarkup(resize_keyboard=True)
kbcl.add(b1,b2).add(b3,b4)

markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)

markup.add(('Виручка до обіду 💵'), 'Виручка після обіду 💶').add('Статистика за місяць 📊','Видатки').add('Минулий місяць')