from telegram import Update, BotCommand, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.error import Forbidden
import asyncio
import os

TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = -1002663001994
GROUP_URL = "https://t.me/PrivasichatRuang"

waiting_users = []
paired_users = {}

# ===== Cek apakah user sudah join grup =====
async def is_user_in_group(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=GROUP_CHAT_ID, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== Kirim tombol join group =====
async def send_join_group_message(update: Update):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Join the Group", url=GROUP_URL)],
        [InlineKeyboardButton("🔄 Try Again", callback_data="try_again")]
    ])
    await update.message.reply_text(
        "🚫 You must join our group first to use this bot:",
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

# ===== Start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_group(user_id, context):
        await send_join_group_message(update)
        return

    await update.message.reply_text("🔎 Looking for a partner...", reply_markup=ReplyKeyboardRemove())
    await search(update, context)

# ===== Search =====
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_group(user_id, context):
        await send_join_group_message(update)
        return

    if user_id in paired_users:
        await update.message.reply_text("⚠️ You're already in a dialog. Type /stop to end it.")
        return

    if user_id in waiting_users:
        return

    if waiting_users:
        partner_id = waiting_users.pop(0)
        paired_users[user_id] = partner_id
        paired_users[partner_id] = user_id

        connected_text = "✅ Partner found!\n/next - find a new partner\n/stop - stop this dialog"
        await context.bot.send_message(chat_id=user_id, text=connected_text)
        await context.bot.send_message(chat_id=partner_id, text=connected_text)
    else:
        waiting_users.append(user_id)

# ===== Leave / Stop =====
async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in paired_users:
        partner_id = paired_users.pop(user_id)
        paired_users.pop(partner_id, None)

        await context.bot.send_message(chat_id=partner_id, text="❌ Your partner has stopped the dialog.\nType /search to find a new partner.")
        await update.message.reply_text("❌ You stopped the dialog.\nType /search to find a new partner.")
    elif user_id in waiting_users:
        waiting_users.remove(user_id)
        await update.message.reply_text("❌ You stopped searching.")
    else:
        await update.message.reply_text("⚠️ You're not in a dialog.")

# ===== Next =====
async def next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_in_group(user_id, context):
        await send_join_group_message(update)
        return

    await leave(update, context)
    await update.message.reply_text("🔄 Looking for a partner...")
    await search(update, context)

# ===== Forward pesan ke pasangan =====
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_user_in_group(user_id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Rejoin Group", url=GROUP_URL)]
        ])
        await update.message.reply_text(
            "👋 You've left the group. Please rejoin to continue using AnonChat.",
            reply_markup=keyboard
        )
        return

    if user_id not in paired_users:
        username = update.effective_user.first_name
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🚀 Start Chatting", url=f"https://t.me/{context.bot.username}?start=start")]
        ])
        await update.message.reply_text(
            f"👋 Welcome {username} to AnonChat!\n\nYou're not connected to anyone yet.\nTap the button below to start chatting.",
            reply_markup=keyboard
        )
        return

    partner_id = paired_users[user_id]
    msg = update.message

    if msg.text:
        await context.bot.send_message(chat_id=partner_id, text=msg.text)
    elif msg.photo:
        await context.bot.send_photo(chat_id=partner_id, photo=msg.photo[-1].file_id, caption=msg.caption or "")
    elif msg.video:
        await context.bot.send_video(chat_id=partner_id, video=msg.video.file_id, caption=msg.caption or "")
    elif msg.voice:
        await context.bot.send_voice(chat_id=partner_id, voice=msg.voice.file_id)
    elif msg.audio:
        await context.bot.send_audio(chat_id=partner_id, audio=msg.audio.file_id)
    elif msg.document:
        await context.bot.send_document(chat_id=partner_id, document=msg.document.file_id, caption=msg.caption or "")
    else:
        await update.message.reply_text("❗This message type is not supported.")

# ===== Callback tombol "Try Again" =====
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "try_again":
        await context.bot.send_message(chat_id=query.from_user.id, text="🔄 Checking group status...")
        await search(update, context)

# ===== Sambutan ketika user masuk ke grup =====
async def group_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.id == context.bot.id:
                continue

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Start Anonymous Chat", url=f"https://t.me/{context.bot.username}?start=start")]
            ])

            await update.message.reply_text(
                f"👋 Welcome {member.mention_html()}!\n\nClick the button below to start anonymous chatting.",
                parse_mode='HTML',
                reply_markup=keyboard
            )

# ===== Menu bot =====
async def set_commands(app):
    commands = [
        BotCommand("search", "🔍 Find a partner"),
        BotCommand("next", "🔄 Find a new partner"),
        BotCommand("stop", "⛔ Stop current dialog"),
    ]
    await app.bot.set_my_commands(commands)

# ===== Setup bot =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("search", search))
app.add_handler(CommandHandler("next", next_command))
app.add_handler(CommandHandler("stop", leave))
app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), forward_message))
app.add_handler(CallbackQueryHandler(handle_callback))
app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, group_welcome))

# ===== Jalankan bot =====
if __name__ == '__main__':
    async def startup():
        await set_commands(app)
        print("🤖 Bot berjalan...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        await asyncio.Event().wait()

    asyncio.run(startup())