#!/usr/bin/env python3
"""
Robust Import Tool (Idempotent)
Use this tool to import receipts safely. It checks for duplicates before creating.
"""
import os
import time
import requests
import pandas as pd
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN")
if not LOYVERSE_TOKEN:
    print("❌ Error: LOYVERSE_TOKEN not found in .env or environment variables.")
    exit(1)

print("✅ Loaded LOYVERSE_TOKEN from environment.")
BASE_URL = "https://api.loyverse.com/v1.0/receipts"

class LoyverseImporter:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def check_exists(self, created_at, total_money, receipt_number=None):
        """
        Check if receipt exists by (created_at + total_money) or receipt_number.
        Returns existing ID if found, None otherwise.
        """
        # Search window: +/- 1 second to be safe, or exact match
        params = {
            "created_at_min": created_at,
            "created_at_max": created_at,
            "limit": 20
        }
        
        try:
            res = requests.get(BASE_URL, headers=self.headers, params=params, timeout=10)
            if res.status_code == 200:
                candidates = res.json().get('receipts', [])
                for r in candidates:
                    # 1. Check receipt number if provided (Strongest check)
                    if receipt_number and r.get('receipt_number') == receipt_number:
                        return r.get('id') or "EXISTING_NO_ID"
                    
                    # 2. Check total money (Secondary check)
                    # Note: Float comparison needs epsilon, but API returns string or float
                    api_total = float(r.get('total_money', 0))
                    if abs(api_total - float(total_money)) < 0.01:
                        return r.get('id') or "EXISTING_NO_ID"
                        
            return None
        except Exception as e:
            print(f"⚠️ Check failed: {e}")
            # Fail safe: If we can't check, assume it might exist (or just fail)
            # Returning a special sentinel to indicate check failure would be better,
            # but for now let's just return None and handle it in caller or print warning.
            # actually, let's return a sentinel to prevent creation
            return "CHECK_FAILED"

    def import_receipt(self, receipt_data):
        """
        Import a single receipt idempotently.
        """
        created_at = receipt_data.get('created_at')
        total_money = receipt_data.get('total_money')
        receipt_number = receipt_data.get('receipt_number')
        
        if not created_at or total_money is None:
            print("❌ Invalid data: Missing created_at or total_money")
            return False

        # 1. Idempotency Check
        existing_id = self.check_exists(created_at, total_money, receipt_number)
        if existing_id == "CHECK_FAILED":
             print(f"⚠️ Skipped due to check failure: {created_at} - {total_money}")
             return False
        if existing_id:
            print(f"⏭️ Skipped duplicate: {created_at} - {total_money} (ID: {existing_id})")
            return True # Treated as success

        # 2. Create
        try:
            res = requests.post(BASE_URL, headers=self.headers, json=receipt_data, timeout=10)
            if res.status_code == 201:
                new_id = res.json().get('id')
                print(f"✅ Created: {created_at} - {total_money} (ID: {new_id})")
                return True
            else:
                print(f"❌ Failed to create: {res.status_code} - {res.text}")
                return False
        except Exception as e:
            print(f"❌ Network error: {e}")
            return False

def main():
    print("🚀 Robust Import Tool")
    print("=====================")
    
    # Example: Import from a CSV file
    import sys
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "receipts_to_import.csv"
    
    if not os.path.exists(input_file):
        print(f"ℹ️ No '{input_file}' found. Creating a sample template...")
        sample_data = [
            {
                "receipt_number": "TEST-001",
                "created_at": "2025-12-04T10:00:00.000Z",
                "total_money": 150.00,
                "payment_type": "CASH"
            }
        ]
        pd.DataFrame(sample_data).to_csv(input_file, index=False)
        print(f"✅ Created template '{input_file}'. Populate it and run again.")
        return

    print(f"📂 Reading {input_file}...")
    df = pd.read_csv(input_file)
    
    importer = LoyverseImporter(LOYVERSE_TOKEN)
    
    success_count = 0
    for _, row in df.iterrows():
        # Convert row to dict and format as needed by API
        receipt_data = {
            "created_at": row['created_at'],
            "total_money": row['total_money'],
            "receipt_number": row.get('receipt_number'),
            # Add other fields mapping here
        }
        
        if importer.import_receipt(receipt_data):
            success_count += 1
            
    print(f"\n✅ Import complete. Processed {len(df)} items.")

if __name__ == "__main__":
    main()
