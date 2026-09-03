import os
import logging
from datetime import datetime, timezone, timedelta
from hijri_converter import Gregorian
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# إعداد السجلات
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# محرف RLM المخفي (Right-to-Left Mark) لإجبار المحاذاة لليمين للأسماء اللاتينية
RLM = "\u200f"

# سطر أوراق الشجر الفاصل بين القوائم
SEPARATOR = f"{RLM}🍃🍃🍃🍃🍃🍃🍃🍃🍃\n"

# ذاكرة متكاملة مستقلة لكل مجموعة
groups_data = {}

def get_group_storage(chat_id: int):
    """جلب أو إنشاء ذاكرة مستقلة بناءً على معرف المجموعة الفريد"""
    if chat_id not in groups_data:
        groups_data[chat_id] = {
            "open": True,
            "roles": {},      # {user_id: {"name": str, "username": str, "read": bool, "similar": bool}}
            "listeners": {},  # {user_id: {"name": str, "username": str}}
            "excused": {}     # {user_id: {"name": str, "username": str}}
        }
    return groups_data[chat_id]

def get_formatted_header():
    """توليد الترويسة بالتاريخ الميلادي والهجري وتوقيت مصر بخط عريض"""
    egypt_offset = timedelta(hours=3)  # توقيت مصر UTC+3
    now = datetime.now(timezone.utc) + egypt_offset
    hijri_date = Gregorian(now.year, now.month, now.day).to_hijri()
    
    gregorian_str = now.strftime("%Y / %m / %d")
    hijri_str = f"{hijri_date.year} / {hijri_date.month} / {hijri_date.day}"
    time_str = now.strftime("%I:%M %p")
    
    header = (
        f"{RLM}<b>❖════════════════════❖</b>\n"
        f"{RLM}       🗓️ <b>التاريخ الميلادي :</b> {gregorian_str}\n"
        f"{RLM}       🌙 <b>التاريخ الهجري :</b> {hijri_str}\n"
        f"{RLM}       ⏰ <b>الساعة (مصر) :</b> {time_str}\n"
        f"{RLM}<b>❖════════════════════❖</b>\n"
        f"{RLM}         🌷 <b>رضا الرحمن مبتغانا</b> 🌷\n"
        f"{RLM}             <b>─── ❖ ───<b>\n"
    )
    return header

def generate_full_caption(chat_id: int):
    """إنشاء القائمة مع السطور الفاصلة بين الأقسام"""
    storage = get_group_storage(chat_id)
    roles_dict = storage["roles"]
    listeners_dict = storage["listeners"]
    excused_dict = storage["excused"]

    caption = get_formatted_header() + "\n"
    
    # 1. قسم أدوار الغاليات
    caption += f"{RLM}<b>🏷️ أدوار الغاليات :</b>\n"
    if roles_dict:
        for idx, (u_id, data) in enumerate(roles_dict.items(), 1):
            user_text = f"<b>{data['name']}</b>"
            if data['username']:
                user_text += f" (@{data['username']})"
                
            line = f"{RLM}<b>{idx}-🌷</b> {user_text}"
            if data['read']:
                line += " ✅️"
            if data['similar']:
                line += " ☑️"
            caption += f"{line}\n"
    else:
        caption += f"{RLM}<i>لا يوجد أسماء بعد</i>\n"
        
    # فاصل بين الأدوار والمستمعات
    caption += f"\n{SEPARATOR}\n"

    # 2. قسم المستمعات
    caption += f"{RLM}<b>🏷️ المستمعات:</b>\n"
    if listeners_dict:
        for idx, (u_id, data) in enumerate(listeners_dict.items(), 1):
            user_text = f"<b>{data['name']}</b>"
            if data['username']:
                user_text += f" (@{data['username']})"
            caption += f"{RLM}<b>{idx}-🌸</b> {user_text}\n"
    else:
        caption += f"{RLM}<i>لا يوجد أسماء بعد</i>\n"
        
    # فاصل بين المستمعات والمعتذرات
    caption += f"\n{SEPARATOR}\n"

    # 3. قسم المعتذرات
    caption += f"{RLM}<b>🏷️ المعتذرات:</b>\n"
    if excused_dict:
        for idx, (u_id, data) in enumerate(excused_dict.items(), 1):
            user_text = f"<b>{data['name']}</b>"
            if data['username']:
                user_text += f" (@{data['username']})"
            caption += f"{RLM}<b>{idx}-🍂</b> {user_text}\n"
    else:
        caption += f"{RLM}<i>لا يوجد أسماء بعد</i>\n"
        
    # كفارة المجلس
    caption += (
        f"\n{RLM}<s>كفآرة آلمــجـلس <s>\n\n"
        f"{RLM}<b>\"سُبْحَانَكَ اللَّهُمَّ وَبِحَمْدِكَ، أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا أَنْتَ، "
        f"أَسْتَغْفِرُكَ وَأَتُوبُ إِلَيْكَ\"</b>"
    )
    
    return caption

def get_keyboard(chat_id: int):
    """توليد الأزرار التفاعلية"""
    storage = get_group_storage(chat_id)
    keyboard = []
    
    if storage["open"]:
        keyboard.append([
            InlineKeyboardButton("🔘 سجل إسمي", callback_data="register_role"),
            InlineKeyboardButton("✅️ قرأت", callback_data="toggle_read"),
        ])
    
    keyboard.extend([
        [
            InlineKeyboardButton("🎧 مستمعة", callback_data="register_listener"),
            InlineKeyboardButton("🚫 معتذرة", callback_data="register_excused"),
        ],
        [
            InlineKeyboardButton("☑️ متشابهات", callback_data="toggle_similar"),
            InlineKeyboardButton("❌️ أحذف إسمي", callback_data="delete_name"),
        ]
    ])
    
    return InlineKeyboardMarkup(keyboard)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من صلاحية المشرف"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if update.effective_chat.type == "private":
        return True
        
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["creator", "administrator"]

# --- أوامر الأدمن ---

async def startliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ هذا الأمر مخصص لأدمن المجموعة فقط.")
        return

    chat_id = update.effective_chat.id
    storage = get_group_storage(chat_id)
    storage["open"] = True
    
    await update.message.reply_text(
        generate_full_caption(chat_id),
        reply_markup=get_keyboard(chat_id),
        parse_mode=ParseMode.HTML
    )

async def stopliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ هذا الأمر مخصص لأدمن المجموعة فقط.")
        return

    chat_id = update.effective_chat.id
    storage = get_group_storage(chat_id)
    storage["open"] = False
    
    await update.message.reply_text(
        "🛑 <b>تم إيقاف التسجيل</b> (إخفاء زر سجل إسمي) مع الحفاظ على القائمة الحالية لهذه المجموعة.",
        reply_markup=get_keyboard(chat_id),
        parse_mode=ParseMode.HTML
    )

async def deleteliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ هذا الأمر مخصص لأدمن المجموعة فقط.")
        return

    chat_id = update.effective_chat.id
    storage = get_group_storage(chat_id)
    storage["roles"].clear()
    storage["listeners"].clear()
    storage["excused"].clear()
    storage["open"] = True
    
    await update.message.reply_text("🗑️ <b>تم مسح قائمة هذه المجموعة بنجاح.</b> يمكنك البدء بقائمة جديدة.", parse_mode=ParseMode.HTML)

# --- معالج الأزرار التفاعلية ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    storage = get_group_storage(chat_id)
    roles_dict = storage["roles"]
    listeners_dict = storage["listeners"]
    excused_dict = storage["excused"]

    user = query.from_user
    user_id = user.id
    full_name = user.first_name + (f" {user.last_name}" if user.last_name else "")
    username = user.username if user.username else ""
    data = query.data

    # 1. زر "سجل إسمي"
    if data == "register_role":
        if not storage["open"]:
            await query.answer("التسجيل مغلق حالياً!", show_alert=True)
            return
        listeners_dict.pop(user_id, None)
        excused_dict.pop(user_id, None)
        if user_id not in roles_dict:
            roles_dict[user_id] = {
                "name": full_name,
                "username": username,
                "read": False,
                "similar": False
            }

    # 2. زر "قرأت"
    elif data == "toggle_read":
        if user_id in roles_dict:
            roles_dict[user_id]["read"] = not roles_dict[user_id]["read"]
        else:
            await query.answer("يجب أن تسجل اسمك أولاً عبر زر (سجل إسمي)!", show_alert=True)
            return

    # 3. زر "متشابهات"
    elif data == "toggle_similar":
        if user_id in roles_dict:
            roles_dict[user_id]["similar"] = not roles_dict[user_id]["similar"]
        else:
            await query.answer("يجب أن تسجل اسمك أولاً عبر زر (سجل إسمي)!", show_alert=True)
            return

    # 4. زر "مستمعة"
    elif data == "register_listener":
        roles_dict.pop(user_id, None)
        excused_dict.pop(user_id, None)
        listeners_dict[user_id] = {"name": full_name, "username": username}

    # 5. زر "معتذرة"
    elif data == "register_excused":
        roles_dict.pop(user_id, None)
        listeners_dict.pop(user_id, None)
        excused_dict[user_id] = {"name": full_name, "username": username}

    # 6. زر "أحذف إسمي"
    elif data == "delete_name":
        roles_dict.pop(user_id, None)
        listeners_dict.pop(user_id, None)
        excused_dict.pop(user_id, None)

    # تحديث نص القائمة مع استخدام HTML
    await query.edit_message_text(
        generate_full_caption(chat_id),
        reply_markup=get_keyboard(chat_id),
        parse_mode=ParseMode.HTML
    )

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        raise ValueError("خطأ: لم يتم العثور على BOT_TOKEN في متغيرات البيئة!")

    app = Application.builder().token(TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("startliste", startliste))
    app.add_handler(CommandHandler("stopliste", stopliste))
    app.add_handler(CommandHandler("deleteliste", deleteliste))
    
    # تسجيل معالج الأزرار
    app.add_handler(CallbackQueryHandler(button_handler))

    # تشغيل البوت
    app.run_polling(allowed_updates=["message", "callback_query", "chat_member"])

if __name__ == "__main__":
    main()
   
