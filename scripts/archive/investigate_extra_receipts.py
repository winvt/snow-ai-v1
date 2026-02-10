#!/usr/bin/env python3
"""
Investigate where extra receipts are coming from - compare API vs CSV date boundaries
"""
import os
import time
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
from dotenv import load_dotenv

load_dotenv()

LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN", "d18826e6c76345888204b310aaca1351")
BASE_URL = "https://api.loyverse.com/v1.0/receipts"

def fetch_receipts_detailed(token: str, start_date: date, end_date: date):
    """Fetch receipts with detailed date analysis."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # Convert Bangkok local date range to UTC timestamps
    tz_bkk = pytz.timezone("Asia/Bangkok")
    start_dt_utc = tz_bkk.localize(datetime.combine(start_date, datetime.min.time())).astimezone(pytz.UTC)
    end_dt_utc = tz_bkk.localize(datetime.combine(end_date, datetime.max.time())).astimezone(pytz.UTC)
    
    params = {
        "created_at_min": start_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "created_at_max": end_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": 100,
    }
    
    print(f"📅 Date Range Analysis:")
    print(f"  Bangkok Time: {start_date} to {end_date}")
    print(f"  UTC Time: {start_dt_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_dt_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API Params: created_at_min={params['created_at_min']}, created_at_max={params['created_at_max']}")
    print()
    
    all_receipts = []
    cursor = None
    
    while True:
        if cursor:
            params["cursor"] = cursor
        
        res = requests.get(BASE_URL, headers=headers, params=params, timeout=60)
        if res.status_code != 200:
            print(f"❌ Error {res.status_code}: {res.text}")
            break
        
        data = res.json()
        receipts = data.get("receipts", [])
        all_receipts.extend(receipts)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(0.1) # Be nice to the API
    
    return all_receipts, start_dt_utc, end_dt_utc

def analyze_receipt_dates(receipts, expected_start: date, expected_end: date):
    """Analyze receipt dates to find timezone boundary issues."""
    tz_bkk = pytz.timezone("Asia/Bangkok")
    tz_utc = pytz.UTC
    
    date_breakdown = {}
    boundary_issues = []
    outside_range = []
    
    for receipt in receipts:
        created_at = receipt.get("created_at")
        receipt_id = receipt.get("id") or receipt.get("receipt_number")
        
        if not created_at:
            continue
        
        try:
            # Parse UTC timestamp from API
            receipt_dt_utc = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            receipt_dt_bkk = receipt_dt_utc.astimezone(tz_bkk)
            receipt_date = receipt_dt_bkk.date()
            
            # Count by date
            if receipt_date not in date_breakdown:
                date_breakdown[receipt_date] = {
                    'count': 0,
                    'total': 0.0,
                    'receipts': []
                }
            
            receipt_total = float(receipt.get("total_money", 0) or 0)
            receipt_discount = float(receipt.get("total_discount", 0) or 0)
            net = receipt_total - receipt_discount
            
            date_breakdown[receipt_date]['count'] += 1
            date_breakdown[receipt_date]['total'] += net
            date_breakdown[receipt_date]['receipts'].append({
                'id': receipt_id,
                'created_at_utc': created_at,
                'created_at_bkk': receipt_dt_bkk.strftime('%Y-%m-%d %H:%M:%S'),
                'date': receipt_date,
                'total': net
            })
            
            # Check if outside expected range
            if receipt_date < expected_start or receipt_date > expected_end:
                outside_range.append({
                    'id': receipt_id,
                    'date': receipt_date,
                    'expected_range': f"{expected_start} to {expected_end}",
                    'created_at_utc': created_at,
                    'created_at_bkk': receipt_dt_bkk.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # Check for boundary issues (receipts near midnight)
            hour = receipt_dt_bkk.hour
            if hour == 0 or hour == 23:
                boundary_issues.append({
                    'id': receipt_id,
                    'date': receipt_date,
                    'hour_bkk': hour,
                    'created_at_utc': created_at,
                    'created_at_bkk': receipt_dt_bkk.strftime('%Y-%m-%d %H:%M:%S')
                })
                
        except Exception as e:
            print(f"⚠️ Error parsing receipt {receipt_id}: {e}")
    
    return date_breakdown, boundary_issues, outside_range

def main():
    print("=" * 80)
    print("INVESTIGATION: Where are the extra receipts coming from?")
    print("=" * 80)
    print()
    
    # CSV shows Dec 1-3, let's check what API returns
    start_date = date(2025, 11, 1)
    end_date = date(2025, 12, 3)
    
    print(f"🔍 Fetching receipts for {start_date} to {end_date}...")
    receipts, start_dt_utc, end_dt_utc = fetch_receipts_detailed(LOYVERSE_TOKEN, start_date, end_date)
    
    print(f"✅ Fetched {len(receipts)} receipts from API")
    print()
    
    # Analyze dates
    date_breakdown, boundary_issues, outside_range = analyze_receipt_dates(receipts, start_date, end_date)
    
    print("📊 Receipts by Date (Bangkok Time):")
    print("-" * 80)
    total_in_range = 0
    total_outside = 0
    
    for d in sorted(date_breakdown.keys()):
        info = date_breakdown[d]
        in_range = start_date <= d <= end_date
        status = "✅" if in_range else "⚠️ OUTSIDE RANGE"
        
        print(f"{status} {d}: {info['count']} receipts, Total: {info['total']:,.2f}")
        
        if in_range:
            total_in_range += info['count']
        else:
            total_outside += info['count']
    
    print()
    print(f"📈 Summary:")
    print(f"  Receipts in range ({start_date} to {end_date}): {total_in_range}")
    print(f"  Receipts outside range: {total_outside}")
    print(f"  Total receipts fetched: {len(receipts)}")
    print()
    
    if outside_range:
        print(f"⚠️ Found {len(outside_range)} receipts outside expected date range:")
        for issue in outside_range[:10]:  # Show first 10
            print(f"  Receipt {issue['id']}: Date {issue['date']} (expected {issue['expected_range']})")
            print(f"    UTC: {issue['created_at_utc']}, BKK: {issue['created_at_bkk']}")
        if len(outside_range) > 10:
            print(f"  ... and {len(outside_range) - 10} more")
        print()
    
    if boundary_issues:
        print(f"🕐 Found {len(boundary_issues)} receipts near timezone boundaries (midnight):")
        midnight_receipts = [b for b in boundary_issues if b['hour_bkk'] == 0]
        late_night = [b for b in boundary_issues if b['hour_bkk'] == 23]
        print(f"  At midnight (00:xx): {len(midnight_receipts)}")
        print(f"  Late night (23:xx): {len(late_night)}")
        print()
    
    # Compare with CSV
    print("📄 CSV Comparison:")
    print("-" * 80)
    csv_path = "sales-summary-2025-11-01-2025-12-03.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df['parsed_date'] = pd.to_datetime(df['วันที่'], format='%d/%m/%y')
        csv_dec = df # Compare all dates
        
        print("CSV Daily Totals:")
        for _, row in csv_dec.iterrows():
            csv_date = row['parsed_date'].date()
            csv_total = row['ยอดขายสุทธิ']
            api_total = date_breakdown.get(csv_date, {}).get('total', 0)
            diff = api_total - csv_total
            print(f"  {csv_date}: CSV={csv_total:,.2f}, API={api_total:,.2f}, Diff={diff:,.2f}")
        
        csv_total = csv_dec['ยอดขายสุทธิ'].sum()
        api_total = sum(info['total'] for d, info in date_breakdown.items() if start_date <= d <= end_date)
        print(f"\n  Total: CSV={csv_total:,.2f}, API={api_total:,.2f}, Diff={api_total - csv_total:,.2f}")
    
    # Check if there are receipts from other dates
    print()
    print("🔍 Checking for receipts from other dates in API response:")
    print("-" * 80)
    all_dates = sorted(date_breakdown.keys())
    print(f"API returned receipts from {len(all_dates)} different dates:")
    for d in all_dates:
        count = date_breakdown[d]['count']
        print(f"  {d}: {count} receipts")

if __name__ == "__main__":
    main()



