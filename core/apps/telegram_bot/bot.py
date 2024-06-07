import telebot
import webbrowser
from conf import url

bot = telebot.TeleBot('6991307584:AAH3-fJH1FVuAP8xjCyU8iNudzRf-Wz1pew',parse_mode=None)


@bot.message_handler(commands= ['start','main','hello'])
def start_handler(message: telebot.types.Message):
    text = f"""Привет {message.chat.first_name}! Добро пожаловать в бот комопании  W2W. Данный бот служит для оповещения о новых анкетах  коллабораций. Для получения более детальной информации о командах введите команду /help"""
    bot.reply_to(message,text)

@bot.message_handler(commands= ['help'])
def help_handler(message: telebot.types.Message):
    text = f"""Возможности:"""
    bot.reply_to(message,text)

@bot.message_handler(commands = ['site','website'])
def open_site(message:telebot.types.Message):
    webbrowser.open(f'{url}')

@bot.message_handler()
def hello(message:telebot.types.Message):
    if message.text.lower() == 'hello' or message.text.lower() == 'привет':
        bot.reply_to(message, 'Привет!')

bot.polling(none_stop=True)