import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from ai_agent import handle_message_and_get_response
from zoho_agent import get_access_token, mark_invoices_as_paid

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Make sure this is stripped and clean

# Store pending invoice selections: {session_id: {"combos": [...], "amount": ..., "customer_name": ...}}
pending_selections = {}


# 🔁 Process every incoming message
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    if not user_message:
        return

    # Run your existing AI message processing and get responses
    responses = handle_message_and_get_response(user_message)

    # Reply in the group with each result
    for res in responses:
        if isinstance(res, dict) and res.get("type") == "selection":
            # Multiple invoice combos found — show inline keyboard for user to pick
            session_id = uuid.uuid4().hex[:8]
            pending_selections[session_id] = {
                "combos": res["combos"],
                "amount": res["amount"],
                "customer_name": res["customer_name"]
            }

            keyboard = []
            for i, combo in enumerate(res["combos"]):
                invoice_nums = ", ".join(inv["invoice_number"] for inv in combo)
                total = sum(float(inv["balance"]) for inv in combo)
                button_text = f"Option {i + 1}: {invoice_nums} (₹{total:.0f})"
                callback_data = f"pay:{session_id}:{i}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

            reply_markup = InlineKeyboardMarkup(keyboard)
            header = (
                f"🤔 Multiple invoice combinations match ₹{res['amount']} "
                f"for {res['customer_name']}.\n\n"
                f"Please select one option below:"
            )
            await update.message.reply_text(header, reply_markup=reply_markup)
        else:
            await update.message.reply_text(res)


# 🔁 Handle inline keyboard button press
async def handle_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # e.g. "pay:abc12345:2"
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "pay":
        await query.edit_message_text("⚠️ Invalid selection.")
        return

    session_id = parts[1]
    combo_index = int(parts[2])

    selection = pending_selections.pop(session_id, None)
    if not selection:
        await query.edit_message_text("⚠️ This selection has expired. Please resend the payment message.")
        return

    combos = selection["combos"]
    amount = selection["amount"]
    customer_name = selection["customer_name"]

    if combo_index < 0 or combo_index >= len(combos):
        await query.edit_message_text("⚠️ Invalid option selected.")
        return

    selected_invoices = combos[combo_index]
    token = get_access_token()
    success = mark_invoices_as_paid(selected_invoices, amount, token)

    if success:
        invoice_info = "\n".join(f"✔ {inv['invoice_number']} | ₹{inv['balance']}" for inv in selected_invoices)
        await query.edit_message_text(
            f"✅ Payment recorded for {customer_name} (₹{amount}):\n{invoice_info}"
        )
    else:
        await query.edit_message_text(f"❌ Failed to mark invoice(s) for {customer_name} as paid.")


# 🏁 Start the bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_selection_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_group_message))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
