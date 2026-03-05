"""
AUTHOR CODE - V1N3R
TG: @v1n3r
Site Company: buy-bot.ru
"""
# Site Company: buy-bot.ru

from __future__ import annotations

from datetime import datetime, time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from bot.initialization import bot_texts

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery, Message
    from aiogram import Dispatcher
    from aiogram.fsm.context import FSMContext

import logging

from aiogram.exceptions import TelegramAPIError

from bot.handlers.client import client_main
from bot.integrations import DB
from bot.keyboards.admin import kb_admin_topic, kb_admin_support
from bot.utils import telegram as telegram
from bot.utils.announce_bot import bot
from bot.handlers.client.client_main import back_menu


async def not_handled_callback(call: CallbackQuery, state: FSMContext):
    logging.error(f'Not handled | DATA: {call.data} | State: {await state.get_state()}')
    await call.answer('🚫Произошла ошибка при нажатии кнопки, повторите попытку',
                      show_alert=True)
    await back_menu(call, state)

async def is_in_night_period():
    moscow_tz = ZoneInfo("Europe/Moscow")
    now = datetime.now(moscow_tz).time()
    start = time(19, 20)  # 19:20
    end = time(9, 40)     # 09:40

    # Если текущее время >= 19:20 ИЛИ <= 09:40 — значит ночь
    return now >= start or now <= end

async def not_handled_message(message: Message, state: FSMContext,
                              user_data: DB.User | None, album: list[Message] = False):
    forward_message = None
    if message.chat.type == 'private':
        if message.text and message.text.lower() in ['старт', 'перезапустить', 'перезапуск', 'начать',
                                                     'запустить', 'запуск', 'start']:
            return await client_main.main_menu(message, message.from_user, user_data, state)
        elif user_data:
            if message.reply_to_message:
                if message.reply_to_message.from_user.id == message.from_user.id:
                    message_data = DB.ForwardTopicMessages.select(
                        where=[
                            DB.ForwardTopicMessages.chat_id == message.from_user.id,
                            DB.ForwardTopicMessages.message_id == message.reply_to_message.message_id,
                            DB.ForwardTopicMessages.from_entity == 'user'
                        ])
                    if message_data:
                        forward_message = message_data.forward_message_id
                else:
                    message_data = DB.ForwardTopicMessages.select(
                        where=[
                            DB.ForwardTopicMessages.chat_id == message.from_user.id,
                            DB.ForwardTopicMessages.forward_message_id == message.reply_to_message.message_id,
                            DB.ForwardTopicMessages.from_entity == 'bot'
                        ]
                    )
                    if message_data:
                        forward_message = message_data.message_id
            if not album:
                if forward_message:
                    await telegram.topic_manager.send_message(
                        thread_id=user_data.thread_id,
                        text='Ответ на сообщение:',
                        reply_to_message_id=forward_message
                    )
                mess = await bot.forward_message(chat_id=telegram.topic_manager.bot_group,
                                                 from_chat_id=message.chat.id,
                                                 message_id=message.message_id,
                                                 message_thread_id=user_data.thread_id)
            else:
                mess = await bot.send_media_group(chat_id=telegram.topic_manager.bot_group,
                                                  media=telegram.unpack_media_group(album, 'input_media'),
                                                  message_thread_id=user_data.thread_id,
                                                  reply_to_message_id=forward_message)
                mess = mess[0]
            DB.ForwardTopicMessages.add(message.from_user.id, message.message_id, mess.message_id, 'user')
            if await is_in_night_period():
                await message.answer(bot_texts.menu['night'])
            if not user_data.authorized:
                await telegram.topic_manager.edit_topic(
                    name=f'{message.from_user.full_name} [Пользователь]',
                    thread_id=user_data.thread_id,
                    emoji_id='5377438129928020693'
                )

                support_id = DB.Support.add(
                    message.from_user.id, user_data.thread_id, message.text if message.text else 'Нет'
                )

                thread_url = telegram.topic_manager.topic_url(user_data.thread_id)
                admin_hlink = []
                notify = DB.AdminNotification.select(all_scalars=True)
                for admin in notify:
                    if admin.support:
                        admin_data = DB.User.select(mark=admin.admin_id)
                        admin_hlink.append(
                            telegram.generate_user_hlink(
                                user_id=admin_data.user_id, user_name=admin_data.username,
                                text_link=admin_data.full_name))

                sup_msg = await telegram.topic_manager.send_message(
                    8946, f'🔔 <b>Новое обращение в поддержку!</b>\n\n' + ', '.join(admin_hlink),
                    reply_markup=telegram.create_inline([['⤴️Открыть диалог', 'url', thread_url]], 1), main_bot=True)

                support_message = await mess.reply(f'<b>🔔Обращение в поддержку №{support_id}:\n\n'
                                                         f'Статус обращения: <code>Открыто</code>\n'
                                                         f'Тип обращения: Новые\n\n'
                                                         f'<i>Переписка с пользователем </i>👇</b>',
                                                         reply_markup=kb_admin_support.support_kb(support_id, sup_msg.message_id))
                await support_message.pin()
            # if user_data.authorized:
            #     try:
            #         await telegram.topic_manager.edit_topic(
            #             name=f'{message.from_user.full_name} [Пользователь]',
            #             thread_id=user_data.thread_id,
            #             emoji_id='5312241539987020022'
            #         )
            #     except TelegramAPIError:
            #         ...
            # else:
            #     try:
            #         await telegram.topic_manager.edit_topic(
            #             name=f'{message.from_user.full_name} [Пользователь]',
            #             thread_id=user_data.thread_id,
            #             emoji_id='5309958691854754293'
            #         )
            #     except TelegramAPIError:
            #         ...
    elif message.message_thread_id and message.chat.id == telegram.topic_manager.bot_group:
        thread_user = DB.User.select(where=DB.User.thread_id == message.message_thread_id)
        if thread_user:
            if message.text and message.text[0] == '!':
                # await bot.pin_chat_message(chat_id=telegram.topic_manager.bot_group, message_id=message.message_id)
                return await message.reply('<b>✅Заметка сохранена</b>')
            elif message.text and message.text[0] == '/':
                return await message.reply('<b>❌Команда не найдена!</b>')
            try:
                if message.reply_to_message:
                    if message.reply_to_message.from_user.is_bot:
                        message_data = DB.ForwardTopicMessages.select(
                            where=[
                                DB.ForwardTopicMessages.chat_id == thread_user.user_id,
                                DB.ForwardTopicMessages.forward_message_id == message.reply_to_message.message_id,
                                DB.ForwardTopicMessages.from_entity == 'user'
                            ])
                        if message_data:
                            forward_message = message_data.message_id
                    else:
                        message_data = DB.ForwardTopicMessages.select(
                            where=[
                                DB.ForwardTopicMessages.chat_id == thread_user.user_id,
                                DB.ForwardTopicMessages.message_id == message.reply_to_message.message_id,
                                DB.ForwardTopicMessages.from_entity == 'bot'
                            ])
                        if message_data:
                            forward_message = message_data.forward_message_id

                if not album:
                    message_new = await bot.copy_message(chat_id=thread_user.user_id,
                                                         from_chat_id=message.chat.id,
                                                         message_id=message.message_id,
                                                         reply_to_message_id=forward_message,
                                                         allow_sending_without_reply=True)
                    db_id = DB.TopicMessages.add(thread_user.user_id, False if message.text else True,
                                                 [message_new.message_id], message.from_user.id)
                    DB.ForwardTopicMessages.add(thread_user.user_id, message.message_id, message_new.message_id, 'bot')
                    await message.reply(
                        '✅Сообщение отправлено', reply_markup=kb_admin_topic.topic_message(message, db_id))
                else:
                    messages = await bot.send_media_group(chat_id=thread_user.user_id,
                                                          media=telegram.unpack_media_group(album, 'input_media'),
                                                          reply_to_message_id=forward_message,
                                                          allow_sending_without_reply=True)
                    db_id = DB.TopicMessages.add(thread_user.user_id, True, [mess.message_id for mess in messages],
                                                 message.from_user.id)
                    for msg in messages:
                        DB.ForwardTopicMessages.add(thread_user.user_id, msg.message_id, msg.message_id, 'bot')
                    await message.reply('✅Группа вложений отправлена',
                                        reply_markup=kb_admin_topic.topic_message(album[0], db_id))
            except TelegramAPIError as exc:
                str_exc = str(exc)
                if 'user was deleted' in str_exc:
                    await message.reply(f'❌Сообщение не доставлено: пользователь удален')
                elif 'message is too long' in str_exc:
                    await message.reply(f'❌Сообщение не доставлено: сообщение слишком длинное')
                elif 'bot was blocked by the user' in str_exc:
                    await message.reply(f'❌Сообщение не доставлено: пользователь заблокировал бота')
                else:
                    await message.reply(f'❌Сообщение не доставлено: {exc.message}')

def register_not_handled(dp: Dispatcher):
    dp.callback_query.register(not_handled_callback)
    dp.message.register(not_handled_message)
