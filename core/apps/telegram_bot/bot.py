import telebot



bot = telebot.TeleBot('6991307584:AAH3-fJH1FVuAP8xjCyU8iNudzRf-Wz1pew',parse_mode=None)


@bot.message_handler(commands= ['start'])
def command_handler(message: telebot.types.Message):
    text = f"""Добро пожаловать в бот комопании  W2W. Данный бот служит для оповещения о новых анкетах  коллабораций. Для получения более детальной информации о командах введите /help"""
    bot.reply_to(message,text)

@bot.message_handler(commands= ['help'])
def command_handler(message: telebot.types.Message):
    text = f"""Возможности"""
    bot.reply_to(message,text)




bot.polling(none_stop=True)