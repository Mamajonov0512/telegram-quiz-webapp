import logging
import asyncio
from io import BytesIO
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    WebAppInfo, 
    Message, 
    CallbackQuery,
    BufferedInputFile
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, ADMIN_IDS, WEB_APP_URL, DEFAULT_TEST_QUESTIONS_COUNT, DEFAULT_TEST_DURATION_MINUTES
import database as db
from parser import parse_file

logger = logging.getLogger(__name__)

bot: Bot = None
dp: Dispatcher = Dispatcher()

def get_bot():
    global bot
    if bot is None and BOT_TOKEN:
        bot = Bot(token=BOT_TOKEN)
    return bot

def get_main_keyboard(user_id: int, is_allowed: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    if is_allowed:
        # If WEB_APP_URL is configured, create WebApp button
        app_url = WEB_APP_URL.strip() if WEB_APP_URL else f"http://127.0.0.1:8000"
        builder.button(
            text="🚀 Testni boshlash (Web App)", 
            web_app=WebAppInfo(url=f"{app_url}?v=1")
        )
        builder.button(text="📊 Mening natijalarim", callback_data="my_results")
    else:
        builder.button(text="🆔 Mening Telegram ID", callback_data="show_my_id")

    builder.button(text="ℹ️ Bot haqida", callback_data="about_bot")
    
    if user_id in ADMIN_IDS:
        builder.button(text="⚙️ Admin panel", callback_data="admin_panel")

    builder.adjust(1)
    return builder.as_markup()

def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Ruxsat berilganlar", callback_data="admin_users")
    builder.button(text="➕ Foydalanuvchi qo'shish", callback_data="admin_add_user_help")
    builder.button(text="📈 Natijalar Tahlili", callback_data="admin_analytics")
    builder.button(text="📥 Excel hisobot (.xlsx)", callback_data="admin_export_excel")
    builder.button(text="📁 Test yuklash (Shablonlar)", callback_data="admin_templates")
    builder.button(text="🔄 Rejimni o'zgartirish", callback_data="admin_toggle_mode")
    builder.button(text="◀️ Orqaga", callback_data="back_to_main")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

# --- COMMAND HANDLERS ---

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    full_name = message.from_user.full_name or "Foydalanuvchi"
    username = message.from_user.username or ""
    
    is_allowed = db.is_user_allowed(user_id)
    whitelist_mode = db.get_setting("whitelist_enabled", "true").lower() == "true"
    duration = db.get_setting("duration_minutes", str(DEFAULT_TEST_DURATION_MINUTES))
    q_count = db.get_setting("questions_per_test", str(DEFAULT_TEST_QUESTIONS_COUNT))

    if is_allowed:
        text = (
            f"👋 <b>Assalomu alaykum, {full_name}!</b>\n\n"
            f"🎓 <b>Onlayn Test topshirish tizimiga xush kelibsiz!</b>\n\n"
            f"📌 <b>Test qoidalari:</b>\n"
            f"• Savollar soni: <b>{q_count} ta</b>\n"
            f"• Ajratilgan vaqt: <b>{duration} daqiqa</b>\n"
            f"• Har bir savolga bittadan to'g'ri javob mavjud.\n"
            f"• Vaqt tugagach test avtomatik yakunlanadi.\n\n"
            f"Pastdagi <b>«Testni boshlash (Web App)»</b> tugmasini bosib testni boshlashingiz mumkin."
        )
    else:
        text = (
            f"👋 <b>Assalomu alaykum, {full_name}!</b>\n\n"
            f"⛔ <b>Kechirasiz, sizga test topshirish uchun ruxsat berilmagan!</b>\n\n"
            f"Tizimda faqat ro'yxatga olingan foydalanuvchilar test topshira oladi.\n\n"
            f"Sizning Telegram ID raqamingiz:\n"
            f"👉 <code>{user_id}</code>\n\n"
            f"<i>Ruxsat olish uchun ushbu ID raqamni administratorga yuboring.</i>"
        )
        
    await message.answer(
        text, 
        reply_markup=get_main_keyboard(user_id, is_allowed),
        parse_mode="HTML"
    )

@dp.message(Command("id"))
async def cmd_id(message: Message):
    user_id = message.from_user.id
    is_allowed = db.is_user_allowed(user_id)
    status_text = "✅ Ruxsat berilgan" if is_allowed else "⛔ Ruxsat yo'q"
    
    await message.answer(
        f"👤 <b>Sizning ma'lumotlaringiz:</b>\n"
        f"• Telegram ID: <code>{user_id}</code> (nusxalash uchun bosing)\n"
        f"• Ism: <b>{message.from_user.full_name}</b>\n"
        f"• Holat: {status_text}",
        parse_mode="HTML"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Siz administrator emassiz!")
        return

    stats = db.get_stats()
    whitelist_mode = db.get_setting("whitelist_enabled", "true").lower() == "true"
    mode_text = "🔒 Faqat ruxsat berilgan IDlar" if whitelist_mode else "🔓 Hammaga ochiq"

    text = (
        f"⚙️ <b>ADMINISTRATOR BOSHQARUV PANELI</b>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"• Jami savollar soni: <b>{stats['total_questions']} ta</b>\n"
        f"• Ruxsat berilgan foydalanuvchilar: <b>{stats['total_users']} ta</b>\n"
        f"• Topshirilgan testlar: <b>{stats['total_tests_taken']} ta</b>\n"
        f"• O'rtacha natija: <b>{stats['avg_score']}%</b>\n\n"
        f"🔐 <b>Kirish rejimi:</b> {mode_text}\n\n"
        f"<i>Quyidagi tugmalardan birini tanlang yoki savollar faylini (.xlsx, .docx, .json, .txt) to'g'ridan-to'g'ri botga yuboring.</i>"
    )
    await message.answer(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")

@dp.message(Command("add"))
async def cmd_add_user(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return

    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer(
            "⚠️ <b>Noto'g'ri format!</b>\nFoydalanish: <code>/add 12345678 Ism Familiya</code>",
            parse_mode="HTML"
        )
        return

    target_id = int(parts[1])
    target_name = " ".join(parts[2:]) if len(parts) > 2 else "Foydalanuvchi"

    success = db.add_allowed_user(
        telegram_id=target_id,
        full_name=target_name,
        added_by=user_id,
        notes="Bot orqali qo'shildi"
    )

    if success:
        await message.answer(
            f"✅ <b>Foydalanuvchi muvaffaqiyatli qo'shildi!</b>\n"
            f"• ID: <code>{target_id}</code>\n"
            f"• Ism: <b>{target_name}</b>\n\n"
            f"Endi ushbu foydalanuvchi test topshira oladi.",
            parse_mode="HTML"
        )
        # Notify user if bot can reach them
        try:
            bot_inst = get_bot()
            await bot_inst.send_message(
                target_id,
                f"🎉 <b>Tabriklaymiz!</b> Sizga test topshirish uchun ruxsat berildi.\n"
                f"Boshlash uchun /start buyrug'ini bosing.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        await message.answer("❌ Xatolik yuz berdi!")

@dp.message(Command("del"))
async def cmd_del_user(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return

    parts = message.text.strip().split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ <b>Foydalanish:</b> <code>/del 12345678</code>", parse_mode="HTML")
        return

    target_id = int(parts[1])
    success = db.remove_allowed_user(target_id)
    if success:
        await message.answer(f"✅ ID <code>{target_id}</code> ruxsat ro'yxatidan o'chirildi.", parse_mode="HTML")
    else:
        await message.answer("❌ O'chirishda xatolik yuz berdi.", parse_mode="HTML")

@dp.message(Command("users"))
async def cmd_users(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return

    users = db.get_allowed_users()
    if not users:
        await message.answer("ℹ️ Ruxsat berilgan foydalanuvchilar ro'yxati hozircha bo'sh.")
        return

    text = f"👥 <b>Ruxsat berilgan foydalanuvchilar ({len(users)} ta):</b>\n\n"
    for idx, u in enumerate(users[:30], start=1):
        status_icon = "🟢" if u["is_active"] else "🔴"
        uname = f"@{u['username']}" if u.get("username") else "—"
        text += f"{idx}. {status_icon} <code>{u['telegram_id']}</code> | {u['full_name']} ({uname})\n"
    
    if len(users) > 30:
        text += f"\n<i>...va yana {len(users) - 30} ta foydalanuvchi.</i>"

    await message.answer(text, parse_mode="HTML")

# --- FILE UPLOAD HANDLER ---

@dp.message(F.document)
async def handle_document_upload(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Faqat administratorlar test fayllarini yuklashi mumkin.")
        return

    doc = message.document
    filename = doc.file_name or "test_file.txt"
    ext = filename.lower().split(".")[-1]

    if ext not in ["xlsx", "xls", "docx", "json", "txt"]:
        await message.answer(
            "⚠️ <b>Qo'llab-quvvatlanmaydigan format!</b>\n"
            "Iltimos, <code>.xlsx</code>, <code>.docx</code>, <code>.json</code> yoki <code>.txt</code> formatdagi fayl yuboring.",
            parse_mode="HTML"
        )
        return

    status_msg = await message.answer(f"⏳ <b>{filename}</b> fayli qabul qilindi, tahlil qilinmoqda...", parse_mode="HTML")
    
    try:
        bot_inst = get_bot()
        file_io = BytesIO()
        file = await bot_inst.get_file(doc.file_id)
        await bot_inst.download_file(file.file_path, destination=file_io)
        file_bytes = file_io.getvalue()

        questions, errors = parse_file(filename, file_bytes)
        
        if not questions:
            err_text = "\n".join(errors[:5]) if errors else "Fayldan hech qanday to'g'ri test topilmadi."
            await status_msg.edit_text(
                f"❌ <b>Faylni yuklashda xatolik yuz berdi:</b>\n\n{err_text}\n\n"
                f"<i>Namuna shablonlarni olish uchun /admin bo'limiga kiring.</i>",
                parse_mode="HTML"
            )
            return

        # Bulk save to DB
        saved_count = db.bulk_add_questions(questions)
        total_in_db = db.get_questions_count()

        result_text = (
            f"✅ <b>Fayl muvaffaqiyatli qabul qilindi!</b>\n\n"
            f"• Fayl nomi: <code>{filename}</code>\n"
            f"• Tahlil qilindi: <b>{len(questions)} ta</b> test savoli\n"
            f"• Bazaga qo'shildi: <b>{saved_count} ta</b>\n"
            f"• Bazadagi jami savollar: <b>{total_in_db} ta</b>\n"
        )

        if errors:
            result_text += f"\n⚠️ <i>{len(errors)} ta savolda kamchilik borligi sababli o'tkazib yuborildi.</i>"

        await status_msg.edit_text(result_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error processing uploaded document: {e}")
        await status_msg.edit_text(f"❌ Faylni qayta ishlashda xatolik: {str(e)}")

# --- CALLBACK QUERY HANDLERS ---

@dp.callback_query(F.data == "show_my_id")
async def cb_show_id(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.answer(f"Sizning ID: {user_id}", show_alert=True)

@dp.callback_query(F.data == "about_bot")
async def cb_about_bot(callback: CallbackQuery):
    text = (
        "ℹ️ <b>Onlayn Test Tizimi haqida</b>\n\n"
        "Ushbu bot va Telegram Web App ilovasi orqali foydalanuvchilar qulay va interaktiv ko'rinishda test topshirishlari mumkin.\n\n"
        "✨ <b>Asosiy imkoniyatlar:</b>\n"
        "• Telegram Web App (zamonaviy mobil interfeys)\n"
        "• 50 ta savol va real vaqt hisoblagich taymer\n"
        "• Savollarni Excel (.xlsx), Word (.docx), JSON va TXT orqali yuklash\n"
        "• Telegram ID orqali xavfsiz ruxsat tizimi (Whitelist)\n"
        "• Har bir test natijasini tahlil qilish va xatolar ustida ishlash"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "my_results")
async def cb_my_results(callback: CallbackQuery):
    user_id = callback.from_user.id
    results = db.get_user_results(user_id, limit=5)
    
    if not results:
        await callback.answer("Siz hali hech qanday test topshirmagansiz.", show_alert=True)
        return

    text = "📊 <b>Sizning oxirgi natijalaringiz:</b>\n\n"
    for idx, r in enumerate(results, start=1):
        mins = r['time_spent_seconds'] // 60
        secs = r['time_spent_seconds'] % 60
        text += (
            f"<b>{idx}. Sana: {r['completed_at']}</b>\n"
            f"• Natija: <b>{r['correct_answers']} / {r['total_questions']}</b> ({r['score_percentage']}%)\n"
            f"• Sarflangan vaqt: {mins} daq {secs} son\n\n"
        )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    stats = db.get_stats()
    whitelist_mode = db.get_setting("whitelist_enabled", "true").lower() == "true"
    mode_text = "🔒 Faqat ruxsat berilgan IDlar" if whitelist_mode else "🔓 Hammaga ochiq"

    text = (
        f"⚙️ <b>ADMINISTRATOR BOSHQARUV PANELI</b>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"• Savollar: <b>{stats['total_questions']} ta</b>\n"
        f"• Ruxsat berilganlar: <b>{stats['total_users']} ta</b>\n"
        f"• Topshirilgan testlar: <b>{stats['total_tests_taken']} ta</b>\n"
        f"• O'rtacha ball: <b>{stats['avg_score']}%</b>\n\n"
        f"🔐 <b>Kirish rejimi:</b> {mode_text}"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    users = db.get_allowed_users()
    text = f"👥 <b>Ruxsat berilgan foydalanuvchilar ({len(users)} ta):</b>\n\n"
    for idx, u in enumerate(users[:20], start=1):
        status_icon = "🟢" if u["is_active"] else "🔴"
        text += f"{idx}. {status_icon} <code>{u['telegram_id']}</code> | {u['full_name']}\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data="admin_panel")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_add_user_help")
async def cb_add_user_help(callback: CallbackQuery):
    text = (
        "➕ <b>Foydalanuvchi qo'shish yo'riqnomasi:</b>\n\n"
        "Foydalanuvchiga ruxsat berish uchun quyidagi buyruqni yuboring:\n"
        "<code>/add TELEGRAM_ID Ism Familiya</code>\n\n"
        "<b>Misol:</b>\n"
        "<code>/add 123456789 Alisher Usmonov</code>\n\n"
        "O'chirish uchun:\n"
        "<code>/del TELEGRAM_ID</code>"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Orqaga", callback_data="admin_panel")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_templates")
async def cb_admin_templates(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    from pathlib import Path
    samples_dir = Path(__file__).resolve().parent / "samples"
    
    excel_path = samples_dir / "test_shablon.xlsx"
    txt_path = samples_dir / "test_shablon.txt"
    json_path = samples_dir / "test_shablon.json"

    bot_inst = get_bot()
    chat_id = callback.message.chat.id

    await callback.message.answer("📁 <b>Namuna shablon fayllar:</b>\nFaylni to'ldirib, botga to'g'ridan-to'g'ri yuborishingiz mumkin.", parse_mode="HTML")

    if excel_path.exists():
        with open(excel_path, "rb") as f:
            await bot_inst.send_document(
                chat_id, 
                BufferedInputFile(f.read(), filename="test_shablon.xlsx"),
                caption="📊 Excel shabloni (.xlsx)"
            )
    if txt_path.exists():
        with open(txt_path, "rb") as f:
            await bot_inst.send_document(
                chat_id, 
                BufferedInputFile(f.read(), filename="test_shablon.txt"),
                caption="📝 Oddiy matn shabloni (.txt)"
            )

    await callback.answer("Shablonlar yuborildi!")

@dp.callback_query(F.data == "admin_toggle_mode")
async def cb_toggle_mode(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    current = db.get_setting("whitelist_enabled", "true").lower() == "true"
    new_val = "false" if current else "true"
    db.set_setting("whitelist_enabled", new_val)

    new_mode_text = "🔒 Faqat ruxsat berilgan IDlar" if new_val == "true" else "🔓 Hammaga ochiq"
    await callback.answer(f"Rejim o'zgartirildi: {new_mode_text}", show_alert=True)
    await cb_admin_panel(callback)

@dp.callback_query(F.data == "back_to_main")
async def cb_back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_allowed = db.is_user_allowed(user_id)
    await callback.message.edit_text(
        "Asosiy menyu:",
        reply_markup=get_main_keyboard(user_id, is_allowed)
    )
    await callback.answer()

@dp.message(Command("analytics"))
@dp.callback_query(F.data == "admin_analytics")
async def handle_analytics(event: Message | CallbackQuery):
    user_id = event.from_user.id
    if user_id not in ADMIN_IDS:
        if isinstance(event, CallbackQuery):
            await event.answer("Ruxsat yo'q!", show_alert=True)
        else:
            await event.answer("⛔ Faqat administratorlar uchun!")
        return

    analytics = db.get_detailed_analytics()
    total_tests = analytics["total_tests"]

    if total_tests == 0:
        msg = "ℹ️ Hozircha hech qanday test topshirilmagan."
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    text = (
        "📈 <b>TEST NATIJALARI CHUQUR TAHLILI</b>\n\n"
        f"• Topshirilgan testlar: <b>{total_tests} ta</b>\n"
        f"• Ishtirokchilar: <b>{analytics['unique_users']} nafar</b>\n"
        f"• O'rtacha o'zlashtirish: <b>{analytics['avg_score']}%</b>\n"
        f"• O'tish ko'rsatkichi: <b>{analytics['pass_rate']}%</b> ({analytics['pass_count']} o'tdi / {analytics['fail_count']} o'tmadi)\n"
        f"• O'rtacha sarflangan vaqt: <b>{analytics['avg_time_min']} daqiqa</b>\n\n"
    )

    # Ballar taqsimoti
    dist = analytics["score_distribution"]
    text += (
        "📊 <b>Ballar taqsimoti:</b>\n"
        f"• 80-100% (A'lo): <b>{dist['80-100']} ta</b>\n"
        f"• 60-79% (Yaxshi): <b>{dist['60-79']} ta</b>\n"
        f"• 40-59% (Past): <b>{dist['40-59']} ta</b>\n"
        f"• 0-39% (Qoniqarsiz): <b>{dist['0-39']} ta</b>\n\n"
    )

    # Top students
    if analytics["leaderboard"]:
        text += "🏆 <b>Yetakchi natijalar (Top 5):</b>\n"
        for idx, u in enumerate(analytics["leaderboard"][:5], 1):
            name = u["full_name"] or f"ID: {u['telegram_id']}"
            text += f"{idx}. <b>{name}</b> — {u['best_score']}% (o'rtacha: {u['avg_score']}%)\n"
        text += "\n"

    # Hardest questions
    if analytics["hardest_questions"]:
        text += "⚠️ <b>Eng ko'p xato qilingan savollar (Top 3):</b>\n"
        for idx, q in enumerate(analytics["hardest_questions"][:3], 1):
            q_short = q["question"][:45] + "..." if len(q["question"]) > 45 else q["question"]
            text += f"{idx}. <i>«{q_short}»</i>\n   ❌ Xato foizi: <b>{q['error_rate']}%</b> ({q['wrong_count']}/{q['total_answered']} ta)\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="📥 Excel hisobot (.xlsx)", callback_data="admin_export_excel")
    builder.button(text="◀️ Admin menyu", callback_data="admin_panel")
    builder.adjust(1)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_export_excel")
async def cb_export_excel(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return

    await callback.answer("Excel hisobot tayyorlanmoqda...")
    try:
        excel_bytes = db.generate_results_excel()
        bot_inst = get_bot()
        doc = BufferedInputFile(excel_bytes, filename="test_natijalari_tahlil.xlsx")
        await bot_inst.send_document(
            chat_id=callback.message.chat.id,
            document=doc,
            caption="📊 <b>Barcha test natijalari, reyting va savollar tahlili bo'yicha to'liq Excel hisoboti</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Excel export error: {e}")
        await callback.message.answer(f"❌ Excel yaratishda xatolik: {e}")
