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
        print(response)
    print("\n" + "="*60)

if __name__ == "__main__":
    # Test with the provided message
    test_payment("krishna welsing paid 10,000")
