from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


b1 = KeyboardButton("/Внести_день")
b2 = KeyboardButton("/Внести_місяць")
b3=KeyboardButton("/Стат_Місяць")
b4=KeyboardButton("/Стат_Рік")

kbcl = ReplyKeyboardMarkup(resize_keyboard=True)
kbcl.add(b1,b2).add(b3,b4)