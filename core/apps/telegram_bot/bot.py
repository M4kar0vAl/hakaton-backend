import telebot
from telebot import types
from conf import TOKEN

bot = telebot.TeleBot(f'{TOKEN}',parse_mode=None)

bot.polling(none_stop=True)