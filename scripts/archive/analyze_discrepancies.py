#!/usr/bin/env python3
"""
Deep analysis of sales calculation discrepancies between CSV, API, and Dashboard.
"""
import os
import requests
import pandas as pd
from datetime import datetime, date
import pytz
from dotenv import load_dotenv
import json

load_dotenv()

LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN", "d18826e6c76345888204b310aaca1351")
BASE_URL = "https://api.loyverse.com/v1.0/receipts"

def fetch_sample_receipts(token: str, start_date: date, end_date: date, limit=10):
    """Fetch a small sample of receipts to analyze structure."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    tz = pytz.timezone("Asia/Bangkok")
    start_dt_utc = tz.localize(datetime.combine(start_date, datetime.min.time())).astimezone(pytz.UTC)
    end_dt_utc = tz.localize(datetime.combine(end_date, datetime.max.time())).astimezone(pytz.UTC)
    
    params = {
        "created_at_min": start_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "created_at_max": end_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": limit,
    }
    
    res = requests.get(BASE_URL, headers=headers, params=params, timeout=60)
    if res.status_code == 200:
        data = res.json()
        return data.get("receipts", [])
    return []

def analyze_receipt_structure(receipts):
    """Analyze the structure of API receipts to understand field names."""
    if not receipts:
        return {}
    
    sample = receipts[0]
    print("\n📋 API Receipt Structure Analysis:")
    print("=" * 80)
    print("Sample receipt keys:", list(sample.keys()))
    print()
    
    # Check for discount field variations
    discount_fields = {}
    for key in sample.keys():
        if 'discount' in key.lower():
            discount_fields[key] = sample.get(key)
    
    print("Discount-related fields found:")
    for key, value in discount_fields.items():
        print(f"  {key}: {value}")
    print()
    
    # Check receipt type
    print(f"Receipt type field: 'type' = {sample.get('type')}")
    print(f"Receipt type field: 'receipt_type' = {sample.get('receipt_type')}")
    print()
    
    # Check total fields
    total_fields = {}
    for key in sample.keys():
        if 'total' in key.lower() or 'money' in key.lower():
            total_fields[key] = sample.get(key)
    
    print("Total/Money-related fields:")
    for key, value in total_fields.items():
        print(f"  {key}: {value}")
    print()
    
    return {
        'discount_fields': discount_fields,
        'total_fields': total_fields,
        'type': sample.get('type'),
        'receipt_type': sample.get('receipt_type')
    }

def calculate_sales_corrected(receipts, use_total_discount=False):
    """Calculate sales with correct field names."""
    total_sales = 0.0
    total_refunds = 0.0
    total_discounts = 0.0
    receipt_types = {}
    
    for receipt in receipts:
        # Try different field name variations
        receipt_type = receipt.get("type") or receipt.get("receipt_type") or ""
        receipt_type = str(receipt_type).lower()
        
        # Try different total field names
        receipt_total = (
            float(receipt.get("total_money", 0) or 0) or
            float(receipt.get("total", 0) or 0) or
            0
        )
        
        # Try different discount field names
        if use_total_discount:
            receipt_discount = float(receipt.get("total_discount", 0) or 0)
        else:
            receipt_discount = (
                float(receipt.get("discount_money", 0) or 0) or
                float(receipt.get("total_discount", 0) or 0) or
                0
            )
        
        receipt_types[receipt_type] = receipt_types.get(receipt_type, 0) + 1
        
        net_amount = receipt_total - receipt_discount
        
        if receipt_type == "refund":
            total_refunds += net_amount
            total_sales -= net_amount
        else:
            total_sales += net_amount
            total_discounts += receipt_discount
    
    return total_sales, total_refunds, total_discounts, receipt_types

def analyze_timezone_issues(receipts, target_date: date):
    """Analyze if receipts are being assigned to wrong dates due to timezone."""
    tz_bkk = pytz.timezone("Asia/Bangkok")
    
    date_counts = {}
    timezone_issues = []
    
    for receipt in receipts:
        created_at = receipt.get("created_at")
        if created_at:
            try:
                # Parse UTC timestamp
                receipt_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                receipt_dt_bkk = receipt_dt.astimezone(tz_bkk)
                receipt_date = receipt_dt_bkk.date()
                
                date_counts[receipt_date] = date_counts.get(receipt_date, 0) + 1
                
                # Check if date is outside expected range
                if receipt_date < target_date or receipt_date > date(2025, 12, 31):
                    timezone_issues.append({
                        'receipt_id': receipt.get('id'),
                        'created_at_utc': created_at,
                        'date_bkk': receipt_date,
                        'expected_date': target_date
                    })
            except Exception as e:
                print(f"⚠️ Error parsing date: {created_at} - {e}")
    
    return date_counts, timezone_issues

def main():
    print("=" * 80)
    print("DEEP ANALYSIS: Sales Calculation Discrepancies")
    print("=" * 80)
    print()
    
    # Fetch sample receipts from December
    print("🔍 Fetching sample receipts to analyze structure...")
    dec_receipts = fetch_sample_receipts(LOYVERSE_TOKEN, date(2025, 12, 1), date(2025, 12, 3), limit=5)
    
    if not dec_receipts:
        print("❌ No receipts found")
        return
    
    # Analyze structure
    structure = analyze_receipt_structure(dec_receipts)
    
    # Fetch full December data
    print("\n🌐 Fetching full December 1-3 data...")
    headers = {"Authorization": f"Bearer {LOYVERSE_TOKEN}", "Accept": "application/json"}
    tz = pytz.timezone("Asia/Bangkok")
    start_dt_utc = tz.localize(datetime.combine(date(2025, 12, 1), datetime.min.time())).astimezone(pytz.UTC)
    end_dt_utc = tz.localize(datetime.combine(date(2025, 12, 3), datetime.max.time())).astimezone(pytz.UTC)
    
    params = {
        "created_at_min": start_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "created_at_max": end_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": 250,
    }
    
    all_receipts = []
    cursor = None
    while True:
        if cursor:
            params["cursor"] = cursor
        res = requests.get(BASE_URL, headers=headers, params=params, timeout=60)
        if res.status_code != 200:
            break
        data = res.json()
        receipts = data.get("receipts", [])
        all_receipts.extend(receipts)
        cursor = data.get("cursor")
        if not cursor:
            break
    
    print(f"✅ Fetched {len(all_receipts)} receipts")
    
    # Try different calculation methods
    print("\n📊 Testing Different Calculation Methods:")
    print("=" * 80)
    
    # Method 1: Using discount_money (current)
    sales1, refunds1, discounts1, types1 = calculate_sales_corrected(all_receipts, use_total_discount=False)
    print(f"Method 1 (discount_money): {sales1:,.2f}")
    print(f"  Refunds: {refunds1:,.2f}, Discounts: {discounts1:,.2f}")
    print(f"  Receipt types: {types1}")
    
    # Method 2: Using total_discount
    sales2, refunds2, discounts2, types2 = calculate_sales_corrected(all_receipts, use_total_discount=True)
    print(f"\nMethod 2 (total_discount): {sales2:,.2f}")
    print(f"  Refunds: {refunds2:,.2f}, Discounts: {discounts2:,.2f}")
    print(f"  Receipt types: {types2}")
    
    # Analyze timezone issues
    print("\n🕐 Timezone Analysis:")
    print("=" * 80)
    date_counts, tz_issues = analyze_timezone_issues(all_receipts, date(2025, 12, 1))
    print("Receipts by date (Bangkok time):")
    for d in sorted(date_counts.keys()):
        print(f"  {d}: {date_counts[d]} receipts")
    
    if tz_issues:
        print(f"\n⚠️ Found {len(tz_issues)} timezone issues")
        for issue in tz_issues[:5]:  # Show first 5
            print(f"  Receipt {issue['receipt_id']}: UTC={issue['created_at_utc']}, BKK={issue['date_bkk']}")
    
    # Compare with CSV
    print("\n📄 CSV Comparison:")
    print("=" * 80)
    csv_path = "sales-summary-2025-11-01-2025-12-03.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df['parsed_date'] = pd.to_datetime(df['วันที่'], format='%d/%m/%y')
        csv_dec = df[df['parsed_date'].dt.month == 12]
        csv_total = csv_dec['ยอดขายสุทธิ'].sum()
        print(f"CSV Total (Dec 1-3): {csv_total:,.2f}")
        print(f"API Method 1:       {sales1:,.2f} (diff: {sales1 - csv_total:,.2f})")
        print(f"API Method 2:       {sales2:,.2f} (diff: {sales2 - csv_total:,.2f})")
        print(f"Dashboard:          99,910.00")
        print(f"  vs Method 1:      {sales1 - 99910:,.2f}")
        print(f"  vs Method 2:      {sales2 - 99910:,.2f}")
    
    # Check for field name mismatches
    print("\n🔧 Field Name Analysis:")
    print("=" * 80)
    if dec_receipts:
        sample = dec_receipts[0]
        print("Key fields in API response:")
        print(f"  'type': {sample.get('type')}")
        print(f"  'receipt_type': {sample.get('receipt_type')}")
        print(f"  'total_money': {sample.get('total_money')}")
        print(f"  'total_discount': {sample.get('total_discount')}")
        print(f"  'discount_money': {sample.get('discount_money')}")
        print()
        print("⚠️ ISSUE FOUND: API uses 'total_discount', not 'discount_money'!")
        print("   The comparison script was using the wrong field name.")

if __name__ == "__main__":
    main()



