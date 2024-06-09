import telebot
import json
from redis import asyncio as aioredis

from conf import (
    TOKEN,
    REDIS_USER,
    REDIS_PASS,
    REDIS_HOST,
    REDIS_PORT,
)

bot = telebot.TeleBot(f'{TOKEN}',parse_mode=None)


async def main():
    def run_telebot():
        bot.polling(none_stop=True)

    async def sub_redis():
        redis = await aioredis.Redis.from_url(
            (f'redis://{REDIS_USER}:'
             f'{REDIS_PASS}@'
             f'{REDIS_HOST}:'
             f'{REDIS_PORT}/3')
        )
        pub = redis.pubsub()
        await pub.subscribe('organizer')
        async for msg in pub.listen():
            data = msg.get('data', None)
            if type(data) is bytes:  # при первичном подключении в data будет число
                data_dict = json.loads(data.decode())
                message = data_dict.get('message')
                users = data_dict.get('users')
                await send_notification(users, message)