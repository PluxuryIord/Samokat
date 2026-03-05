"""
AUTHOR CODE - V1N3R
TG: @v1n3r
Site Company: buy-bot.ru
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable, Dict, Any, Awaitable, Union
    from aiogram.types import InlineQuery

from bot.integrations import DB, DBStats
from bot.utils.telegram import topic_manager
from bot.handlers.client import client_main

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from cachetools import TTLCache
from datetime import datetime
from bot.utils import telegram as telegram

class UserData(BaseMiddleware):

    _cache: TTLCache[int, datetime] = TTLCache(
        maxsize=256,
        ttl=1.5,
    )

    def __init__(self):
        self.bot_chat = telegram.topic_manager.bot_group

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Union[Message, CallbackQuery, InlineQuery],
            data: Dict[str, Any]
    ) -> Any:
        # Update Stat
        if isinstance(event, Message):
            if event.chat.type in ['private', 'supergroup'] or event.chat.id == self.bot_chat:
                DBStats.Events.new('message', event.from_user.id, event.html_text)
            else:
                return False
        elif isinstance(event, CallbackQuery):
            if event.message.chat.type in ['private', 'supergroup'] or event.message.chat.id == self.bot_chat:
                DBStats.Events.new('callback', event.from_user.id, event.data)
            else:
                return False
        elif isinstance(event, InlineQuery):
            DBStats.Events.new('inline', event.from_user.id, event.query)

        # Check registration
        if event.from_user.id in self._cache:
            return False
        user_data = DB.User.select(mark=event.from_user.id)
        if not user_data:
            self._cache[event.from_user.id] = datetime.now()
            if isinstance(event, Message):
                await client_main.main_menu(event, event.from_user, user_data)
            else:
                await event.answer('❌ Не удалось обработать ваш запрос, повторите попытку',
                                   show_alert=True)
                await client_main.back_menu(event, data['state'])
            return False

        # Check change userdata
        if user_data.username != event.from_user.username or user_data.full_name != event.from_user.full_name:
            old_username = user_data.username if user_data.username else 'отсутствует'
            old_full_name = user_data.full_name
            DB.User.update(mark=event.from_user.id, username=event.from_user.username,
                           full_name=event.from_user.full_name)
            user_data.username, user_data.full_name = event.from_user.username, event.from_user.full_name
            username = event.from_user.username if event.from_user.username else 'отсутствует'
            await topic_manager.send_message(
                user_data.thread_id,
                '<b>🔔Пользователь сменил ник или имя\n\n'
                f'Отображаемое имя: <s>{old_full_name}</s> -> <code>{event.from_user.full_name}</code>\n'
                f'Ник: <s>{old_username}</s> -> <code>{username}</code></b>')

        # Add handler params
        data['user_data'] = user_data
        data['user'] = event.from_user
        if await data['state'].get_state():
            storage = await data['state'].get_data()
            if 'menu_id' in storage:
                data['menu_id'] = storage['menu_id']
        return await handler(event, data)
