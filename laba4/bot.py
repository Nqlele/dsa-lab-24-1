import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from dotenv import load_dotenv

# Загрузка токена из .env файла
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

# Включаем логирование
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище курсов валют
currency_data = {}

# Состояния
class CurrencyState(StatesGroup):
    waiting_for_currency_name = State()
    waiting_for_currency_rate = State()

class ConvertState(StatesGroup):
    waiting_for_convert_currency = State()
    waiting_for_amount = State()
    
    
    
    
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # сбрасываем текущее состояние
    await message.answer(
        "Бот арбитражник.\n\n"
        "Вот что я умею:\n"
        "/save_currency — создать и сохранить валюту\n"
        "/convert — конвертировать\n"
        "/restart — сброс текущего процесса"
    )    

# Команда /save_currency
@dp.message(Command("save_currency"))
async def cmd_save_currency(message: Message, state: FSMContext):
    await message.answer("название валюты (которую хотим создать):")
    await state.set_state(CurrencyState.waiting_for_currency_name)
    logger.debug("ввод")

@dp.message(CurrencyState.waiting_for_currency_name)
async def process_currency_name(message: Message, state: FSMContext):
    await state.update_data(currency_name=message.text.upper())
    await message.answer(f"курс {message.text.upper()} к рублю:")
    await state.set_state(CurrencyState.waiting_for_currency_rate)

@dp.message(CurrencyState.waiting_for_currency_rate)
async def process_currency_rate(message: Message, state: FSMContext):
    user_data = await state.get_data()
    currency_name = user_data.get("currency_name")

    try:
        rate = float(message.text.replace(",", "."))
        currency_data[currency_name] = rate
        await message.answer(f"Курс {currency_name} к рублю сохранен: {rate}")
        await message.answer("Теперь вы можете использовать команду /convert для конвертации.")
        await state.clear()
    except ValueError:
        await message.answer("введите правильное число")

# Команда /convert
@dp.message(Command("convert"))
async def cmd_convert(message: Message, state: FSMContext):
    await message.answer("название валюты которую хотите обменять")
    await state.set_state(ConvertState.waiting_for_convert_currency)

@dp.message(ConvertState.waiting_for_convert_currency)
async def process_convert_currency(message: Message, state: FSMContext):
    currency = message.text.upper()
    if currency not in currency_data:
        await message.answer("такой валюты у нас нету")
        await state.clear()
        return
    await state.update_data(currency=currency)
    await message.answer(f"введите сумму в валюте {currency}:")
    await state.set_state(ConvertState.waiting_for_amount)

@dp.message(ConvertState.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    user_data = await state.get_data()
    currency = user_data.get("currency")
    try:
        amount = float(message.text.replace(",", "."))
        rate = currency_data[currency]
        rubles = amount * rate
        await message.answer(f"{amount} {currency} = {rubles:.2f} RUB")
        await state.clear()
    except ValueError:
        await message.answer("введите правильное число.")

# Команда /restart — сброс
@dp.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("сброшено. Начните с /save_currency или /convert.")
    logger.debug("сброшено вручную")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
