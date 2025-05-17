import asyncio
import psycopg2
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, BotCommand
from dotenv import load_dotenv
import os
import logging

# Настройка подключения к БД и загрузка токена
load_dotenv()
conn = psycopg2.connect(
    dbname=os.getenv('DB_NAME', 'postgres'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', 'postgres'),
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5433'),
    client_encoding='utf-8'
)
API_TOKEN = os.getenv("API_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Состояния FSM
class AddCurrencyStep(StatesGroup):
    name = State()
    rate = State()

class DeleteCurrencyStep(StatesGroup):
    name = State()

class ChangeRateStep(StatesGroup):
    name = State()
    rate = State()

class ConvertCurrencyStep(StatesGroup):
    name = State()
    amount = State()

class AddAdminStep(StatesGroup):
    chat_id = State()

# Проверка администратора
async def is_admin(chat_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE chat_id = %s", (str(chat_id),))
    return cursor.fetchone() is not None

# Настройка меню команд
async def setup_commands(bot: Bot):
    user_commands = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="get_currencies", description="Список валют"),
        BotCommand(command="convert", description="Конвертация валюты")
    ]
    admin_commands = user_commands + [
        BotCommand(command="manage_currency", description="Управление валютами"),
        BotCommand(command="add_admin", description="Добавить администратора")
    ]
    
    await bot.set_my_commands(commands=user_commands)
    
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM admins")
    admins = cursor.fetchall()
    for admin in admins:
        try:
            await bot.set_my_commands(commands=admin_commands, scope=types.BotCommandScopeChat(chat_id=int(admin[0])))
        except Exception as e:
            logger.error(f"Failed to set commands for admin {admin[0]}: {e}")

# Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    commands_list = [
        "/get_currencies - список всех валют",
        "/convert - конвертировать валюту"
    ]
    
    if await is_admin(message.chat.id):
        commands_list.append("/manage_currency - управление валютами (только для админов)")
        commands_list.append("/add_admin - добавить администратора")
    
    await message.answer(
        "Привет! Я бот для работы с валютами.\n\n"
        "Доступные команды:\n" + "\n".join(commands_list)
    )

# Команда /add_admin (только для суперадмина)
@dp.message(Command("add_admin"))
async def add_admin(message: Message, state: FSMContext):
    if message.chat.id != 796749531: 
        await message.answer("Нет доступа")
        return
        
    await message.answer("Введите chat_id нового админа:")
    await state.set_state(AddAdminStep.chat_id)

@dp.message(AddAdminStep.chat_id)
async def add_admin_chat_id(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный chat_id. Введите число.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO admins (chat_id) VALUES (%s)", (str(chat_id),))
        conn.commit()
        await message.answer(f"Пользователь {chat_id} добавлен в админы.")
        await setup_commands(bot)  # Обновляем меню команд
    except psycopg2.errors.UniqueViolation:
        await message.answer("Этот пользователь уже является админом.")
    await state.clear()

# Команда /manage_currency (только для админов)
@dp.message(Command("manage_currency"))
async def manage_currency(message: Message):
    if not await is_admin(message.chat.id):
        await message.answer("Нет доступа к команде")
        return

    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить валюту"), KeyboardButton(text="Удалить валюту")],
            [KeyboardButton(text="Изменить курс валюты")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие:", reply_markup=markup)

# Добавление валюты
@dp.message(F.text == "Добавить валюту")
async def add_currency(message: Message, state: FSMContext):
    if not await is_admin(message.chat.id):
        await message.answer("Нет доступа")
        return
        
    await message.answer("Введите название валюты:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddCurrencyStep.name)

@dp.message(AddCurrencyStep.name)
async def add_currency_name(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
    
    if cursor.fetchone() is not None:
        await message.answer("Данная валюта уже существует")
        await state.clear()
        return

    await state.update_data(currency_name=currency_name)
    await message.answer("Введите курс к рублю:")
    await state.set_state(AddCurrencyStep.rate)

@dp.message(AddCurrencyStep.rate)
async def add_rate_step(message: Message, state: FSMContext):
    try:
        rate = float(message.text.strip().replace(",", "."))
        if rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректный формат курса. Введите положительное число")
        return

    data = await state.get_data()
    currency_name = data.get('currency_name')
    
    cursor = conn.cursor()
    cursor.execute("INSERT INTO currencies (currency_name, rate) VALUES (%s, %s)", (currency_name, rate))
    conn.commit()
    
    await message.answer(f"Валюта {currency_name} успешно добавлена с курсом {rate}")
    await state.clear()

# Удаление валюты
@dp.message(F.text == "Удалить валюту")
async def delete_currency(message: Message, state: FSMContext):
    if not await is_admin(message.chat.id):
        await message.answer("Нет доступа")
        return
        
    await message.answer("Введите название валюты для удаления:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(DeleteCurrencyStep.name)

@dp.message(DeleteCurrencyStep.name)
async def delete_currency_name(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
    if cursor.fetchone() is None:
        await message.answer(f"Валюта {currency_name} не найдена")
        await state.clear()
        return
    
    cursor.execute("DELETE FROM currencies WHERE currency_name = %s", (currency_name,))
    conn.commit()
    await message.answer(f"Валюта {currency_name} успешно удалена")
    await state.clear()

# Изменение курса валюты
@dp.message(F.text == "Изменить курс валюты")
async def change_rate(message: Message, state: FSMContext):
    if not await is_admin(message.chat.id):
        await message.answer("Нет доступа")
        return
        
    await message.answer("Введите название валюты:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(ChangeRateStep.name)

@dp.message(ChangeRateStep.name)
async def change_rate_name(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM currencies WHERE currency_name = %s", (currency_name,))
    if cursor.fetchone() is None:
        await message.answer(f"Валюта {currency_name} не найдена")
        await state.clear()
        return
    
    await state.update_data(currency_name=currency_name)
    await message.answer("Введите новый курс к рублю:")
    await state.set_state(ChangeRateStep.rate)

@dp.message(ChangeRateStep.rate)
async def change_rate_value(message: Message, state: FSMContext):
    try:
        rate = float(message.text.strip().replace(",", "."))
        if rate <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректный формат курса. Введите положительное число")
        return

    data = await state.get_data()
    currency_name = data.get('currency_name')
    
    cursor = conn.cursor()
    cursor.execute("UPDATE currencies SET rate = %s WHERE currency_name = %s", (rate, currency_name))
    conn.commit()
    
    await message.answer(f"Курс валюты {currency_name} успешно изменен на {rate}")
    await state.clear()

# Команда /get_currencies
@dp.message(Command("get_currencies"))
async def get_currencies(message: Message):
    cursor = conn.cursor()
    cursor.execute("SELECT currency_name, rate FROM currencies ORDER BY currency_name")
    currencies = cursor.fetchall()
    
    if not currencies:
        await message.answer("В базе данных нет сохраненных валют")
        return
    
    response = "Текущие курсы валют к рублю:\n\n"
    response += "\n".join([f"{curr[0]}: {curr[1]}" for curr in currencies])
    await message.answer(response)

# Команда /convert
@dp.message(Command("convert"))
async def convert_currency(message: Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(ConvertCurrencyStep.name)

@dp.message(ConvertCurrencyStep.name)
async def convert_currency_name(message: Message, state: FSMContext):
    currency_name = message.text.strip().upper()
    cursor = conn.cursor()
    cursor.execute("SELECT rate FROM currencies WHERE currency_name = %s", (currency_name,))
    currency = cursor.fetchone()
    
    if not currency:
        await message.answer(f"Валюта {currency_name} не найдена")
        await state.clear()
        return
    
    await state.update_data(currency_name=currency_name, rate=currency[0])
    await message.answer("Введите сумму для конвертации:")
    await state.set_state(ConvertCurrencyStep.amount)

@dp.message(ConvertCurrencyStep.amount)
async def convert_amount_step(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Некорректный формат суммы. Введите положительное число")
        return

    data = await state.get_data()
    currency_name = data['currency_name']
    rate = data['rate']
    
    converted_amount = amount * float(rate)
    await message.answer(f"{amount} {currency_name} = {converted_amount:.2f} рублей")
    await state.clear()

# Обработка неизвестных сообщений
@dp.message()
async def unknown_command(message: Message):
    await message.answer("Неизвестная команда. Введите /start для просмотра доступных команд")

# Запуск бота
async def on_startup(bot: Bot):
    await setup_commands(bot)
    logger.info("Бот запущен")

async def main():
    dp.startup.register(on_startup)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())