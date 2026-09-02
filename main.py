import os
import logging
from datetime import datetime
from hijri_converter import Hijri
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# إعداد السجلات (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# هَيْكَل تخزين البيانات في الذاكرة
# يمكن استبداله بحفظ في ملف JSON للحفاظ على البيانات عند إيقاف البوت
data_store = {
    "roles": {},       # {user_id: {"name": str, "status": str}} (status: "" أو "✅️" أو "☑️")
    "listeners": {},   # {user_id: str}
    "excused": {},     # {user_id: str}
    "registration_open": True,
    "list_message_id": None,
    "created_at": None,
}

def get_current_time_str():
    """حساب الوقت والتاريخ الميلادي والهجري بصيغة منسقة"""
    now = datetime.now()
    hijri_date = Hijri.fromdate(now.date())
    
    time_str = now.strftime("%H:%M")
    gregorian_str = now.strftime("%Y-%m-%d")
    hijri_str = f"{hijri_date.year}-{hijri_date.month}-{hijri_date.day} هـ"
    
    return f"""🗓 التاريخ الميلادي: {gregorian_str}
التاريخ الهجري: {hijri_str}
الساعة: {time_str}"""

def build_list_text():
    """بناء نص القائمة كاملاً حسب التنسيق المطلوب"""
    time_header = data_store.get("created_at") or get_current_time_str()
    
    text = f"""{time_header}
◉════••• ❖❖ •••════◉     
                🌷 رضا الرحمن مبتغانا 🌷
                       🌷البقرة وجه 🌷 

    •••┈┈┈••❀❀❀••┈┈┈•••

🏷️ أدوار الغاليات :
"""
    # 1. قائمة الأدوار
    if not data_store["roles"]:
        text += "لا يوجد أسماء بعد\n"
    else:
        for idx, (uid, user_info) in enumerate(data_store["roles"].items(), 1):
            name = user_info["name"]
            status = user_info["status"]
            status_text = f" {status}" if status else ""
            text += f"{idx}-🌷 {name}{status_text}\n"

    # 2. قائمة المستمعات
    text += "\n🏷️ المستمعات:\n"
    if not data_store["listeners"]:
        text += "لا يوجد أسماء بعد\n"
    else:
        for idx, (uid, name) in enumerate(data_store["listeners"].items(), 1):
            text += f"{idx}-🌸 {name}\n"

    # 3. قائمة المعتذرات
    text += "\n🏷️ المعتذرات:\n"
    if not data_store["excused"]:
        text += "لا يوجد أسماء بعد\n"
    else:
        for idx, (uid, name) in enumerate(data_store["excused"].items(), 1):
            text += f"{idx}-🍂 {name}\n"

    # الختام
    text += """
~~كفآرة آلمــجـلس~~

"سُبْحَانَكَ اللَّهُمَّ وَبِحَمْدِكَ، أَشْهَدُ أَنْ لَا إِلَهَ إِلَّا أَنْتَ، أَسْتَغْفِرُكَ وَأَتُوبُ إِلَيْكَ\""""
    return text

def get_keyboard():
    """إنشاء أزرار التفاعل"""
    keyboard = []
    
    # يظهر زر التسجيل فقط إذا كان التسجيل مفتوحاً
    if data_store["registration_open"]:
        keyboard.append([InlineKeyboardButton("🔘 سجل إسمي", callback_data="register")])
        
    keyboard.append([
        InlineKeyboardButton("✅️ قرأت", callback_data="read"),
        InlineKeyboardButton("🎧 مستمعة", callback_data="listen"),
    ])
    keyboard.append([
        InlineKeyboardButton("🚫 معتذرة", callback_data="excuse"),
        InlineKeyboardButton("☑️ متشابهات", callback_data="similar"),
    ])
    keyboard.append([InlineKeyboardButton("❌️ أحذف إسمي", callback_data="delete_me")])
    
    return InlineKeyboardMarkup(keyboard)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق مما إذا كان المستخدم أدمن في المجموعة"""
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # إذا كانت الدردشة خاصة
    if update.effective_chat.type == "private":
        return True
        
    member = await context.bot.get_chat_member(chat_id, user_id)
    return member.status in ["creator", "administrator"]

async def startliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الأمر الأول: إظهار أو فتح القائمة (للأدمن فقط)"""
    if not await is_admin(update, context):
        await update.message.reply_text("عذراً، هذا الأمر مخصص للمشرفين فقط.")
        return

    # إذا لم تكن هناك قائمة سابقة أو وقت، يتم إنشاء وقت جديد
    if not data_store["created_at"]:
        data_store["created_at"] = get_current_time_str()
        
    data_store["registration_open"] = True
    
    text = build_list_text()
    reply_markup = get_keyboard()
    
    msg = await update.message.reply_text(text, reply_markup=reply_markup)
    data_store["list_message_id"] = msg.message_id

async def stopliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إيقاف التسجيل مع الإبقاء على البيانات (للأدمن فقط)"""
    if not await is_admin(update, context):
        await update.message.reply_text("عذراً، هذا الأمر مخصص للمشرفين فقط.")
        return

    data_store["registration_open"] = False
    text = build_list_text()
    reply_markup = get_keyboard()
    
    if data_store["list_message_id"]:
        try:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=data_store["list_message_id"],
                text=text,
                reply_markup=reply_markup
            )
            await update.message.reply_text("تم إيقاف خيار (سجل إسمي) مع حفظ بقية البيانات.")
        except Exception as e:
            await update.message.reply_text("تم إيقاف التسجيل.")

async def deleteliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح القائمة وتصفير البيانات لبدء قائمة جديدة (للأدمن فقط)"""
    if not await is_admin(update, context):
        await update.message.reply_text("عذراً، هذا الأمر مخصص للمشرفين فقط.")
        return

    data_store["roles"].clear()
    data_store["listeners"].clear()
    data_store["excused"].clear()
    data_store["registration_open"] = True
    data_store["list_message_id"] = None
    data_store["created_at"] = None
    
    await update.message.reply_text("تم مسح القائمة بنجاح. يمكنك الآن البدء بقائمة جديدة باستخدام /startliste")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحكم في الأزرار والتفاعل مع الطالبات"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    full_name = user.full_name
    action = query.data

    # دالة مساعدة لحذف المستخدم من جميع القوائم أولاً
    def remove_from_all():
        data_store["roles"].pop(user_id, None)
        data_store["listeners"].pop(user_id, None)
        data_store["excused"].pop(user_id, None)

    if action == "register":
        if not data_store["registration_open"]:
            return
        remove_from_all()
        data_store["roles"][user_id] = {"name": full_name, "status": ""}

    elif action == "read":
        if user_id in data_store["roles"]:
            data_store["roles"][user_id]["status"] = "✅️"
        else:
            remove_from_all()
            data_store["roles"][user_id] = {"name": full_name, "status": "✅️"}

    elif action == "similar":
        if user_id in data_store["roles"]:
            data_store["roles"][user_id]["status"] = "☑️"
        else:
            remove_from_all()
            data_store["roles"][user_id] = {"name": full_name, "status": "☑️"}

    elif action == "listen":
        remove_from_all()
        data_store["listeners"][user_id] = full_name

    elif action == "excuse":
        remove_from_all()
        data_store["excused"][user_id] = full_name

    elif action == "delete_me":
        remove_from_all()

    # تحديث نص الرسالة بنفس القائمة
    new_text = build_list_text()
    new_keyboard = get_keyboard()
    
    try:
        await query.edit_message_text(text=new_text, reply_markup=new_keyboard)
    except Exception:
        pass # يتجاهل الخطأ في حال لم يتغير النص

def main():
    TOKEN = os.getenv("BOT_TOKEN")
    
    app = Application.builder().token(TOKEN).build()

    # تسجيل الأوامر
    app.add_handler(CommandHandler("startliste", startliste))
    app.add_handler(CommandHandler("stopliste", stopliste))
    app.add_handler(CommandHandler("deleteliste", deleteliste))
    
    # تسجيل معالج الأزرار
    app.add_handler(CallbackQueryHandler(button_handler))

    # تشغيل البوت
    app.run_polling()

if __name__ == "__main__":
    main()
