#!/usr/bin/env python3
"""Test script to check payment processing without Telegram bot"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_agent import handle_message_and_get_response

def test_payment(message):
    print(f"\n{'='*60}")
    print(f"Testing message: {message}")
    print(f"{'='*60}\n")
    
    responses = handle_message_and_get_response(message)
    
    print("\n" + "="*60)
    print("RESPONSES:")
    print("="*60)
    for i, response in enumerate(responses, 1):
        print(f"\n[Response {i}]")
        if isinstance(response, dict) and response.get("type") == "selection":
            print(f"🤔 Selection required for {response['customer_name']} (₹{response['amount']})")
            print(f"   {len(response['combos'])} matching combinations found:")
            for j, combo in enumerate(response['combos'], 1):
                invoice_nums = ", ".join(inv["invoice_number"] for inv in combo)
                total = sum(float(inv["balance"]) for inv in combo)
                print(f"   Option {j}: {invoice_nums} (₹{total:.0f})")
        else:
            print(response)
    print("\n" + "="*60)

if __name__ == "__main__":
    # Test with the provided message
    test_payment("krishna welsing paid 10,000")
