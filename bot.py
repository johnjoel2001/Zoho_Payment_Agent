import os
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from ai_agent import handle_message_and_get_response
from zoho_agent import get_access_token, mark_invoices_as_paid

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Make sure this is stripped and clean

# Store pending invoice selections:
# {session_id: {"invoices": [...], "amount": ..., "customer_name": ..., "selected": set()}}
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
            # Multiple combos found — show multi-select invoice picker
            session_id = uuid.uuid4().hex[:8]
            pending_selections[session_id] = {
                "invoices": res["invoices"],
                "amount": res["amount"],
                "customer_name": res["customer_name"],
                "selected": set()
            }

            text, reply_markup = build_selection_message(session_id)
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(res)


def build_selection_message(session_id):
    """Build the message text and inline keyboard for the multi-select invoice picker."""
    sel = pending_selections.get(session_id)
    if not sel:
        return "⚠️ Session expired.", None

    invoices = sel["invoices"]
    selected = sel["selected"]
    amount = sel["amount"]
    customer_name = sel["customer_name"]

    selected_total = sum(float(invoices[i]["balance"]) for i in selected)
    diff = selected_total - float(amount)

    lines = [f"🤔 Multiple invoice combinations match ₹{amount} for {customer_name}.",
             "", "Tap invoices to select/deselect:"]
    for i, inv in enumerate(invoices):
        mark = "✅" if i in selected else "⬜"
        lines.append(f"{mark} {inv['invoice_number']} | ₹{inv['balance']}")

    lines.append("")
    if selected:
        if abs(diff) <= 5:
            lines.append(f"💰 Selected total: ₹{selected_total:.0f} ✅ (matches payment)")
        else:
            lines.append(f"💰 Selected total: ₹{selected_total:.0f} (target: ₹{amount:.0f}, diff: ₹{diff:+.0f})")
    else:
        lines.append(f"💰 Target amount: ₹{amount:.0f}")

    text = "\n".join(lines)

    keyboard = []
    for i, inv in enumerate(invoices):
        mark = "✅" if i in selected else "⬜"
        btn_text = f"{mark} {inv['invoice_number']} | ₹{inv['balance']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"toggle:{session_id}:{i}")])

    bottom_row = []
    bottom_row.append(InlineKeyboardButton("✅ Confirm", callback_data=f"confirm:{session_id}"))
    bottom_row.append(InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{session_id}"))
    keyboard.append(bottom_row)

    return text, InlineKeyboardMarkup(keyboard)


# 🔁 Handle inline keyboard button press
async def handle_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # e.g. "toggle:abc12345:2" or "confirm:abc12345" or "cancel:abc12345"
    parts = data.split(":")
    action = parts[0]
    session_id = parts[1]

    sel = pending_selections.get(session_id)
    if not sel:
        await query.edit_message_text("⚠️ This selection has expired. Please resend the payment message.")
        return

    if action == "toggle":
        inv_index = int(parts[2])
        if inv_index in sel["selected"]:
            sel["selected"].discard(inv_index)
        else:
            sel["selected"].add(inv_index)
        text, reply_markup = build_selection_message(session_id)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif action == "confirm":
        selected = sel["selected"]
        if not selected:
            await query.answer("Please select at least one invoice first.", show_alert=True)
            return

        invoices = sel["invoices"]
        amount = sel["amount"]
        customer_name = sel["customer_name"]
        selected_invoices = [invoices[i] for i in sorted(selected)]

        pending_selections.pop(session_id, None)

        token = get_access_token()
        success = mark_invoices_as_paid(selected_invoices, amount, token)

        if success:
            invoice_info = "\n".join(f"✔ {inv['invoice_number']} | ₹{inv['balance']}" for inv in selected_invoices)
            await query.edit_message_text(
                f"✅ Payment recorded for {customer_name} (₹{amount}):\n{invoice_info}"
            )
        else:
            await query.edit_message_text(f"❌ Failed to mark invoice(s) for {customer_name} as paid.")

    elif action == "cancel":
        pending_selections.pop(session_id, None)
        await query.edit_message_text("❌ Selection cancelled.")


# 🏁 Start the bot
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_selection_callback))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_group_message))
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
