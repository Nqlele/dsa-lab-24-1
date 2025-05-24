import logging
import os
import asyncio
from decimal import Decimal, ROUND_HALF_UP
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command
import psycopg2
from datetime import datetime
import requests
from functools import lru_cache

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

### ПОМЕНЯТТЬ ТУТА АААААААААААААААААААААААААААААААААААААААААААААААААААААААААААААААА
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")  
FLASK_SERVER_URL = os.getenv('FLASK_SERVER_URL', 'http://localhost:5000')
DB_CONFIG = {
    "user": "postgres",
    "password": "postgres",
    "database": "postgres",
    "host": "localhost",
    "port": 5433
}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

class Register(StatesGroup):
    waiting_for_login = State()

class AddOperation(StatesGroup):
    waiting_for_type = State()
    waiting_for_sum = State()
    waiting_for_date = State()

class OperationsChoice(StatesGroup):
    waiting_for_currency = State()

class BudgetStates(StatesGroup):
    waiting_for_budget = State()

def db_connection():
    return psycopg2.connect(**DB_CONFIG)

@lru_cache(maxsize=3)
def get_cached_rate(currency: str) -> Decimal:
    try:
        response = requests.get(
            f"{FLASK_SERVER_URL}/rate?currency={currency}",
            timeout=3
        )
        if response.status_code == 200:
            rate = response.json().get('rate', 1.0)
            return Decimal(str(rate))  # Явное преобразование в Decimal
        return Decimal('1.0')
    except Exception as e:
        logger.error(f"Ошибка подключения: {e}")
        return Decimal('1.0')

def db_connection():
    return psycopg2.connect(**DB_CONFIG)

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "💰 <b>Финансовый менеджер</b> 💰\n\n"
        "Доступные команды:\n"
        "/reg - регистрация\n"
        "/add_operation - добавить операцию\n"
        "/operations - просмотреть операции\n"
        "/setbudget - установить бюджет на месяц\n\n"
        "Используйте кнопки для удобного ввода данных.",
        parse_mode="HTML"
    )

# Регистрация пользователя
@dp.message(Command("reg"))
async def register(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM users WHERE chat_id = %s", (user_id,))
        if cursor.fetchone():
            await message.answer("ℹ️ Вы уже зарегистрированы.")
            return
        
        await message.answer(
            "📝 Введите ваш логин (от 3 до 20 символов, только буквы и цифры):",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(Register.waiting_for_login)
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Обработка логина
@dp.message(Register.waiting_for_login)
async def save_login(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    login = message.text.strip()
    
    if len(login) < 3 or len(login) > 20:
        await message.answer("❌ Логин должен быть от 3 до 20 символов. Попробуйте еще раз.")
        return
    
    if not login.isalnum():
        await message.answer("❌ Логин должен содержать только буквы и цифры. Попробуйте еще раз.")
        return
    
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT chat_id FROM users WHERE name = %s", (login,))
        if cursor.fetchone():
            await message.answer("❌ Этот логин уже занят. Выберите другой.")
            return
        
        cursor.execute(
            "INSERT INTO users (name, chat_id) VALUES (%s, %s)",
            (login, user_id)
        )
        conn.commit()
        
        await message.answer(f"✅ Регистрация успешна! Добро пожаловать, <b>{login}</b>!", parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении логина: {e}")
        await message.answer("⚠️ Произошла ошибка при регистрации. Попробуйте снова.")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Добавление операции
@dp.message(Command("add_operation"))
async def add_operation(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM users WHERE chat_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Введите команду /reg для регистрации.")
            return
        
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="РАСХОД"), types.KeyboardButton(text="ДОХОД")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer("Выберите тип операции:", reply_markup=keyboard)
        await state.set_state(AddOperation.waiting_for_type)
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении операции: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Обработка типа операции
@dp.message(AddOperation.waiting_for_type)
async def process_type(message: types.Message, state: FSMContext):
    operation_type = message.text.upper()
    
    if operation_type not in ["РАСХОД", "ДОХОД"]:
        await message.answer("❌ Пожалуйста, выберите тип операции с помощью кнопок.")
        return
    
    await state.update_data(operation_type=operation_type)
    await message.answer("Введите сумму операции (только цифры):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddOperation.waiting_for_sum)

# Обработка суммы операции (без подсказки "сегодня")
@dp.message(AddOperation.waiting_for_sum)
async def process_sum(message: types.Message, state: FSMContext):
    try:
        amount = Decimal(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (положительное число).")
        return
    
    await state.update_data(amount=amount)
    await message.answer("Введите дату операции в формате ГГГГ-ММ-ДД:")
    await state.set_state(AddOperation.waiting_for_date)

# Обработка даты операции (без обработки "сегодня")
@dp.message(AddOperation.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    operation_type = user_data['operation_type']
    amount = user_data['amount']
    
    try:
        operation_date = datetime.strptime(message.text, '%Y-%m-%d').date()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ГГГГ-ММ-ДД.")
        return
    
    user_id = message.from_user.id
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO operations (date, sum, chat_id, type_operation) VALUES (%s, %s, %s, %s)",
            (operation_date, amount, user_id, operation_type)
        )
        conn.commit()
        
        await message.answer(
            f"✅ Операция успешно добавлена:\n\n"
            f"<b>Тип:</b> {operation_type}\n"
            f"<b>Сумма:</b> {amount:.2f} руб.\n"
            f"<b>Дата:</b> {operation_date}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении операции: {e}")
        await message.answer("⚠️ Произошла ошибка при сохранении операции. Попробуйте снова.")
    finally:
        await state.clear()
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Установка бюджета
@dp.message(Command("setbudget"))
async def set_budget_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM users WHERE chat_id = %s", (user_id,))
        if not cursor.fetchone():
            await message.answer("❌ Вы не зарегистрированы. Введите команду /reg для регистрации.")
            return
        
        current_month = datetime.now().date().replace(day=1)
        cursor.execute(
    "SELECT amount FROM budget WHERE chat_id = %s AND month = %s::date",
    (user_id, current_month)
)
        existing_budget = cursor.fetchone()
        
        if existing_budget:
            await message.answer(
                f"ℹ️ У вас уже установлен бюджет на текущий месяц: {existing_budget[0]:.2f} руб.\n"
                "Хотите изменить его? Введите новую сумму бюджета или 'отмена' для отмены:"
            )
        else:
            await message.answer("Введите сумму бюджета на текущий месяц (в рублях):")
        
        await state.set_state(BudgetStates.waiting_for_budget)
        
    except Exception as e:
        logger.error(f"Ошибка при установке бюджета: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@dp.message(BudgetStates.waiting_for_budget)
async def process_budget(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    budget_input = message.text.lower()
    
    if budget_input == 'отмена':
        await message.answer("❌ Установка бюджета отменена.")
        await state.clear()
        return
    
    try:
        amount = Decimal(budget_input.replace(',', '.'))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму (положительное число).")
        return
    
    current_month = datetime.now().date().replace(day=1)
    
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO budget (chat_id, month, amount)
            VALUES (%s, %s, %s)
            ON CONFLICT (chat_id, month) 
            DO UPDATE SET amount = EXCLUDED.amount, created_at = CURRENT_TIMESTAMP
        """, (user_id, current_month, amount))
        
        conn.commit()
        
        await message.answer(
            f"✅ Бюджет на {current_month.strftime('%B %Y')} установлен: {amount:.2f} руб."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении бюджета: {e}")
        await message.answer("⚠️ Произошла ошибка при сохранении бюджета. Попробуйте снова.")
    finally:
        await state.clear()
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Просмотр операций с учетом бюджета
@dp.message(Command("operations"))
async def operations(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        conn = db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM users WHERE chat_id = %s", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            await message.answer("❌ Вы не зарегистрированы. Введите команду /reg для регистрации.")
            return
        
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="RUB"), types.KeyboardButton(text="USD"), types.KeyboardButton(text="EUR")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await message.answer("Выберите валюту для отображения операций:", reply_markup=keyboard)
        await state.set_state(OperationsChoice.waiting_for_currency)
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре операций: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@dp.message(OperationsChoice.waiting_for_currency)
async def process_currency(message: types.Message, state: FSMContext):
    currency = message.text.upper()
    user_id = message.from_user.id

    if currency not in ["RUB", "USD", "EUR"]:
        await message.answer("❌ Пожалуйста, выберите валюту с помощью кнопок.")
        return

    try:
        with db_connection() as conn:
            with conn.cursor() as cursor:
                # Получаем курс валюты
                rate = (
                    Decimal("1.0")
                    if currency == "RUB"
                    else get_cached_rate(currency)
                )

                # Проверка ошибки получения курса
                if currency != "RUB" and rate == Decimal("1.0"):
                    await message.answer(
                        f"⚠️ Курс {currency} недоступен. Показываю в рублях.",
                        reply_markup=types.ReplyKeyboardRemove(),
                    )
                    currency = "RUB"
                    rate = Decimal("1.0")

                current_month = datetime.now().date().replace(day=1)

                # Получаем бюджет
                cursor.execute(
                    "SELECT amount FROM budget WHERE chat_id = %s AND month = %s",
                    (user_id, current_month),
                )
                budget = cursor.fetchone()
                budget_amount = (
                    Decimal(str(budget[0])) if budget else None
                )

                # Получаем операции
                cursor.execute(
                    """SELECT date, sum, type_operation 
                    FROM operations 
                    WHERE chat_id = %s 
                    AND date >= %s 
                    AND date < %s + INTERVAL '1 month'
                    ORDER BY date DESC""",
                    (user_id, current_month, current_month),
                )
                operations = cursor.fetchall()

                # Рассчитываем общие расходы
                cursor.execute(
                    """SELECT COALESCE(SUM(sum), 0)
                    FROM operations
                    WHERE chat_id = %s
                    AND type_operation = 'РАСХОД'
                    AND date >= %s
                    AND date < %s + INTERVAL '1 month'""",
                    (user_id, current_month, current_month),
                )
                total_expenses = Decimal(str(cursor.fetchone()[0]))

                # Формируем ответ
                response_text = (
                    f"📊 <b>Ваши операции за {current_month.strftime('%B %Y')} ({currency}):</b>\n\n"
                )
                for op in operations:
                    date, amount, op_type = op
                    converted_amount = (Decimal(str(amount)) / rate)
                    converted_amount = converted_amount.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
                    response_text += f"<i>{date}</i>: {op_type} {converted_amount} {currency}\n"

                # Добавляем расходы
                total_expenses_converted = (total_expenses / rate).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
                response_text += f"\n<b>Итого расходов:</b> {total_expenses_converted} {currency}\n"

                # Обработка бюджета
                if budget_amount:
                    converted_budget = (budget_amount / rate).quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)
                    remaining_budget = (budget_amount - total_expenses) / rate
                    remaining_budget = remaining_budget.quantize(Decimal("0.00"), rounding=ROUND_HALF_UP)

                    response_text += (
                        f"<b>Установленный бюджет:</b> {converted_budget} {currency}\n"
                        f"<b>Остаток бюджета:</b> {remaining_budget} {currency}\n"
                    )

                    # Расчет процента с защитой от деления на ноль
                    if budget_amount != Decimal("0"):
                        percentage = (total_expenses / budget_amount * Decimal("100")).quantize(
                            Decimal("1.00"), rounding=ROUND_HALF_UP
                        )
                        percentage = min(percentage, Decimal("100.00"))  # Ограничение до 100%
                        filled = min(int(percentage) // 10, 10)  # Не больше 10 ячеек
                        progress_bar = "🟩" * filled + "⬜️" * (10 - filled)
                    else:
                        percentage = Decimal("0.00")
                        progress_bar = "[⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️⬜️]"

                    response_text += f"\n<b>Использовано:</b> {percentage}% {progress_bar}"
                else:
                    response_text += "\nℹ️ Бюджет не установлен. Используйте /setbudget"

                await message.answer(response_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка: {str(e)}", exc_info=True)
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
    finally:
        await state.clear()

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())