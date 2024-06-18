import telebot
from telebot import types

from .conf import TOKEN
from .utils import get_user_code
from .send_request import set_telegram_id_django

bot = telebot.TeleBot(f'{TOKEN}', parse_mode=None)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = get_user_code(message.text)
    telegram_id = message.from_user.id
    response = set_telegram_id_django(user_id, telegram_id)
    if response.status_code == 200:
        reply = 'Вы успешно подключились к боту'
    else:
        reply = 'Вы перешли по некорректной ссылке'
    bot.reply_to(message, reply)


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


# функция рассылки сообщений пользователям
async def send_notification(
        users: list[str],
        message: str
) -> None:
    for user in users:
        bot.send_message(chat_id=user, text=message)


# Позже добавлю код, для подключения к бд и получения списка пользователей для рассылки
# Добавлю возможность регистрации в боте для того, чтобы доступ к рассылке имели только зарегестрированные менеджеры компании
