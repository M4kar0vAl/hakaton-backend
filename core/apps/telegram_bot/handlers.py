import telebot
from telebot import types
from bot import bot
from dotenv import load_dotenv


@bot.message_handler(commands=['start', 'main', 'hello'])
def start_handler(message: telebot.types.Message):
    text = (
        f"Привет {message.chat.first_name}! Добро пожаловать "
        f"в бот комопании  W2W. Данный бот служит для оповещения "
        f"о новых анкетах  коллабораций. Для получения более "
        f"детальной информации о командах введите команду /help"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['help'])
def help_handler(message: telebot.types.Message):
    text = f"""Возможности:"""
    bot.reply_to(message, text)


@bot.message_handler(commands=['site', 'website'])
def open_site(message: telebot.types.Message):
    button = types.InlineKeyboardMarkup()
    button.add(
        types.InlineKeyboardButton(
            'Перейти на сайт', url='https://google.com'
        )
    )  # будет добавлен url нашего приложения
    bot.reply_to(message, 'Перейти нас сайт', reply_markup=button)


@bot.message_handler()
def hello(message: telebot.types.Message):
    if message.text.lower() == 'hello' or message.text.lower() == 'привет':
        bot.reply_to(message, 'Привет!')


@bot.message_handler()
def spam(spam_message, id_list):
    for user_id in id_list:
        bot.send_message(chat_id=user_id, text=spam_message)

# Позже добавлю код, для подключения к бд и получения списка пользователей для рассылки
# Добавлю возможность регистрации в боте для того, чтобы доступ к рассылке имели только зарегестрированные менеджеры компании
