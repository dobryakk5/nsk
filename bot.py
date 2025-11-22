import asyncio
import logging
import os
import asyncpg
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters.state import StateFilter
from goal_messages import (
    get_women_beauty_message,
    get_youth_message,
    get_energy_message,
    get_calm_message,
    get_focus_message,
    get_children_health_message,
    get_chlorophyll_message
)

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
FORM_URL = "https://nsp25.com/signup?sid=7628641"
DATABASE_URL = os.getenv('DATABASE_URL')
SPONSOR_NUMBER = 7628641

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_db_connection():
    return await asyncpg.connect(DATABASE_URL)

async def add_user_to_db(user: types.User):
    try:
        conn = await get_db_connection()
        await conn.execute('''
            INSERT INTO users (tg_user_id, username, first_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (tg_user_id) DO NOTHING
        ''', user.id, user.username, user.first_name)
    except asyncpg.PostgresError as e:
        logging.error(f"Database error: {e}")
    finally:
        if conn:
            await conn.close()

async def update_user_reg(tg_user_id: int, reg_number: int):
    try:
        conn = await get_db_connection()
        await conn.execute('''
            UPDATE users SET reg = $1 WHERE tg_user_id = $2
        ''', reg_number, tg_user_id)
    except asyncpg.PostgresError as e:
        logging.error(f"Database error: {e}")
    finally:
        if conn:
            await conn.close()

async def get_user_data(tg_user_id: int):
    try:
        conn = await get_db_connection()
        user_data = await conn.fetchrow('''
            SELECT reg, first_name FROM users WHERE tg_user_id = $1
        ''', tg_user_id)
        return user_data
    except asyncpg.PostgresError as e:
        logging.error(f"Database error: {e}")
        return None
    finally:
        if conn:
            await conn.close()

async def get_all_users():
    try:
        conn = await get_db_connection()
        users = await conn.fetch('''
            SELECT username, reg FROM users 
            WHERE username IS NOT NULL 
            ORDER BY created_at DESC
        ''')
        return users
    except asyncpg.PostgresError as e:
        logging.error(f"Database error: {e}")
        return []
    finally:
        if conn:
            await conn.close()

async def is_admin(tg_user_id: int):
    try:
        conn = await get_db_connection()
        user = await conn.fetchrow('''
            SELECT role FROM users WHERE tg_user_id = $1
        ''', tg_user_id)
        return user and user['role'] == 1
    except asyncpg.PostgresError as e:
        logging.error(f"Database error: {e}")
        return False
    finally:
        if conn:
            await conn.close()

def get_system_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="📋 Мои данные"), KeyboardButton(text="🛒 Заказ продуктов")],
        [KeyboardButton(text="👩‍⚕️ Мой нутрициолог"), KeyboardButton(text="🎯 Моя цель")],
        [KeyboardButton(text="🔢 Ввести регистрационный номер")],
        [KeyboardButton(text="❓ Поддержка")]
    ], resize_keyboard=True)

def get_goals_menu_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💃 Женская красота"), KeyboardButton(text="✨ Молодость")],
        [KeyboardButton(text="⚡ Больше энергии"), KeyboardButton(text="😌 Успокоиться")],
        [KeyboardButton(text="🎯 Концентрация внимания"), KeyboardButton(text="👶 Детское здоровье")],
        [KeyboardButton(text="⬅️ Главное меню"), KeyboardButton(text="🌿 НА КАЖДЫЙ ДЕНЬ")]
    ], resize_keyboard=True)

class UserStates(StatesGroup):
    waiting_for_reg_number = State()

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    user = message.from_user
    await add_user_to_db(user)
    
    welcome_text = f"""Здравствуйте, {user.first_name}! 👋

Добро пожаловать в NSP бот помощник!

Пожалуйста, прочтите инструкцию, перейдите по ссылке и заполните анкету:
(номер сервисного центра 300)
{FORM_URL}
"""
    
    await message.answer(welcome_text)
    
    await asyncio.sleep(5)
    
    await message.answer("После заполнения анкеты отправьте этому боту регистрационный номер")
    await state.set_state(UserStates.waiting_for_reg_number)

@dp.message(UserStates.waiting_for_reg_number, lambda message: message.text not in ["❓ Поддержка", "📋 Мои данные", "🔢 Ввести регистрационный номер", "🛒 Заказ продуктов", "👩‍⚕️ Мой нутрициолог", "🎯 Моя цель"])
async def process_reg_number(message: Message, state: FSMContext):
    try:
        reg_number = int(message.text.strip())
        user_id = message.from_user.id
        
        await update_user_reg(user_id, reg_number)
        await message.answer(f"Ваш регистрационный номер {reg_number} записан", reply_markup=get_system_menu_keyboard())
        
        growth_text = """Выбирайте в меню свою цель и присоединяйтесь для дальнейшего роста:

https://t.me/+WTmB9LAAHmpjZGJi
https://t.me/naturessunshine25
https://naturessunshine.ru/"""
        
        await message.answer(growth_text)
        await state.clear()
        
        
    except ValueError:
        await message.answer(f"Пожалуйста, сначала заполните анкету по ссылке:\n{FORM_URL} \n Номер сервисного центра 300\n\nЗатем отправьте полученный регистрационный номер (только цифры).", reply_markup=get_system_menu_keyboard())

@dp.message(lambda message: message.text == "❓ Поддержка", UserStates.waiting_for_reg_number)
async def handle_support_during_reg(message: Message, state: FSMContext):
    support_text = """❓ Поддержка

Если у вас возникли вопросы или проблемы, обратитесь к администратору:
@admin_username

Или напишите на почту: support@example.com
Обновить бота: /start"""
    
    await message.answer(support_text)
    await message.answer("После получения помощи отправьте ваш регистрационный номер:")

@dp.message(lambda message: message.text == "📋 Мои данные", UserStates.waiting_for_reg_number)
async def handle_my_data_during_reg(message: Message):
    user_data = await get_user_data(message.from_user.id)
    
    if user_data:
        reg_number = user_data['reg'] if user_data['reg'] else "Не указан"
        sponsor_number = SPONSOR_NUMBER
        
        referral_link = f"https://nsp25.com/signup?sid={reg_number}" if reg_number != "Не указан" else "Сначала укажите регистрационный номер"
        
        data_text = f"""📋 Мои данные

Номер спонсора: {sponsor_number}
Мой рег номер: {reg_number}
Моя личная реферальная ссылка: {referral_link}"""
    else:
        data_text = "❌ Данные не найдены. Попробуйте зарегистрироваться заново."
    
    await message.answer(data_text)

@dp.callback_query(lambda c: c.data == "enter_reg_number")
async def process_enter_reg_number(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer(f"Заполните анкету по ссылке:\n{FORM_URL}")
    
    await asyncio.sleep(5)
    
    await callback_query.message.answer("Отправьте номер полученный в анкете")
    await state.set_state(UserStates.waiting_for_reg_number)

@dp.callback_query(lambda c: c.data == "support")
async def process_support(callback_query: CallbackQuery):
    await callback_query.answer()
    support_text = """❓ Поддержка

Если у вас возникли вопросы или проблемы, обратитесь к администратору:
@admin_username

Или напишите на почту: support@example.com"""
    
    await callback_query.message.answer(support_text)

@dp.callback_query(lambda c: c.data == "my_data")
async def process_my_data(callback_query: CallbackQuery):
    await callback_query.answer()
    
    user_data = await get_user_data(callback_query.from_user.id)
    
    if user_data:
        reg_number = user_data['reg'] if user_data['reg'] else "Не указан"
        sponsor_number = SPONSOR_NUMBER  # По умолчанию как просил
        
        referral_link = f"https://nsp25.com/signup?sid={reg_number}" if reg_number != "Не указан" else "Сначала укажите регистрационный номер"
        
        data_text = f"""📋 Мои данные

Номер спонсора: {sponsor_number}
Мой рег номер: {reg_number}
Ваша личная реферальная ссылка: {referral_link}"""
    else:
        data_text = "❌ Данные не найдены. Попробуйте зарегистрироваться заново."
    
    await callback_query.message.answer(data_text)

@dp.message(lambda message: message.text == "🔢 Ввести регистрационный номер", StateFilter(None))
async def handle_enter_reg_number(message: Message, state: FSMContext):
    await message.answer(f"Заполните анкету по ссылке:\n{FORM_URL}")
    
    await asyncio.sleep(5)
    
    await message.answer("Отправьте номер полученный в анкете")
    await state.set_state(UserStates.waiting_for_reg_number)

@dp.message(lambda message: message.text == "📋 Мои данные", StateFilter(None))
async def handle_my_data(message: Message):
    user_data = await get_user_data(message.from_user.id)
    
    if user_data:
        reg_number = user_data['reg'] if user_data['reg'] else "Не указан"
        sponsor_number = SPONSOR_NUMBER
        
        referral_link = f"https://nsp25.com/signup?sid={reg_number}" if reg_number != "Не указан" else "Сначала укажите регистрационный номер"
        
        data_text = f"""📋 Мои данные

Номер спонсора: {sponsor_number}
Мой рег номер: {reg_number}
Ваша личная реферальная ссылка: {referral_link}"""
    else:
        data_text = "❌ Данные не найдены. Попробуйте зарегистрироваться заново."
    
    await message.answer(data_text)

@dp.message(lambda message: message.text == "❓ Поддержка", StateFilter(None))
async def handle_support(message: Message):
    support_text = """❓ Поддержка

Если у вас возникли вопросы или проблемы, обратитесь к администратору:
@admin_username

Или напишите на почту: support@example.com"""
    
    await message.answer(support_text)

@dp.message(lambda message: message.text == "🛒 Заказ продуктов", StateFilter(None))
async def handle_product_order(message: Message):
    order_text = f"""🛒 Заказ продуктов

https://nsp.com.ru/

Нужно ввести свой регистрационный номер и номер спонсора {SPONSOR_NUMBER}
Чтобы видеть оптовые цены"""
    
    await message.answer(order_text)

@dp.message(lambda message: message.text == "🛒 Заказ продуктов", UserStates.waiting_for_reg_number)
async def handle_product_order_during_reg(message: Message):
    order_text = f"""🛒 Заказ продуктов

https://nsp.com.ru/

Нужно ввести свой регистрационный номер и номер спонсора {SPONSOR_NUMBER}
Чтобы видеть оптовые цены"""
    
    await message.answer(order_text)

@dp.message(lambda message: message.text == "👩‍⚕️ Мой нутрициолог", StateFilter(None))
async def handle_nutritionist(message: Message):
    nutritionist_text = """👩‍⚕️ Мой нутрициолог

Имя: Надежда Артюх
Мобильный: +7 922 420-14-99

https://wa.me/79224201499"""
    
    await message.answer(nutritionist_text)

@dp.message(lambda message: message.text == "👩‍⚕️ Мой нутрициолог", UserStates.waiting_for_reg_number)
async def handle_nutritionist_during_reg(message: Message):
    nutritionist_text = """👩‍⚕️ Мой нутрициолог

Имя: Надежда Артюх
Мобильный: +7 922 420-14-99

https://wa.me/79224201499"""

    await message.answer(nutritionist_text)

@dp.message(lambda message: message.text == "🎯 Моя цель", StateFilter(None))
async def handle_my_goal(message: Message):
    goal_text = """🎯 Моя цель

Выберите свою цель:"""

    await message.answer(goal_text, reply_markup=get_goals_menu_keyboard())

@dp.message(lambda message: message.text == "🎯 Моя цель", UserStates.waiting_for_reg_number)
async def handle_my_goal_during_reg(message: Message):
    goal_text = """🎯 Моя цель

Выберите свою цель:"""

    await message.answer(goal_text, reply_markup=get_goals_menu_keyboard())

@dp.message(lambda message: message.text == "⬅️ Назад в главное меню")
async def handle_back_to_main_menu(message: Message):
    await message.answer(reply_markup=get_system_menu_keyboard())

@dp.message(lambda message: message.text == "💃 Женская красота")
async def handle_goal_lose_weight(message: Message):
    await message.answer(get_women_beauty_message())

@dp.message(lambda message: message.text == "✨ Молодость")
async def handle_goal_youth(message: Message):
    await message.answer(get_youth_message())

@dp.message(lambda message: message.text == "⚡ Больше энергии")
async def handle_goal_energy(message: Message):
    await message.answer(get_energy_message())

@dp.message(lambda message: message.text == "😌 Успокоиться")
async def handle_goal_calm(message: Message):
    await message.answer(get_calm_message())

@dp.message(lambda message: message.text == "🎯 Концентрация внимания")
async def handle_goal_focus(message: Message):
    await message.answer(get_focus_message())

@dp.message(lambda message: message.text == "👶 Детское здоровье")
async def handle_goal_children_health(message: Message):
    await message.answer(get_children_health_message())

@dp.message(lambda message: message.text == "🌿 НА КАЖДЫЙ ДЕНЬ")
async def handle_goal_chlorophyll(message: Message):
    await message.answer(get_chlorophyll_message())

@dp.message(lambda message: message.text and message.text.lower() == "клиенты")
async def handle_clients_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("Нет доступа")
        return
    
    users = await get_all_users()
    
    if not users:
        await message.answer("Пользователи не найдены")
        return
    
    clients_text = "<b>Список клиентов:</b>\n\n"
    
    for user in users:
        username = user['username'] if user['username'] else "Нет username"
        reg = user['reg'] if user['reg'] else "Нет номера"
        clients_text += f"<b>@{username}</b> | <code>{reg}</code>\n"
    
    await message.answer(clients_text, parse_mode="HTML")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())