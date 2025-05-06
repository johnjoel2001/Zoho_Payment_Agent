import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from ai_agent import handle_message_and_get_response

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Make sure this is stripped and clean

# 🔁 Process every incoming message
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    if not user_message:
        return

    # Run your existing AI message processing and get responses
    responses = handle_message_and_get_response(user_message)

    # Reply in the group with each result
    for res in responses:
        await update.message.reply_text(res)

# 🏁 Start the bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_group_message))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
