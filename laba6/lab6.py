import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import requests
from dotenv import load_dotenv
import os

# Загрузка .env
load_dotenv()

# Инициализация
TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token='7989831725:AAHZLYBMEsrz-a-p5fgZh_ypn4rI96zsAs4')
dp = Dispatcher(storage=MemoryStorage())

# URLs
CURRENCY_MANAGER_URL = 'http://localhost:5001'
DATA_MANAGER_URL = 'http://localhost:5002'

logging.basicConfig(level=logging.INFO)

# Состояния FSM
class AddCurrency(StatesGroup):
    currency_name = State()
    currency_rate = State()

class DeleteCurrency(StatesGroup):
    currency_name = State()

class UpdateCurrency(StatesGroup):
    currency_name = State()
    new_rate = State()

class ConvertCurrency(StatesGroup):
    currency_name = State()
    amount = State()

# Команды
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привет! Я бот для управления валютами. Набери /menu.")

@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Старт")],
            [KeyboardButton(text="Управление валютами")],
            [KeyboardButton(text="Список валют")],
            [KeyboardButton(text="Конвертировать")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие из меню:", reply_markup=keyboard)

# Обработчики для кнопок
@dp.message(F.text == "Старт")
async def start_button_handler(message: types.Message):
    await start(message)

@dp.message(F.text == "Список валют")
async def currencies_button_handler(message: types.Message):
    await get_currencies(message)

@dp.message(F.text == "Конвертировать")
async def convert_button_handler(message: types.Message, state: FSMContext):
    await convert_currency(message, state)

@dp.message(F.text == "Управление валютами")
async def manage_currency(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить валюту")],
            [KeyboardButton(text="Удалить валюту")],
            [KeyboardButton(text="Изменить курс валюты")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите действие:", reply_markup=keyboard)

# Добавление валюты
@dp.message(F.text == "Добавить валюту")
async def add_currency(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(AddCurrency.currency_name)

@dp.message(AddCurrency.currency_name)
async def process_currency_name(message: types.Message, state: FSMContext):
    currency = message.text.upper()
    response = requests.get(f"{DATA_MANAGER_URL}/currencies")
    try:
        currencies = response.json().get("currencies", [])
    except Exception:
        await message.answer("Ошибка получения списка валют.")
        await state.clear()
        return

    if currency in currencies:
        await message.answer("Такая валюта уже существует.")
        await state.clear()
    else:
        await state.update_data(currency_name=currency)
        await message.answer("Введите курс к рублю:")
        await state.set_state(AddCurrency.currency_rate)

@dp.message(AddCurrency.currency_rate)
async def process_currency_rate(message: types.Message, state: FSMContext):
    try:
        rate = float(message.text)
    except ValueError:
        await message.answer("Введите числовое значение.")
        return

    data = await state.get_data()
    response = requests.post(f"{CURRENCY_MANAGER_URL}/load", json={
        "currency_name": data["currency_name"],
        "rate": rate
    })

    if response.status_code == 200:
        await message.answer(f"Валюта {data['currency_name']} успешно добавлена.")
    else:
        await message.answer("Ошибка при добавлении валюты.")
    await state.clear()

# Удаление валюты
@dp.message(F.text == "Удалить валюту")
async def delete_currency(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(DeleteCurrency.currency_name)

@dp.message(DeleteCurrency.currency_name)
async def process_delete_currency(message: types.Message, state: FSMContext):
    currency = message.text.upper()
    response = requests.post(f"{CURRENCY_MANAGER_URL}/delete", json={"currency_name": currency})

    if response.status_code == 200:
        await message.answer(f"Валюта {currency} удалена.")
    else:
        await message.answer("Ошибка при удалении.")
    await state.clear()

# Обновление курса
@dp.message(F.text == "Изменить курс валюты")
async def update_currency(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(UpdateCurrency.currency_name)

@dp.message(UpdateCurrency.currency_name)
async def process_update_currency_name(message: types.Message, state: FSMContext):
    await state.update_data(currency_name=message.text.upper())
    await message.answer("Введите новый курс:")
    await state.set_state(UpdateCurrency.new_rate)

@dp.message(UpdateCurrency.new_rate)
async def process_update_currency_rate(message: types.Message, state: FSMContext):
    try:
        new_rate = float(message.text)
    except ValueError:
        await message.answer("Введите числовое значение.")
        return

    data = await state.get_data()
    response = requests.post(f"{CURRENCY_MANAGER_URL}/update_currency", json={
        "currency_name": data["currency_name"],
        "rate": new_rate
    })

    if response.status_code == 200:
        await message.answer(f"Курс валюты {data['currency_name']} обновлен.")
    else:
        await message.answer("Ошибка при обновлении.")
    await state.clear()

# Получение валют
@dp.message(Command("get_currencies"))
async def get_currencies(message: types.Message):
    response = requests.get(f"{DATA_MANAGER_URL}/currencies")
    try:
        currencies = response.json().get("currencies", [])
    except Exception:
        await message.answer("Ошибка при получении валют.")
        return

    if currencies:
        await message.answer("Доступные валюты:\n" + "\n".join(currencies))
    else:
        await message.answer("Валюты отсутствуют.")

# Конвертация
@dp.message(Command("convert"))
async def convert_currency(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(ConvertCurrency.currency_name)

@dp.message(ConvertCurrency.currency_name)
async def process_convert_currency_name(message: types.Message, state: FSMContext):
    await state.update_data(currency_name=message.text.upper())
    await message.answer("Введите сумму:")
    await state.set_state(ConvertCurrency.amount)

@dp.message(ConvertCurrency.amount)
async def process_convert_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Введите числовое значение.")
        return

    data = await state.get_data()
    response = requests.get(f"{DATA_MANAGER_URL}/convert", params={
        "currency_name": data["currency_name"],
        "amount": amount
    })

    if response.status_code == 200:
        converted = response.json().get("converted_amount")
        if converted is not None:
            await message.answer(f"Сконвертированная сумма: {converted} руб.")
        else:
            await message.answer("Ошибка при конвертации.")
    else:
        await message.answer("Ошибка от сервера при конвертации.")
    await state.clear()

# Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())