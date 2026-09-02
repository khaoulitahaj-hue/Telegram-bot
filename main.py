import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from hijri_converter import Gregorian
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# إعداد السجلات لمتابعة الأخطاء
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# متغيرات حالة القائمة والبيانات في الذاكرة
is_registration_open = True
roles_dict = {}       # {user_id: {"name": str, "read": bool, "similar": bool}}
listeners_dict = {}   # {user_id: str}
excused_dict = {}     # {user_id: str}

def get_formatted_header():
    """توليد ترويسة التاريخ والوقت بتنسيق متوازن ومحاذى للمنتصف قدر الإمكان"""
    now = datetime.now()
    hijri_date = Gregorian(now.year, now.month, now.day).to_hijri()
    
egypt_time = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%I:%M %p")
    hijri_str = f"{hijri_date.year} / {hijri_date.month} / {hijri_date.day}"
    time_str = now.strftime("%H:%M")
    text += f"⏰ الوقت: {egypt_time}\n"

    header = (
        f"❖════════════════════❖\n"
        f"       🗓️ التاريخ الميلادي : {gregorian_str}\n"
        f"       🌙 التاريخ الهجري : {hijri_str}\n"
        f"       ⏰ الساعة : {time_str}\n"
        f"❖════════════════════❖\n"
        f"         🌷 رضا الرحمن مبتغانا 🌷\n"
        f"─── ❖ ───\n"
    )
    return header

def generate_full_caption():
    """بناء النص الكامل للقائمة بجميع أقسامها وترقيمها بالجهة اليمنى"""
    caption = get_formatted_header() + "\n"
    
    # 1. قسم أدوار الغاليات
    caption += "🏷️ أدوار الغاليات :\n"
    if roles_dict:
        for idx, (u_id, data) in enumerate(roles_dict.items(), 1):
            line = f"🌹 {i}. \u200e{name}\n"
            if data['read']:
                line += " ✅️"
            if data['similar']:
                line += " ☑️"
            caption += f"{line}\n"
    else:
        caption += "لا يوجد أسماء بعد\n"
        
    # 2. قسم المستمعات
    caption += "\n🏷️ المستمعات:\n"
    if listeners_dict:
        for idx, (u_id, name) in enumerate(listeners_dict.items(), 1):
            caption += f"🌸 {i}. \u200e{name}\n"
    else:
        caption += "لا يوجد أسماء بعد\n"
        
    # 3. قسم المعتذرات
    caption += "\n🏷️ المعتذرات:\n"
    if excused_dict:
        for idx, (u_id, name) in enumerate(excused_dict.items(), 1):
            caption += f"🌺 {i}. \u200e{name}\n"

    else:
        caption += "لا يوجد أسماء بعد\n"
        
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
    
    # أزرار التسجيل (تظهر فقط إذا كان التسجيل مفتوحاً)
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
    
    # السماح بالتجربة إن كانت المحادثة خاصة
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
    is_registration_open = False  # إخفاء زر "سجل إسمي" مع الإبقاء على باقي البيانات
    
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
    data = query.data

    # 1. زر "سجل إسمي"
    if data == "register_role":
        if not is_registration_open:
            await query.answer("التسجيل مغلق حالياً!", show_alert=True)
            return
        listeners_dict.pop(user_id, None)
        excused_dict.pop(user_id, None)
        if user_id not in roles_dict:
            roles_dict[user_id] = {"name": full_name, "read": False, "similar": False}

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
        listeners_dict[user_id] = full_name

    # 5. زر "معتذرة"
    elif data == "register_excused":
        roles_dict.pop(user_id, None)
        listeners_dict.pop(user_id, None)
        excused_dict[user_id] = full_name

    # 6. زر "أحذف إسمي"
    elif data == "delete_name":
        roles_dict.pop(user_id, None)
        listeners_dict.pop(user_id, None)
        excused_dict.pop(user_id, None)

    # تحديث الرسالة تلقائياً بالتنسيق الجديد
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
