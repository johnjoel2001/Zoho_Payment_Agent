import requests
import datetime
import os
import json
from itertools import combinations
from openai import OpenAI
from env import CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, ORG_ID

ai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.helicone.ai/v1",
    default_headers={
        "Helicone-Auth": os.getenv("HELICONE_API_KEY"),
    }
)


def get_access_token():
    url = "https://accounts.zoho.in/oauth/v2/token"
    data = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }
    res = requests.post(url, data=data)
    res.raise_for_status()
    token = res.json().get("access_token")
    print("✅ Access token retrieved:", token[:10], "...")
    return token


def ai_match_customer_name(user_input, customer_names):
    if not customer_names:
        return None
    prompt = f'''You are given a customer name from a user message and a list of actual customer names from our system.
Find the BEST matching customer name from the list. The user input may contain:
- Typos or misspellings (e.g. "mankattu" instead of "manakattu", "jayalakshni" instead of "jayalakshmi")
- Missing or extra letters
- Abbreviations or short forms
- Different casing

Be GENEROUS in matching — if the input is even roughly close to a name in the list, pick that name.
Only return the exact matching name from the list, nothing else. If absolutely no reasonable match exists, return "NO_MATCH".

User input: "{user_input}"

Customer names:
{json.dumps(customer_names)}'''

    response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    matched = response.choices[0].message.content.strip().strip('"')
    if matched == "NO_MATCH" or matched not in customer_names:
        return None
    return matched


def find_invoice_combinations(name, amount, token):
    url = "https://www.zohoapis.in/books/v3/invoices"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    start_date = "2025-02-01"

    print(f"\n🔍 Fetching invoices sent since {start_date}...")

    all_invoices = []
    page = 1
    while True:
        params = {
            "organization_id": ORG_ID,
            "per_page": 200,
            "page": page
        }
        res = requests.get(url, params=params, headers=headers)
        res.raise_for_status()
        invoices = res.json().get("invoices", [])
        if not invoices:
            break
        all_invoices.extend(invoices)
        if len(invoices) < 200:
            break
        page += 1

    # 🧾 Log all fetched invoices
    # print("\n📦 All Fetched Invoices:")
    # for inv in all_invoices:
    #     print(f"{inv['invoice_number']} | {inv['customer_name']} | ₹{inv['balance']} | Date: {inv.get('date')}")

    # Sort invoices by date and invoice number
    def extract_invoice_number(inv):
        try:
            return int(inv['invoice_number'].split('-')[1].split('/')[0])
        except:
            return 9999

    all_invoices.sort(key=lambda inv: (inv.get("date", "9999-12-31"), extract_invoice_number(inv)))

    # Use AI to match customer name against actual Zoho customer names
    unique_customers = list(set(inv["customer_name"] for inv in all_invoices if float(inv["balance"]) > 0))
    matched_customer = ai_match_customer_name(name, unique_customers)
    print(f"🤖 AI matched '{name}' → '{matched_customer}'")

    if not matched_customer:
        return {"matched_combos": [], "available": []}

    matched_invoices = [inv for inv in all_invoices if inv["customer_name"] == matched_customer and float(inv["balance"]) > 0]

    if not matched_invoices:
        return {"matched_combos": [], "available": []}

    # Find ALL combinations of matched invoices that sum to target amount
    matched_combos = []
    for r in range(1, len(matched_invoices) + 1):
        for combo in combinations(matched_invoices, r):
            total = sum(float(inv["balance"]) for inv in combo)
            if abs(total - float(amount)) <= 5:
                print(f"✅ Matched combination of {r} invoices totaling ₹{total:.2f}")
                matched_combos.append(list(combo))

    if matched_combos:
        return {
            "matched_combos": matched_combos,
            "available": matched_invoices,
        }

    # Return available invoices when no match is found
    return {"matched_combos": [], "available": matched_invoices}


def mark_invoices_as_paid(invoices, total_amount, token, mode="Bank Transfer"):
    url = "https://www.zohoapis.in/books/v3/customerpayments"
    headers = {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json"
    }

    customer_id = invoices[0]["customer_id"]
    today = str(datetime.date.today())
    applied_list = []
    remaining = total_amount

    for inv in invoices:
        balance = float(inv["balance"])
        apply = min(balance, remaining)
        applied_list.append({
            "invoice_id": inv["invoice_id"],
            "amount_applied": apply
        })
        remaining -= apply
        if remaining <= 0:
            break

    data = {
        "customer_id": customer_id,
        "payment_mode": mode,
        "amount": total_amount,
        "date": today,
        "invoices": applied_list
    }

    params = {"organization_id": ORG_ID}
    res = requests.post(url, headers=headers, json=data, params=params)
    print(f"💰 Marking {len(applied_list)} invoice(s) as paid...")
    print(f"🔁 Status Code: {res.status_code}")
    print(f"📄 Response Text: {res.text}")
    return res.status_code == 201
