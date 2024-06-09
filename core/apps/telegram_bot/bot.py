import telebot
from telebot import types
import

bot = telebot.TeleBot(f'{TOKEN}',parse_mode=None)

bot.polling(none_stop=True)