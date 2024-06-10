import asyncio
import json
from redis import asyncio as aioredis
from asgiref.sync import sync_to_async

from telegram_bot.conf import (
    REDIS_USER,
    REDIS_PASS,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_BOT_DB,
)
from telegram_bot.handlers import send_notification
from .handlers import bot


async def main():
    async def bot_polling():
        await sync_to_async(bot.polling)(none_stop=True)

    async def sub_redis():
        redis = await aioredis.Redis.from_url(
            (f'redis://{REDIS_USER}:'
             f'{REDIS_PASS}@'
             f'{REDIS_HOST}:'
             f'{REDIS_PORT}/'
             f'{REDIS_BOT_DB}')
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

    await asyncio.gather(bot_polling(), sub_redis())


if __name__ == "__main__":
    asyncio.run(main())
