import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F
from aiogram.client.default import DefaultBotProperties
from PIL import Image

TOKEN = "8386598513:AAFv3PWegrToJ_G8FntEfFkpYLjWxckESmA"
ADMIN_ID = 8397359520
mandatory_channels = []

LANGUAGES = {
    "uz": {
        "not_subscribed": "Avval kanalga obuna bo‘ling!",
        "ask_pdf": "Rasm saqlandi ✅\nPDF fayl nomini kiriting (masalan: MyPhotos):",
        "send_images": "📷 PDFga aylantirish uchun rasmlarni yuboring!"
    },
    "en": {
        "not_subscribed": "Please subscribe to the channel first!",
        "ask_pdf": "Image saved ✅\nEnter PDF file name (e.g., MyPhotos):",
        "send_images": "📷 Send images to convert into PDF!"
    },
    "ru": {
        "not_subscribed": "Сначала подпишитесь на канал!",
        "ask_pdf": "Изображение сохранено ✅\nВведите имя PDF файла (например: MyPhotos):",
        "send_images": "📷 Отправьте изображения для преобразования в PDF!"
    }
}

user_data = {}

class PDFStates(StatesGroup):
    waiting_images = State()
    waiting_pdf_name = State()

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

def language_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇺🇿 O‘zbek", callback_data="lang_uz")
    kb.button(text="🇬🇧 English", callback_data="lang_en")
    kb.button(text="🇷🇺 Русский", callback_data="lang_ru")
    kb.adjust(1)
    return kb.as_markup()

async def check_subscription(user_id: int) -> bool:
    for channel in mandatory_channels:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await message.answer("Tilni tanlang / Choose language / Выберите язык:", reply_markup=language_keyboard())

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_data[callback.from_user.id] = {"lang": lang, "images": []}
    await callback.message.answer(LANGUAGES[lang]["send_images"])
    await state.set_state(PDFStates.waiting_images)

@dp.message(Command("language"))
async def change_language(message: types.Message):
    await message.answer("Tilni tanlang / Choose language / Выберите язык:", reply_markup=language_keyboard())

# Rasm qabul qilish va darhol PDF nomini so‘rash
@dp.message(PDFStates.waiting_images, F.photo)
async def collect_images(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = user_data[user_id]["lang"]

    if not await check_subscription(user_id):
        if mandatory_channels:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"📢 {ch}", url=f"https://t.me/{ch.lstrip('@')}")] 
                    for ch in mandatory_channels
                ]
            )
            await message.answer(LANGUAGES[lang]["not_subscribed"], reply_markup=kb)
        else:
            await message.answer(LANGUAGES[lang]["not_subscribed"])
        return

    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_name = f"{user_id}_{photo.file_id}.jpg"
    await bot.download_file(file.file_path, file_name)

    user_data[user_id]["images"].append(file_name)
    await message.answer(LANGUAGES[lang]["ask_pdf"])
    await state.set_state(PDFStates.waiting_pdf_name)

# PDF yaratish
@dp.message(PDFStates.waiting_pdf_name)
async def make_pdf(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    pdf_name = f"{message.text}.pdf"

    images = [Image.open(img).convert("RGB") for img in user_data[user_id]["images"]]
    images[0].save(pdf_name, save_all=True, append_images=images[1:])

    await message.answer_document(types.FSInputFile(pdf_name))

    for img in user_data[user_id]["images"]:
        os.remove(img)
    os.remove(pdf_name)
    user_data[user_id]["images"] = []
    await state.clear()

# Admin panel
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistikani ko‘rish", callback_data="stats")],
        [InlineKeyboardButton(text="➕ Kanal qo‘shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="➖ Kanal o‘chirish", callback_data="remove_channel")]
    ])
    await message.answer("Admin panel:", reply_markup=kb)

@dp.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer(f"Foydalanuvchilar soni: {len(user_data)}")

@dp.callback_query(F.data == "add_channel")
async def add_channel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer("Kanal username yuboring (masalan: @mychannel)")

@dp.message(F.text.startswith("@"))
async def save_channel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    mandatory_channels.append(message.text)
    await message.answer(f"Kanal qo‘shildi ✅ {message.text}")

@dp.callback_query(F.data == "remove_channel")
async def remove_channel(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    if not mandatory_channels:
        await callback.message.answer("Majburiy kanal yo‘q ❌")
        return
    channel = mandatory_channels.pop()
    await callback.message.answer(f"Kanal o‘chirildi ❌ {channel}")

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())