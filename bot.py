import os
import json
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ==============================
# 🔹 Налаштування
# ==============================

TOKEN = os.environ.get("BOT_TOKEN")  # Токен беремо з змінних середовища Render
TECH_ADMINS = [123456789, 987654321]  # ID двох "технічних" адмінів, яких не можна видалити

ADMINS_FILE = "admins.json"

# Якщо файл з адмінами не існує — створюємо його
if not os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(TECH_ADMINS, f)

# Завантаження списку адмінів
def load_admins():
    with open(ADMINS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Збереження списку адмінів
def save_admins(admins):
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(admins, f)

# Перевірка чи користувач адмін
def is_admin(user_id):
    return user_id in load_admins()

# ==============================
# 🔹 Парсер часу (1h, 10m, 2d)
# ==============================
def parse_duration(duration_str):
    try:
        unit = duration_str[-1]
        value = int(duration_str[:-1])
        if unit == "m":
            return value * 60
        elif unit == "h":
            return value * 3600
        elif unit == "d":
            return value * 86400
    except:
        return None
    return None

# ==============================
# 🔹 Команди модерації
# ==============================

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У вас немає прав.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Відповідь на повідомлення користувача, якого хочете зам'ютити.")

    if not context.args:
        return await update.message.reply_text("⏳ Вкажіть тривалість (наприклад: 1h, 30m)")

    seconds = parse_duration(context.args[0])
    if not seconds:
        return await update.message.reply_text("⛔ Формат часу: 10m, 1h, 2d")

    until = datetime.utcnow() + timedelta(seconds=seconds)
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        update.message.reply_to_message.from_user.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until
    )
    await update.message.reply_text(f"🔇 Користувача зам'ютили на {context.args[0]}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У вас немає прав.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Відповідь на повідомлення користувача.")

    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        update.message.reply_to_message.from_user.id,
        permissions=ChatPermissions(can_send_messages=True)
    )
    await update.message.reply_text("🔊 Користувача розм'ютили.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У вас немає прав.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Відповідь на повідомлення користувача.")

    if not context.args:
        return await update.message.reply_text("⏳ Вкажіть тривалість (1h, 2d) або 0 для перманентного бану.")

    if context.args[0] == "0":
        until = None
    else:
        seconds = parse_duration(context.args[0])
        if not seconds:
            return await update.message.reply_text("⛔ Формат часу: 10m, 1h, 2d")
        until = datetime.utcnow() + timedelta(seconds=seconds)

    await context.bot.ban_chat_member(
        update.effective_chat.id,
        update.message.reply_to_message.from_user.id,
        until_date=until
    )
    await update.message.reply_text(f"🚫 Користувача забанено на {context.args[0]}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У вас немає прав.")

    if not context.args:
        return await update.message.reply_text("⚠️ Вкажіть ID користувача.")

    await context.bot.unban_chat_member(update.effective_chat.id, int(context.args[0]))
    await update.message.reply_text("✅ Користувача розбанено.")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У вас немає прав.")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Відповідь на повідомлення користувача.")

    user_id = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(update.effective_chat.id, user_id)
    await context.bot.unban_chat_member(update.effective_chat.id, user_id)
    await update.message.reply_text("👢 Користувача кікнули.")

# ==============================
# 🔹 Система адмінів
# ==============================

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = load_admins()
    text = "👮‍♂️ Список адмінів:\n" + "\n".join(str(a) for a in admins)
    await update.message.reply_text(text)

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in TECH_ADMINS:
        return await update.message.reply_text("⛔ Лише технічні адміни можуть додавати адмінів.")

    if not context.args:
        return await update.message.reply_text("⚠️ Вкажіть ID користувача.")

    admins = load_admins()
    new_id = int(context.args[0])
    if new_id not in admins:
        admins.append(new_id)
        save_admins(admins)
        await update.message.reply_text("✅ Адміна додано.")
    else:
        await update.message.reply_text("ℹ️ Користувач вже адмін.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in TECH_ADMINS:
        return await update.message.reply_text("⛔ Лише технічні адміни можуть видаляти адмінів.")

    if not context.args:
        return await update.message.reply_text("⚠️ Вкажіть ID користувача.")

    admins = load_admins()
    rem_id = int(context.args[0])
    if rem_id in TECH_ADMINS:
        return await update.message.reply_text("⛔ Неможливо видалити технічного адміна.")
    if rem_id in admins:
        admins.remove(rem_id)
        save_admins(admins)
        await update.message.reply_text("✅ Адміна видалено.")
    else:
        await update.message.reply_text("ℹ️ Користувач не адмін.")

# ==============================
# 🔹 Інші команди
# ==============================

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            text = f.read()
        await update.message.reply_text(text)
    except FileNotFoundError:
        await update.message.reply_text("📄 Файл з правилами не знайдено.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = load_admins()
    text = f"📢 Репорт від {update.effective_user.full_name} ({update.effective_user.id}):\n"
    text += " ".join(context.args) if context.args else "(без тексту)"
    for admin_id in admins:
        try:
            await context.bot.send_message(admin_id, text)
        except:
            pass
    await update.message.reply_text("✅ Репорт відправлено.")

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"👋 Вітаємо, {member.full_name}!\n📜 Ознайомтесь з правилами команди /rules"
        )

# ==============================
# 🔹 Запуск бота (Webhook)
# ==============================

def main():
    PORT = int(os.environ.get("PORT", "8443"))
    HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    WEBHOOK_URL = f"https://{HOSTNAME}/{TOKEN}"

    app = ApplicationBuilder().token(TOKEN).build()

    # Команди модерації
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("kick", kick))

    # Система адмінів
    app.add_handler(CommandHandler("admins", list_admins))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))

    # Інші команди
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

    print(f"🚀 Запуск webhook на порту {PORT} з URL: {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()
