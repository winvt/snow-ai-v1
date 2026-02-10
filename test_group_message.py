#!/usr/bin/env python3
"""
Test script to send a message to LINE group chat
"""

import os
import requests
from dotenv import load_dotenv

def send_test_message():
    load_dotenv()
    
    channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    group_id = os.getenv("LINE_RECIPIENT_ID")  # This should be your group ID
    
    if not channel_access_token:
        print("❌ Missing LINE_CHANNEL_ACCESS_TOKEN")
        return
    
    if not group_id:
        print("❌ Missing LINE_RECIPIENT_ID (group ID)")
        return
    
    headers = {
        "Authorization": f"Bearer {channel_access_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "to": group_id,
        "messages": [
            {
                "type": "text",
                "text": "🧪 Test message from Snowbomb bot!\n\nThis is a test to verify group messaging is working. ✅"
            }
        ]
    }
    
    try:
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Test message sent successfully to group!")
            print(f"Group ID: {group_id}")
        else:
            print(f"❌ Failed to send message: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_test_message()
