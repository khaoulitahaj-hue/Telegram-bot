import os
import logging
from datetime import datetime, timezone, timedelta
from hijri_converter import Gregorian
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# رمز إجبار الاتجاه من اليمين إلى اليسار (Right-to-Left Mark)
RLM = "\u200f"

# متغيرات حالة القائمة والبيانات في الذاكرة
is_registration_open = True
roles_dict = {}       # {user_id: {"name": str, "username": str, "read": bool, "similar": bool}}
listeners_dict = {}   # {user_id: {"name": str, "username": str}}
excused_dict = {}     # {user_id: {"name": str, "username": str}}

def get_formatted_header():
    """توليد ترويسة التاريخ والوقت بتوقيت مصر بتنسيق متوازن"""
    egypt_offset = timedelta(hours=3) # توقيت مصر UTC+3
    now = datetime.now(timezone.utc) + egypt_offset
    hijri_date = Gregorian(now.year, now.month, now.day).to_hijri()
    
    gregorian_str = now.strftime("%Y / %m / %d")
    hijri_str = f"{hijri_date.year} / {hijri_date.month} / {hijri_date.day}"
    time_str = now.strftime("%I:%M %p")
    
    header = (
        f"❖════════════════════❖\n"
        f"       🗓️ التاريخ الميلادي : {gregorian_str}\n"
        f"       🌙 التاريخ الهجري : {hijri_str}\n"
        f"       ⏰ الساعة (مصر) : {time_str}\n"
        f"❖════════════════════❖\n"
        f"         🌷 رضا الرحمن مبتغانا 🌷\n"
        f"─── ❖ ───\n"
    )
    return header

def generate_full_caption():
    """بناء النص الكامل للقائمة مع إجبار المحاذاة لليمين باستخدام RLM"""
    caption = get_formatted_header() + "\n"
    
    # 1. قسم أدوار الغاليات
    caption += f"{RLM}🏷️ أدوار الغاليات :\n"
    if roles_dict:
        for idx, (u_id, data) in enumerate(roles_dict.items(), 1):
            user_text = f"{data['name']}"
            if data['username']:
                user_text += f" (@{data['username']})"
                
            line = f"{RLM}{idx}-🌷 {user_text}"
            if data['read']:
                line += " ✅️"
            if data['similar']:
                line += " ☑️"
            caption += f"{line}\n"
    else:
        caption += f"{RLM}لا يوجد أسماء بعد\n"
        
    # 2. قسم المستمعات
    caption += f"\n{RLM}🏷️ المستمعات:\n"
    if listeners_dict:
        for idx, (u_id, data) in enumerate(listeners_dict.items(), 1):
            user_text = f"{data['name']}"
            if data['username']:
                user_text += f" (@{data['username']})"
            caption += f"{RLM}{idx}-🌸 {user_text}\n"
    else:
        caption += f"{RLM}لا يوجد أسماء بعد\n"
        
    # 3. قسم المعتذرات
    caption += f"\n{RLM}🏷️ المعتذرات:\n"
    if excused_dict:
        for idx, (u_id, data) in enumerate(excused_dict.items(), 1):
            user_text = f"{data['name']}"
            if data['username']:
                user_text += f" (@{data['username']})"
            caption += f"{RLM}{idx}-🍂 {user_text}\n"
    else:
        caption += f"{RLM}لا يوجد أسماء بعد\n"
        
    # ختام القائمة
    caption += (
        "\n~~كفآرة آلمــجـلس~~\n\n"
        "\"سُبْحَانَكَ اللَّهُمَّ وَبِحَمْدِكَ، أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا أَنْتَ، "
        "أَسْتَغْفِرُكَ وَأَتُوبُ إِلَيْكَ\""
    )
    
    return caption

def get_keyboard():
    """توليد الأزرار التفاعلية"""
    keyboard = []
    
    if is_registration_open:
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
    """التحقق مما إذا كان مستخدم الأمر أدمن في المجموعة"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if update.effective_chat.type == "private":
        return True
        
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["creator", "administrator"]

# --- الأوامر الثلاثة (للأدمن فقط) ---

async def startliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ هذا الأمر مخصص لأدمن المجموعة فقط.")
        return

    global is_registration_open
    is_registration_open = True
    
    await update.message.reply_text(
        generate_full_caption(),
        reply_markup=get_keyboard()
    )

async def stopliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ هذا الأمر مخصص لأدمن المجموعة فقط.")
        return

    global is_registration_open
    is_registration_open = False
    
    await update.message.reply_text(
        "🛑 تم إيقاف التسجيل (إخفاء زر سجل إسمي) مع الحفاظ على القائمة الحالية.",
        reply_markup=get_keyboard()
    )

async def deleteliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("⚠️ هذا الأمر مخصص لأدمن المجموعة فقط.")
        return

    global roles_dict, listeners_dict, excused_dict, is_registration_open
    roles_dict.clear()
    listeners_dict.clear()
    excused_dict.clear()
    is_registration_open = True
    
    await update.message.reply_text("🗑️ تم مسح كافة القوائم والأسماء بنجاح. يمكنك البدء بقائمة جديدة.")

# --- معالجة الضغط على الأزرار ---

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    full_name = user.first_name + (f" {user.last_name}" if user.last_name else "")
    username = user.username if user.username else ""
    data = query.data

    # 1. زر "سجل إسمي"
    if data == "register_role":
        if not is_registration_open:
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

    # تحديث الرسالة
    await query.edit_message_text(
        generate_full_caption(),
        reply_markup=get_keyboard()
    )

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN:
        raise ValueError("خطأ: التوكن غير موجود! تأكد من إضافته في Railway تحت اسم BOT_TOKEN")

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
