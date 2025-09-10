import asyncio
import logging
import os
import asyncpg
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
FORM_URL = "https://example.com/form"
DATABASE_URL = os.getenv('DATABASE_URL')

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

class UserStates(StatesGroup):
    waiting_for_reg_number = State()

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    user = message.from_user
    await add_user_to_db(user)
    
    welcome_text = f"""Привет, {user.first_name}! 👋

Добро пожаловать в наш бот!

Пожалуйста, прочтите инструкцию, перейдите по ссылке и заполните анкету:
{FORM_URL}"""
    
    await message.answer(welcome_text)
    
    await asyncio.sleep(5)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔢 Ввести регистрационный номер", callback_data="enter_reg_number")],
        [InlineKeyboardButton(text="📋 Мои данные", callback_data="my_data")],
        [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")]
    ])
    
    await message.answer("После заполнения анкеты выберите действие:", reply_markup=keyboard)

@dp.message(UserStates.waiting_for_reg_number)
async def process_reg_number(message: Message, state: FSMContext):
    try:
        reg_number = int(message.text.strip())
        user_id = message.from_user.id
        
        await update_user_reg(user_id, reg_number)
        await message.answer(f"Ваш регистрационный номер {reg_number} записан")
        await state.clear()
        
    except ValueError:
        await message.answer("Пожалуйста, отправьте только число - ваш регистрационный номер.")

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
    support_text = """🆘 Поддержка

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
        curator_reg = 2323  # По умолчанию как просил
        
        data_text = f"""📋 Мои данные

Рег номер куратора: {curator_reg}
Мой рег номер: {reg_number}"""
    else:
        data_text = "❌ Данные не найдены. Попробуйте зарегистрироваться заново."
    
    await callback_query.message.answer(data_text)

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())