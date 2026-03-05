"""
AUTHOR CODE - V1N3R
TG: @v1n3r
Site Company: buy-bot.ru
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from bot.utils.telegram import create_inline, kb_delete_message


def main_menu(admin: bool):
    buttons = [
        ['Чаты', 'call', 'client_chats'],
        # ['Правила', 'call', 'client_rules'],
        ['Помощь', 'call', 'client_support']
    ]
    if admin:
        buttons.append(['⚙️ Меню администратора', 'call', 'admin_menu'])
    return create_inline(buttons, 1)


delete_message = kb_delete_message

back_menu = create_inline([['🔙 Меню', 'call', 'client_back_menu']], 1)


async def send_phone():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="Отправить контакт", request_contact=True))
    builder.row(KeyboardButton(text="Стать частью команды 🦹‍♂️"))
    return builder.as_markup(resize_keyboard=True)


async def chat_links(link: str):
    return create_inline([
        ['📎 Чат', 'url', f'{link}'],
        ['Прочие чаты с описанием', 'call', f'other_chats'],
        ['🔙 Меню', 'call', 'client_back_menu']
    ], 1
    )


back_chats = create_inline([['🔙 Назад', 'call', 'client_chats']], 1)

support_type = create_inline(
    [
        # ['Чат с поддержкой', 'call', 'support_type:Чат'],
        ['Вопрос по выплатам', 'call', 'support_type:Выплаты'],
        # ['Часто задаваемые вопросы', 'call', 'client_faq'],
        # ['Техническая поддержка', 'call', 'support_type:Тех.проблема'],
        ['Другие вопросы', 'call', 'support_type:Другие вопросы'],
        ['Контакты', 'call', 'client_contacts'],
        ['🔙 Меню', 'call', 'client_back_menu']
    ], 1
)

cooperation = create_inline([['Хочу сотрудничать!', 'url', 'https://t.me/m/_zoFjGb-YTky']], 1)

back_support = create_inline([['🔙 Назад', 'call', 'client_support']], 1)