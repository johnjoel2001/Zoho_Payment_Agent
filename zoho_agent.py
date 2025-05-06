import requests
import datetime
from itertools import combinations
from env import CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN, ORG_ID


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

    # Fuzzy customer name match
    def customer_name_match(user_input, customer_name):
        user_words = user_input.lower().split()
        customer_words = customer_name.lower().split()
        return any(word in customer_words for word in user_words)

    matched_invoices = [inv for inv in all_invoices if customer_name_match(name, inv["customer_name"]) and float(inv["balance"]) > 0]

    # Try combinations of matched invoices to match amount
    for r in range(1, len(matched_invoices) + 1):
        for combo in combinations(matched_invoices, r):
            total = sum(float(inv["balance"]) for inv in combo)
            if abs(total - float(amount)) <= 5:
                print(f"✅ Matched combination of {r} invoices totaling ₹{total:.2f}")
                return combo

    print("❌ No matching invoice combination found")
    return []


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
