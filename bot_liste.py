import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# ==== إعدادات يجب تعديلها ====
BOT_TOKEN = "8966926917:AAH_NfukVrf2efJwVREW9nOdQV311YtVeYY"          # التوكن من BotFather
# لا حاجة لكتابة معرفات الأدمينات يدوياً — البوت يتحقق تلقائياً من تيليجرام
# ==============================

# تخزين حالة كل محادثة في الذاكرة (يُعاد تصفيرها عند إعادة تشغيل البوت)
chat_data = {}

HEADER = (
    "الســلآمــ عليكمـ وڕحـمــة ﷲوبــڕڪآته\n\n"
    "❄️اقرأ القرآن لك ، لقلبك ، لحث خطاك إلى الجنة \n"
    "لشفاءك ، لسقيا روحك العطشى.❄️\n"
    "❄️متنعماً ، مترسلًا ، لا عجلاً ؛ لكي تحيا ❄️\n\n"
    "■■■■ رضا الرحمن مبتغانا ■■■■\n\n"
    "أسماء الطالبات:\n\n"
)

FOOTER = (
    "\n\n❄كفآرة آلمــجـلس❄\n\n"
    "ســبــــحـآنك آللهمــ وبــــحمــدك\n"
    "آشــهد آن لآ آله آلآ آنت\n"
    "آســتغـفرك وآتوب  إليك\n"
    "❄ــــــــــــــــــ🌿ــــــــــــــــــــ❄"
)

NUM_TAG = "🌿⃝❄"  # يُلحق بعد رقم كل طالبة


async def is_admin(chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def build_list_text(chat_id: int) -> str:
    data = chat_data.get(chat_id)
    if not data:
        return HEADER + FOOTER
    lines = []
    for i, (uid, info) in enumerate(data["students"].items(), start=1):
        line = f"{i}{NUM_TAG} {info['name']}"
        status = info.get("status", "")
        if status == "read":
            line += "  ✅️قرأت🩵"
        elif status == "listening":
            line += "  مستمعة🩶"
        elif status == "excused":
            line += "  معتذرة❤️"
        elif status == "similar":
            line += "  ✅️☑️🩵"
        lines.append(line)
    body = "\n\n".join(lines)
    return HEADER + body + FOOTER


def build_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    data = chat_data.get(chat_id, {})
    active = data.get("active", True)
    rows = []
    if active:
        rows.append([InlineKeyboardButton("🔘 سجل إسمي", callback_data="register")])
    rows.append([
        InlineKeyboardButton("✅️ قرأت", callback_data="read"),
        InlineKeyboardButton("🎧 مستمعة", callback_data="listening"),
    ])
    rows.append([
        InlineKeyboardButton("🚫 معتذرة", callback_data="excused"),
        InlineKeyboardButton("☑️ متشابهات", callback_data="similar"),
    ])
    rows.append([InlineKeyboardButton("❌️ أحذف إسمي", callback_data="unregister")])
    return InlineKeyboardMarkup(rows)


async def startliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not await is_admin(chat_id, user.id, context):
        await update.message.reply_text("⚠️ هذا الأمر متاح فقط لأدمينات الصفحة.")
        return
    chat_data[chat_id] = {"active": True, "students": {}, "message_id": None}
    msg = await update.message.reply_text(
        build_list_text(chat_id), reply_markup=build_keyboard(chat_id)
    )
    chat_data[chat_id]["message_id"] = msg.message_id


async def deletliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not await is_admin(chat_id, user.id, context):
        await update.message.reply_text("⚠️ هذا الأمر متاح فقط لأدمينات الصفحة.")
        return
    chat_data.pop(chat_id, None)
    await update.message.reply_text("🗑️ تم حذف القائمة.")


async def stopliste(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not await is_admin(chat_id, user.id, context):
        await update.message.reply_text("⚠️ هذا الأمر متاح فقط لأدمينات الصفحة.")
        return
    data = chat_data.get(chat_id)
    if not data:
        await update.message.reply_text("لا توجد قائمة نشطة حالياً.")
        return
    data["active"] = False
    if data.get("message_id"):
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=data["message_id"],
                text=build_list_text(chat_id),
                reply_markup=build_keyboard(chat_id),
            )
        except Exception:
            pass
    await update.message.reply_text("🔒 تم إغلاق باب التسجيل في القائمة.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = query.message.chat_id
    user = query.from_user
    data = chat_data.get(chat_id)

    if not data:
        await query.answer("لا توجد قائمة نشطة حالياً.", show_alert=True)
        return

    action = query.data

    if action == "register":
        if not data.get("active", True):
            await query.answer("تم إغلاق التسجيل.", show_alert=True)
            return
        if user.id in data["students"]:
            await query.answer("إسمك مسجل مسبقاً.", show_alert=True)
            return
        data["students"][user.id] = {"name": user.full_name, "status": ""}
        await query.answer("تم تسجيل إسمك ✅️")

    elif action == "unregister":
        if user.id in data["students"]:
            del data["students"][user.id]
            await query.answer("تم حذف إسمك ❌️")
        else:
            await query.answer("إسمك غير مسجل في القائمة.", show_alert=True)
            return

    elif action in ("read", "listening", "excused", "similar"):
        if user.id not in data["students"]:
            await query.answer("سجلي إسمك أولاً.", show_alert=True)
            return
        data["students"][user.id]["status"] = action
        await query.answer("تم التحديث ✅️")

    else:
        await query.answer()
        return

    try:
        await query.edit_message_text(
            text=build_list_text(chat_id), reply_markup=build_keyboard(chat_id)
        )
    except Exception:
        pass


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("startliste", startliste))
    app.add_handler(CommandHandler("deletliste", deletliste))
    app.add_handler(CommandHandler("stopliste", stopliste))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()


if __name__ == "__main__":
    main()
