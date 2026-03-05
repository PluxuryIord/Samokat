"""
AUTHOR CODE - V1N3R
TG: @v1n3r
Site Company: buy-bot.ru
"""

from aiogram import Dispatcher
from aiogram import F
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.handlers.client.client_main import main_menu
from bot.initialization import bot_texts
from bot.integrations import DB
from bot.keyboards.admin import kb_admin_support
from bot.keyboards.client import kb_client_menu
from bot.states.wait_question import FsmWaitQuestion
from bot.utils import telegram as telegram

async def select_type(call: CallbackQuery):
    await call.message.edit_text('<b>Выберите тип вашего обращения 👇</b>',
                                 reply_markup=kb_client_menu.support_type)


async def support(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text('<b>Кратко опишите свой запрос, а я передам его команде поддержки. '
                                 'Они обязательно свяжутся с вами!</b>',
                                 reply_markup=kb_client_menu.back_menu)
    await state.set_state(FsmWaitQuestion.wait_text)
    await state.update_data(menu=call.message, question=call.data.split(':')[1])
    await call.answer()


async def command_support(message: Message, state: FSMContext, user_data: DB.User):
    menu: Message = await main_menu(update=message, user=message.from_user, state=state, user_data=user_data)
    await menu.edit_text('<b>Кратко опишите свой запрос, а я передам его команде поддержки. '
                         'Они обязательно свяжутся с вами!</b>',
                         reply_markup=kb_client_menu.back_menu)
    await state.set_state(FsmWaitQuestion.wait_text)
    await state.update_data(menu=menu)


async def wait_question(message: Message, state: FSMContext, user_data: DB.User, album: list[Message] = False):
    data = await state.get_data()
    menu: Message = data['menu']
    if message.text in ['/start', '/help', '🔄Перезагрузить меню']:
        await state.clear()
        return
    await menu.edit_text('⏳')
    try:
        await telegram.topic_manager.edit_topic(
            name=f'{message.from_user.full_name} [{"Кандидат" if not user_data.authorized else "Пользователь"}]',
            thread_id=user_data.thread_id,
            emoji_id='5377438129928020693'
        )
    except TelegramAPIError:
        ...
    support_id = DB.Support.add(
        message.from_user.id, user_data.thread_id, message.text if message.text else 'Нет'
    )
    if not album:
        quest_text = await telegram.bot.forward_message(chat_id=telegram.topic_manager.bot_group,
                                                       from_chat_id=message.chat.id,
                                                       message_id=message.message_id,
                                                       message_thread_id=user_data.thread_id)
    else:
        quest_text = await telegram.bot.send_media_group(chat_id=telegram.topic_manager.bot_group,
                                            media=telegram.unpack_media_group(album, 'input_media'),
                                            message_thread_id=user_data.thread_id)
    data = await state.get_data()
    thread_url = telegram.topic_manager.topic_url(user_data.thread_id)
    admin_hlink = []
    notify = DB.AdminNotification.select(all_scalars=True)
    for admin in notify:
        if admin.support:
            admin_data = DB.User.select(mark=admin.admin_id)
            admin_hlink.append(
                telegram.generate_user_hlink(
                    user_id=admin_data.user_id, user_name=admin_data.username, text_link=admin_data.full_name))

    if data["question"] == 'Выплаты':
        sup_msg = await telegram.topic_manager.send_message(
            193, f'🔔 <b>Новое обращение в поддержку!</b>\n\n' + ', '.join(admin_hlink),
            reply_markup=telegram.create_inline([['⤴️Открыть диалог', 'url', thread_url]], 1), main_bot=True)
    elif data['question'] == 'Другие вопросы':
        sup_msg = await telegram.topic_manager.send_message(
            195, f'🔔 <b>Новое обращение в поддержку!</b>\n\n' + ', '.join(admin_hlink),
            reply_markup=telegram.create_inline([['⤴️Открыть диалог', 'url', thread_url]], 1), main_bot=True)

    support_message = await quest_text.reply(f'<b>🔔Обращение в поддержку №{support_id}:\n\n'
                          f'Статус обращения: <code>Открыто</code>\n'
                          f'Тип обращения: {data["question"]}\n\n'
                          f'<i>Переписка с пользователем </i>👇</b>',
                          reply_markup=kb_admin_support.support_kb(support_id, sup_msg.message_id))
    await support_message.pin()
    await menu.edit_text('<b>✅ Ваш запрос передан организаторам!</b>',
                         reply_markup=kb_client_menu.back_menu)
    await state.clear()


async def faq(call: CallbackQuery):
    await call.message.edit_text(bot_texts.menu['faq'], reply_markup=kb_client_menu.back_menu)

def register_handlers_client_support(dp: Dispatcher):
    #dp.message.register(command_support, Command(commands="help"))
    dp.callback_query.register(select_type, F.data == "client_support")
    dp.callback_query.register(support, F.data.startswith("support_type"))
    dp.message.register(wait_question, FsmWaitQuestion.wait_text)
    dp.callback_query.register(faq, F.data == 'client_faq')
