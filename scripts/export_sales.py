#!/usr/bin/env python3
import os
import argparse
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()
LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN")
BASE_URL = "https://api.loyverse.com/v1.0/receipts"

if not LOYVERSE_TOKEN:
    print("❌ Error: LOYVERSE_TOKEN not found in .env")
    exit(1)

def fetch_receipts_for_day(date_obj):
    """Fetch receipts for a specific date (Bangkok time)."""
    tz = pytz.timezone('Asia/Bangkok')
    start_dt = tz.localize(datetime.combine(date_obj, datetime.min.time()))
    end_dt = tz.localize(datetime.combine(date_obj, datetime.max.time()))
    
    start_utc = start_dt.astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_utc = end_dt.astimezone(pytz.UTC).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    
    headers = {"Authorization": f"Bearer {LOYVERSE_TOKEN}"}
    day_receipts = []
    cursor = None
    
    for attempt in range(3):
        try:
            while True:
                params = {
                    "created_at_min": start_utc,
                    "created_at_max": end_utc,
                    "limit": 250,
                    "cursor": cursor
                }
                
                resp = requests.get(BASE_URL, headers=headers, params=params, timeout=10)
                if resp.status_code != 200:
                    print(f"   ⚠️ Error fetching {date_obj}: {resp.status_code}")
                    time.sleep(1)
                    break 
                    
                data = resp.json()
                receipts = data.get('receipts', [])
                day_receipts.extend(receipts)
                
                cursor = data.get('cursor')
                if not cursor:
                    return day_receipts
                
                time.sleep(0.1)
            
        except Exception as e:
            print(f"   ⚠️ Exception fetching {date_obj}: {e}")
            time.sleep(1)
    
    print(f"❌ Failed to fetch complete data for {date_obj}")
    return day_receipts

def fetch_receipts(start_date, end_date):
    """Fetch receipts for a date range."""
    print(f"📅 Fetching receipts from {start_date} to {end_date}...")
    
    all_receipts = []
    current_date = start_date
    while current_date <= end_date:
        print(f"   Fetching {current_date}...", end='\r')
        day_receipts = fetch_receipts_for_day(current_date)
        all_receipts.extend(day_receipts)
        current_date += timedelta(days=1)
        
    print(f"\n✅ Total receipts fetched: {len(all_receipts)}")
    return all_receipts

def main():
    parser = argparse.ArgumentParser(description="Export Sales Data from Loyverse")
    parser.add_argument("--start", type=str, required=True, help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End Date (YYYY-MM-DD)")
    parser.add_argument("--output", type=str, default="sales_export.csv", help="Output CSV filename")
    
    args = parser.parse_args()
    
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    except ValueError:
        print("❌ Invalid date format. Please use YYYY-MM-DD")
        return

    # 1. Fetch
    receipts = fetch_receipts(start_date, end_date)
    
    # 2. Deduplicate
    unique_receipts = []
    seen_keys = set()
    duplicates = []
    
    print("🔍 Deduplicating data...")
    for r in receipts:
        created_at = r.get('created_at')
        total_money = float(r.get('total_money', 0))
        key = (created_at, total_money)
        
        if key in seen_keys:
            duplicates.append(r)
        else:
            seen_keys.add(key)
            unique_receipts.append(r)
            
    # 3. Export
    if unique_receipts:
        df = pd.DataFrame(unique_receipts)
        
        # Order columns
        cols = ['created_at', 'receipt_number', 'total_money', 'receipt_type', 'store_id', 'id']
        existing_cols = [c for c in cols if c in df.columns]
        remaining_cols = [c for c in df.columns if c not in cols]
        df = df[existing_cols + remaining_cols]
        
        df.to_csv(args.output, index=False)
        
        print(f"\n✅ Export Complete: {args.output}")
        print(f"   - Total Fetched: {len(receipts)}")
        print(f"   - Duplicates Removed: {len(duplicates)}")
        print(f"   - Unique Receipts: {len(unique_receipts)}")
        
        total_sales = sum(float(r.get('total_money', 0)) for r in unique_receipts)
        print(f"   - Total Sales Value: {total_sales:,.2f}")
    else:
        print("⚠️ No receipts found to export.")

if __name__ == "__main__":
    main()
