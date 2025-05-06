from zoho_agent import get_access_token, find_invoice_combinations, mark_invoices_as_paid
from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def handle_message_and_get_response(message):
    responses = []
    token = get_access_token()

    if "cheque deposited details" in message.lower():
        print("🧾 Detected multiple cheque deposit entries")
        lines = message.strip().split("\n")
        for line in lines:
            if "cheque deposited details" in line.lower() or not line.strip():
                continue
            result = _process_line_returning_response(line, token)
            if result:
                responses.append(result)
    else:
        result = _process_line_returning_response(message, token)
        if result:
            responses.append(result)

    return responses

def _process_line_returning_response(message, token):
    prompt = f'''
    Extract the customer name and amount from the message below. Only respond with a JSON object like:
    {{"name": "...", "amount": 1234}}

    Message: "{message}"
    '''

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    raw_content = response.choices[0].message.content.strip()
    print("🧠 GPT Output:", raw_content)

    try:
        parsed = eval(raw_content)
        if isinstance(parsed, list):
            parsed = parsed[0]  # Try getting the first dict
        if not isinstance(parsed, dict) or "name" not in parsed or "amount" not in parsed:
            raise ValueError("Invalid format")

        name = parsed["name"].strip()
        amount = float(parsed["amount"])
    except Exception as e:
        print(f"❌ Failed to parse message: {e}")
        return f"⚠️ Couldn't understand message: {message}"

    print(f"\n➡️ Processing: {name} paid ₹{amount}")
    invoices_to_pay = find_invoice_combinations(name, amount, token)

    if invoices_to_pay:
        success = mark_invoices_as_paid(invoices_to_pay, amount, token)
        if success:
            invoice_info = "\n".join(f"✔ {inv['invoice_number']} | ₹{inv['balance']}" for inv in invoices_to_pay)
            return f"✅ Payment recorded for {name} (₹{amount}):\n{invoice_info}"
        else:
            return f"❌ Failed to mark invoice(s) for {name} as paid."
    else:
        return f"❌ No suitable invoice combination found for {name} ₹{amount}"
