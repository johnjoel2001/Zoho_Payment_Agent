# from zoho_agent import get_access_token, find_invoice_combinations, mark_invoices_as_paid
# from openai import OpenAI
# import os

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def handle_message_and_get_response(message):
#     responses = []
#     token = get_access_token()

#     if "cheque deposited details" in message.lower():
#         print("🧾 Detected multiple cheque deposit entries")
#         lines = message.strip().split("\n")
#         for line in lines:
#             if "cheque deposited details" in line.lower() or not line.strip():
#                 continue
#             result = _process_line_returning_response(line, token)
#             if result:
#                 responses.append(result)
#     else:
#         result = _process_line_returning_response(message, token)
#         if result:
#             responses.append(result)

#     return responses

# def _process_line_returning_response(message, token):
#     prompt = f'''
#     Extract the customer name and amount from the message below. Only respond with a JSON object like:
#     {{"name": "...", "amount": 1234}}

#     Message: "{message}"
#     '''

#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[{"role": "user", "content": prompt}]
#     )

#     raw_content = response.choices[0].message.content.strip()
#     print("🧠 GPT Output:", raw_content)

#     try:
#         parsed = eval(raw_content)
#         if isinstance(parsed, list):
#             parsed = parsed[0]  # Try getting the first dict
#         if not isinstance(parsed, dict) or "name" not in parsed or "amount" not in parsed:
#             raise ValueError("Invalid format")

#         name = parsed["name"].strip()
#         amount = float(parsed["amount"])
#     except Exception as e:
#         print(f"❌ Failed to parse message: {e}")
#         return f"⚠️ Couldn't understand message: {message}"

#     print(f"\n➡️ Processing: {name} paid ₹{amount}")
#     invoices_to_pay = find_invoice_combinations(name, amount, token)

#     if invoices_to_pay:
#         success = mark_invoices_as_paid(invoices_to_pay, amount, token)
#         if success:
#             invoice_info = "\n".join(f"✔ {inv['invoice_number']} | ₹{inv['balance']}" for inv in invoices_to_pay)
#             # return f"✅ Payment recorded for {name} (₹{amount}):\n{invoice_info}"
#             # use invoice["customer_name"] from the matched invoice
#             return f"✅ Payment recorded for {invoices[0]['customer_name']} (₹{amount}):\n{invoice_info}"

#         else:
#             return f"❌ Failed to mark invoice(s) for {name} as paid."
#     else:
#         return f"❌ No suitable invoice combination found for {name} ₹{amount}"



from zoho_agent import get_access_token, find_invoice_combinations, mark_invoices_as_paid
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://oai.helicone.ai/v1",
    default_headers={
        "Helicone-Auth": f"Bearer {os.getenv('HELICONE_API_KEY')}",
    }
)

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
    result = find_invoice_combinations(name, amount, token)

    matched_combos = result["matched_combos"]
    available_invoices = result["available"]

    if matched_combos:
        # If exactly one combination matches, auto-apply it
        if len(matched_combos) == 1:
            invoices_to_pay = matched_combos[0]
            success = mark_invoices_as_paid(invoices_to_pay, amount, token)
            if success:
                invoice_info = "\n".join(f"✔ {inv['invoice_number']} | ₹{inv['balance']}" for inv in invoices_to_pay)
                return f"✅ Payment recorded for {invoices_to_pay[0]['customer_name']} (₹{amount}):\n{invoice_info}"
            else:
                return f"❌ Failed to mark invoice(s) for {name} as paid."
        else:
            # Multiple combinations found — let user pick invoices manually
            customer_name = matched_combos[0][0]['customer_name']
            seen = set()
            invoices = []
            for combo in matched_combos:
                for inv in combo:
                    inv_id = inv["invoice_id"]
                    if inv_id not in seen:
                        seen.add(inv_id)
                        invoices.append(inv)
            invoices.sort(key=lambda inv: inv.get("date", "9999-12-31"))
            return {
                "type": "selection",
                "customer_name": customer_name,
                "amount": amount,
                "invoices": invoices
            }
    else:
        # Show available invoices when no match is found
        if available_invoices:
            customer_name = available_invoices[0]['customer_name']
            invoice_list = "\n".join(f"• {inv['invoice_number']} | ₹{inv['balance']}" for inv in available_invoices)
            total_available = sum(float(inv['balance']) for inv in available_invoices)
            return f"❌ No suitable invoice combination found for {name} ₹{amount}\n\n📋 Available invoices for {customer_name}:\n{invoice_list}\n\n💰 Total Outstanding: ₹{total_available:.2f}"
        else:
            return f"❌ No invoices found for customer: {name}"

