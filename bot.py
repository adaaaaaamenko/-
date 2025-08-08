import os
import json
import logging
from datetime import datetime, timedelta

from telegram import (
    Update,
    ChatPermissions,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TOKEN, TECH_ADMINS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMINS_FILE = 'admins.json'

def load_admins():
    try:
        with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_admins(admins):
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f, indent=2)

def is_admin(user_id: int):
    return user_id in TECH_ADMINS or user_id in load_admins()

def is_tech_admin(user_id: int):
    return user_id in TECH_ADMINS

def parse_duration(duration_str: str) -> int:
    unit = duration_str[-1]
    try:
        value = int(duration_str[:-1])
    except ValueError:
        return None

    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я — бот-модератор цього чату.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    help_text = (
        "🛠 *Адмін-команди:*\n"
        "/mute <час> — замʼютити користувача (наприклад: /mute 10m)\n"
        "/unmute — зняти мʼют\n"
        "/ban <час> — забанити (наприклад: /ban 1h)\n"
        "/unban <id> — розбанити за ID\n"
        "/kick — вигнати користувача\n"
        "/clean <N> — видалити останні N повідомлень\n"
        "/lock — закрити чат (лише читання)\n"
        "/unlock — відкрити чат\n"
        "/rules — показати правила\n"
        "/report @юзер причина — повідомити адмінам\n"
        "/admins — список адмінів\n"
        "/addadmin <id> — додати адміна\n"
        "/removeadmin <id> — видалити адміна\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_tech_admin(update.effective_user.id):
        return
    dynamic_admins = load_admins()
    tech_list = "\n".join([f"👑 {admin}" for admin in TECH_ADMINS])
    dynamic_list = "\n".join([f"🔧 {admin}" for admin in dynamic_admins])
    await update.message.reply_text(f"Список адмінів:\n{tech_list}\n{dynamic_list}")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_tech_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Використання: /addadmin <user_id>")
    try:
        user_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Невірний формат ID")
    admins = load_admins()
    if user_id not in admins:
        admins.append(user_id)
        save_admins(admins)
        await update.message.reply_text(f"✅ Адміна додано: {user_id}")
    else:
        await update.message.reply_text("Користувач вже є адміном.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_tech_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Використання: /removeadmin <user_id>")
    try:
        user_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Невірний формат ID")
    admins = load_admins()
    if user_id in admins:
        admins.remove(user_id)
        save_admins(admins)
        await update.message.reply_text(f"❌ Адміна видалено: {user_id}")
    else:
        await update.message.reply_text("Користувач не є адміном.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("🔇 Відповідай на повідомлення користувача, якого треба замʼютити.")
    if not context.args:
        return await update.message.reply_text("❗ Вкажи тривалість мʼюту (наприклад: /mute 10m)")
    seconds = parse_duration(context.args[0])
    if not seconds:
        return await update.message.reply_text("⛔ Формат: 10m, 1h, 2d")
    until = datetime.utcnow() + timedelta(seconds=seconds)
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until
    )
    await update.message.reply_text(f"🔇 Користувача замʼючено на {context.args[0]}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("🔊 Відповідай на повідомлення користувача, якого треба розмʼютити.")
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
    )
    await update.message.reply_text("🔊 Користувача розмʼючено.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У тебе немає прав для виконання цієї команди")
    if not update.message.reply_to_message:
        return await update.message.reply_text("📌 Використовуй команду у відповідь на повідомлення користувача")
    user_id = update.message.reply_to_message.from_user.id
    if not context.args:
        return await update.message.reply_text("⏳ Вкажи тривалість бана (наприклад: /ban 1d)")
    seconds = parse_duration(context.args[0])
    if not seconds:
        return await update.message.reply_text("⛔ Формат: 10m, 1h, 2d")
    until = datetime.utcnow() + timedelta(seconds=seconds)
    await context.bot.ban_chat_member(
        update.effective_chat.id,
        user_id,
        until_date=until
    )
    await update.message.reply_text(f"🚫 Користувача забанено на {context.args[0]}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У тебе немає прав на це.")
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("⛔ Невірний ID користувача.")
    else:
        return await update.message.reply_text("📌 Використання: /unban [ID] або відповісти на повідомлення.")
    try:
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_id,
            only_if_banned=True
        )
        await update.message.reply_text("✅ Користувача розбанено.")
    except Exception as e:
        await update.message.reply_text(f"⚠ Помилка: {e}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("👢 Відповідай на повідомлення користувача, якого треба вигнати.")
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(update.effective_chat.id, user_id)
    await context.bot.unban_chat_member(update.effective_chat.id, user_id)
    await update.message.reply_text("👢 Користувача вигнано з чату.")

async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await context.bot.set_chat_permissions(
        update.effective_chat.id,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text("🔒 Чат закрито. Тепер тільки читання.")

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await context.bot.set_chat_permissions(
        update.effective_chat.id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
    )
    await update.message.reply_text("🔓 Чат відкрито. Всі можуть писати.")

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("🧹 Вкажи кількість повідомлень для видалення: /clean 10")
    try:
        count = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❗ Це має бути число.")
    messages = []
    async for msg in update.effective_chat.get_history(limit=count + 1):
        messages.append(msg.message_id)
    for msg_id in messages:
        try:
            await context.bot.delete_message(update.effective_chat.id, msg_id)
        except:
            continue
    await update.message.reply_text(f"🧼 Видалено {count} повідомлень.")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            text = f.read()
        await update.message.reply_text(text)
    except FileNotFoundError:
        await update.message.reply_text("📄 Файл з правилами не знайдено.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Використання: /report @username причина")
    reason = ' '.join(context.args)
    reporter = update.effective_user.mention_html()
    admin_ids = TECH_ADMINS + load_admins()
    mentions = [f"<a href='tg://user?id={admin_id}'>адмін</a>" for admin_id in admin_ids]
    mention_text = ", ".join(mentions)
    await update.message.reply_html(
        f"🚨 Репорт від {reporter}:\nПричина: {reason}\n🔔 {mention_text}"
    )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
import os
import json
import logging
from datetime import datetime, timedelta

from telegram import (
    Update,
    ChatPermissions,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TOKEN, TECH_ADMINS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMINS_FILE = 'admins.json'

def load_admins():
    try:
        with open(ADMINS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_admins(admins):
    with open(ADMINS_FILE, 'w', encoding='utf-8') as f:
        json.dump(admins, f, indent=2)

def is_admin(user_id: int):
    return user_id in TECH_ADMINS or user_id in load_admins()

def is_tech_admin(user_id: int):
    return user_id in TECH_ADMINS

def parse_duration(duration_str: str) -> int:
    unit = duration_str[-1]
    try:
        value = int(duration_str[:-1])
    except ValueError:
        return None

    if unit == 'm':
        return value * 60
    elif unit == 'h':
        return value * 3600
    elif unit == 'd':
        return value * 86400
    else:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привіт! Я — бот-модератор цього чату.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    help_text = (
        "🛠 *Адмін-команди:*\n"
        "/mute <час> — замʼютити користувача (наприклад: /mute 10m)\n"
        "/unmute — зняти мʼют\n"
        "/ban <час> — забанити (наприклад: /ban 1h)\n"
        "/unban <id> — розбанити за ID\n"
        "/kick — вигнати користувача\n"
        "/clean <N> — видалити останні N повідомлень\n"
        "/lock — закрити чат (лише читання)\n"
        "/unlock — відкрити чат\n"
        "/rules — показати правила\n"
        "/report @юзер причина — повідомити адмінам\n"
        "/admins — список адмінів\n"
        "/addadmin <id> — додати адміна\n"
        "/removeadmin <id> — видалити адміна\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_tech_admin(update.effective_user.id):
        return
    dynamic_admins = load_admins()
    tech_list = "\n".join([f"👑 {admin}" for admin in TECH_ADMINS])
    dynamic_list = "\n".join([f"🔧 {admin}" for admin in dynamic_admins])
    await update.message.reply_text(f"Список адмінів:\n{tech_list}\n{dynamic_list}")

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_tech_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Використання: /addadmin <user_id>")
    try:
        user_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Невірний формат ID")
    admins = load_admins()
    if user_id not in admins:
        admins.append(user_id)
        save_admins(admins)
        await update.message.reply_text(f"✅ Адміна додано: {user_id}")
    else:
        await update.message.reply_text("Користувач вже є адміном.")

async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_tech_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Використання: /removeadmin <user_id>")
    try:
        user_id = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("Невірний формат ID")
    admins = load_admins()
    if user_id in admins:
        admins.remove(user_id)
        save_admins(admins)
        await update.message.reply_text(f"❌ Адміна видалено: {user_id}")
    else:
        await update.message.reply_text("Користувач не є адміном.")

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("🔇 Відповідай на повідомлення користувача, якого треба замʼютити.")
    if not context.args:
        return await update.message.reply_text("❗ Вкажи тривалість мʼюту (наприклад: /mute 10m)")
    seconds = parse_duration(context.args[0])
    if not seconds:
        return await update.message.reply_text("⛔ Формат: 10m, 1h, 2d")
    until = datetime.utcnow() + timedelta(seconds=seconds)
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until
    )
    await update.message.reply_text(f"🔇 Користувача замʼючено на {context.args[0]}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("🔊 Відповідай на повідомлення користувача, якого треба розмʼютити.")
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(
        update.effective_chat.id,
        user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
    )
    await update.message.reply_text("🔊 Користувача розмʼючено.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У тебе немає прав для виконання цієї команди")
    if not update.message.reply_to_message:
        return await update.message.reply_text("📌 Використовуй команду у відповідь на повідомлення користувача")
    user_id = update.message.reply_to_message.from_user.id
    if not context.args:
        return await update.message.reply_text("⏳ Вкажи тривалість бана (наприклад: /ban 1d)")
    seconds = parse_duration(context.args[0])
    if not seconds:
        return await update.message.reply_text("⛔ Формат: 10m, 1h, 2d")
    until = datetime.utcnow() + timedelta(seconds=seconds)
    await context.bot.ban_chat_member(
        update.effective_chat.id,
        user_id,
        until_date=until
    )
    await update.message.reply_text(f"🚫 Користувача забанено на {context.args[0]}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return await update.message.reply_text("⛔ У тебе немає прав на це.")
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            user_id = int(context.args[0])
        except ValueError:
            return await update.message.reply_text("⛔ Невірний ID користувача.")
    else:
        return await update.message.reply_text("📌 Використання: /unban [ID] або відповісти на повідомлення.")
    try:
        await context.bot.unban_chat_member(
            chat_id=update.effective_chat.id,
            user_id=user_id,
            only_if_banned=True
        )
        await update.message.reply_text("✅ Користувача розбанено.")
    except Exception as e:
        await update.message.reply_text(f"⚠ Помилка: {e}")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not update.message.reply_to_message:
        return await update.message.reply_text("👢 Відповідай на повідомлення користувача, якого треба вигнати.")
    user_id = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(update.effective_chat.id, user_id)
    await context.bot.unban_chat_member(update.effective_chat.id, user_id)
    await update.message.reply_text("👢 Користувача вигнано з чату.")

async def lock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await context.bot.set_chat_permissions(
        update.effective_chat.id,
        permissions=ChatPermissions(can_send_messages=False)
    )
    await update.message.reply_text("🔒 Чат закрито. Тепер тільки читання.")

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    await context.bot.set_chat_permissions(
        update.effective_chat.id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
        )
    )
    await update.message.reply_text("🔓 Чат відкрито. Всі можуть писати.")

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("🧹 Вкажи кількість повідомлень для видалення: /clean 10")
    try:
        count = int(context.args[0])
    except ValueError:
        return await update.message.reply_text("❗ Це має бути число.")
    messages = []
    async for msg in update.effective_chat.get_history(limit=count + 1):
        messages.append(msg.message_id)
    for msg_id in messages:
        try:
            await context.bot.delete_message(update.effective_chat.id, msg_id)
        except:
            continue
    await update.message.reply_text(f"🧼 Видалено {count} повідомлень.")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("rules.txt", "r", encoding="utf-8") as f:
            text = f.read()
        await update.message.reply_text(text)
    except FileNotFoundError:
        await update.message.reply_text("📄 Файл з правилами не знайдено.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("Використання: /report @username причина")
    reason = ' '.join(context.args)
    reporter = update.effective_user.mention_html()
    admin_ids = TECH_ADMINS + load_admins()
    mentions = [f"<a href='tg://user?id={admin_id}'>адмін</a>" for admin_id in admin_ids]
    mention_text = ", ".join(mentions)
    await update.message.reply_html(
        f"🚨 Репорт від {reporter}:\nПричина: {reason}\n🔔 {mention_text}"
    )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(
            f"👋 Вітаємо, {member.full_name}!\n📜 Ось правила чату:"
        )
        try:
            with open("rules.txt", "r", encoding="utf-8") as f:
                text = f.read()
            await update.message.reply_text(text)
        except FileNotFoundError:
            await update.message.reply_text("📄 Файл з правилами не знайдено.")

def main():
    PORT = int(os.environ.get("PORT", "8443"))

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admins", list_admins))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("clean", clean))
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("unlock", unlock))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

    WEBHOOK_URL = f"https://your-app-name.onrender.com/{TOKEN}"

    print(f"🚀 Запуск webhook на порту {PORT} з URL: {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == '__main__':
    main()        await update.message.reply_text(
            f"👋 Вітаємо, {member.full_name}!\n📜 Ось правила чату:"
        )
        try:
            with open("rules.txt", "r", encoding="utf-8") as f:
                text = f.read()
            await update.message.reply_text(text)
        except FileNotFoundError:
            await update.message.reply_text("📄 Файл з правилами не знайдено.")

def main():
    PORT = int(os.environ.get("PORT", "8443"))

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admins", list_admins))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("removeadmin", remove_admin))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("kick", kick))
    app.add_handler(CommandHandler("clean", clean))
    app.add_handler(CommandHandler("lock", lock))
    app.add_handler(CommandHandler("unlock", unlock))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))

    WEBHOOK_URL = f"https://your-app-name.onrender.com/{TOKEN}"

    print(f"🚀 Запуск webhook на порту {PORT} з URL: {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == '__main__':
    main() 
