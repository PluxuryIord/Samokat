import csv
import os
from datetime import datetime

from aiogram import Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.integrations.database.db_main import DB
from bot.integrations.database.db_stats import DBStats
from bot.initialization.config import config
from bot.utils.announce_bot import bot

# 1. Клавиатура с 3 кнопками
def season_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Готов выходить", callback_data="season_ready")
    builder.button(text="Выйду в теплую погоду", callback_data="season_warm")
    builder.button(text="Удалиться из бота, не актуально", callback_data="season_leave")
    builder.adjust(1) # Кнопки будут идти друг под другом
    return builder.as_markup()

# 2. Команда запуска рассылки (/season_alert)
async def send_season_alert(message: Message):
    # Защита: запустить может только сисадмин
    if not DB.Admin.select(where=(DB.Admin.admin_id == message.from_user.id)):
        return

    text = "Снег тает, самокаты просыпаются ⛅\nТы с нами в этом сезоне? 😎"
    users = DB.User.select(all_scalars=True)
    count = 0
    
    status_msg = await message.answer(f"⏳ Запускаю рассылку. Всего пользователей в базе: {len(users)}...")
    
    for user in users:
        # Шлем только тем, кто авторизован и не заблокирован
        if user.authorized and not user.banned:
            try:
                await bot.send_message(user.user_id, text, reply_markup=season_keyboard())
                count += 1
            except Exception:
                pass # Игнорируем тех, кто удалил бота
                
    await status_msg.edit_text(f"✅ Рассылка успешно завершена!\nДоставлено сообщений: {count}")

# 3. Обработка нажатий на кнопки
async def handle_season_buttons(call: CallbackQuery):
    action = call.data
    
    if action == "season_ready":
        await call.answer("Супер!", show_alert=True)
    elif action == "season_warm":
        await call.answer("Договорились, напишем, как потеплеет!", show_alert=True)
    elif action == "season_leave":
        await call.answer("Поняли вас. Вы отписаны от рассылок, удачи!", show_alert=True)
        # Отключаем пользователя от будущих рассылок в MySQL
        DB.User.update(mark=call.from_user.id, authorized=0)
        
    # Убираем кнопки, чтобы нельзя было проголосовать дважды
    await call.message.edit_text("✅ Ваш ответ принят")

# 4. Команда выгрузки статистики (/season_stats)
async def get_season_stats(message: Message):
    if not config.admin_filter.is_system(message.from_user.id):
        return
        
    status_msg = await message.answer("⏳ Собираю статистику из баз данных...")
    
    events = DBStats.Events.select(all_scalars=True)
    filename = f"season_stats_{datetime.now().strftime('%d_%m_%Y')}.csv"
    
    # utf-8-sig нужен, чтобы русский язык идеально открывался в Excel
    with open(filename, mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Telegram ID", "Имя", "Никнейм", "Город", "Ответ"])
        
        answers_map = {
            "season_ready": "Готов выходить",
            "season_warm": "Выйду в теплую погоду",
            "season_leave": "Удалиться"
        }
        
        rows_written = 0
        for event in events:
            # Безопасный поиск сохраненной кнопки в логах
            event_data = str(getattr(event, 'data', getattr(event, 'event_data', getattr(event, 'value', str(event)))))
            
            if any(k in event_data for k in answers_map.keys()):
                answer_key = next((k for k in answers_map.keys() if k in event_data), None)
                if not answer_key: continue
                
                # Достаем актуальные данные юзера из основной БД
                user = DB.User.select(mark=event.user_id)
                if user:
                    name = user.full_name
                    username = f"@{user.username}" if user.username else "нет"
                    city = user.region if user.region else "не указан"
                else:
                    name, username, city = "Неизвестно", "Неизвестно", "Неизвестно"
                    
                writer.writerow([event.user_id, name, username, city, answers_map[answer_key]])
                rows_written += 1
                
    if rows_written == 0:
        await status_msg.edit_text("🤷‍♂️ Пока никто не нажал на кнопки в рассылке.")
        os.remove(filename)
        return
        
    doc = FSInputFile(filename)
    await message.answer_document(doc, caption=f"📊 Статистика по сезонной рассылке.\nВсего ответов: {rows_written}")
    await status_msg.delete()
    os.remove(filename)

# 5. Регистратор хэндлеров
def register_handlers_admin_season(dp: Dispatcher):
    dp.message.register(send_season_alert, Command(commands="season_alert"))
    dp.message.register(get_season_stats, Command(commands="season_stats"))
    dp.callback_query.register(handle_season_buttons, F.data.in_(["season_ready", "season_warm", "season_leave"]))
