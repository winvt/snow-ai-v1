#!/usr/bin/env python3
"""
Script to fetch current month's sales from Loyverse API and compare with exported CSV data.
"""
import os
import requests
import pandas as pd
from datetime import datetime, date
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN", "d18826e6c76345888204b310aaca1351")
BASE_URL = "https://api.loyverse.com/v1.0/receipts"

def fetch_receipts_from_api(token: str, start_date: date, end_date: date):
    """Fetch receipts from Loyverse API for a date range (Bangkok -> UTC)."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # Convert Bangkok local date range to UTC timestamps expected by API
    tz = pytz.timezone("Asia/Bangkok")
    start_dt_utc = tz.localize(datetime.combine(start_date, datetime.min.time())).astimezone(pytz.UTC)
    end_dt_utc = tz.localize(datetime.combine(end_date, datetime.max.time())).astimezone(pytz.UTC)
    
    params = {
        "created_at_min": start_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "created_at_max": end_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": 250,
    }
    
    all_receipts = []
    cursor = None
    page_count = 0
    
    print(f"Fetching receipts from {start_date} to {end_date} (Bangkok time)...")
    print(f"API range (UTC): {start_dt_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_dt_utc.strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        page_count += 1
        if cursor:
            params["cursor"] = cursor
        
        try:
            res = requests.get(BASE_URL, headers=headers, params=params, timeout=60)
            
            if res.status_code != 200:
                print(f"❌ Error {res.status_code}: {res.text}")
                break
            
            data = res.json()
            receipts = data.get("receipts", [])
            all_receipts.extend(receipts)
            cursor = data.get("cursor")
            
            print(f"  Page {page_count}: {len(receipts)} receipts (Total: {len(all_receipts)})")
            
            if not cursor:
                break
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
            break
    
    print(f"✅ Fetched {len(all_receipts)} receipts total\n")
    return all_receipts

def calculate_sales_from_receipts(receipts):
    """Calculate total sales from receipts, handling refunds correctly."""
    total_sales = 0.0
    total_refunds = 0.0
    total_discounts = 0.0
    receipt_types = {}
    
    for receipt in receipts:
        # API uses 'receipt_type' field, values are uppercase: 'SALE', 'REFUND'
        receipt_type = (receipt.get("receipt_type") or receipt.get("type") or "").upper()
        receipt_total = float(receipt.get("total_money", 0) or 0)
        # API uses 'total_discount', not 'discount_money'
        receipt_discount = float(receipt.get("total_discount", 0) or 0)
        
        # Count receipt types
        receipt_types[receipt_type] = receipt_types.get(receipt_type, 0) + 1
        
        net_amount = receipt_total - receipt_discount
        
        if receipt_type == "REFUND":
            total_refunds += net_amount
            total_sales -= net_amount  # Refunds subtract from sales
        else:
            total_sales += net_amount
            total_discounts += receipt_discount
    
    return total_sales, total_refunds, total_discounts, receipt_types

def calculate_csv_totals(csv_path):
    """Calculate totals from the CSV file."""
    df = pd.read_csv(csv_path)
    
    # The CSV columns are in Thai:
    # วันที่,ยอดขายรวม,การคืนเงิน,ส่วนลด,ยอดขายสุทธิ,ต้นทุนของสินค้า,กำไรรวม,กำไร,ภาษี
    # Date, Total Sales, Refunds, Discounts, Net Sales, Cost, Gross Profit, Profit %, Tax
    
    total_gross = df["ยอดขายรวม"].sum()
    total_refunds = df["การคืนเงิน"].sum()
    total_discounts = df["ส่วนลด"].sum()
    total_net = df["ยอดขายสุทธิ"].sum()
    
    return {
        "total_gross": total_gross,
        "total_refunds": total_refunds,
        "total_discounts": total_discounts,
        "total_net": total_net,
        "date_range": f"{df['วันที่'].iloc[-1]} to {df['วันที่'].iloc[0]}",
        "num_days": len(df)
    }

def main():
    print("=" * 80)
    print("Sales Comparison: API vs CSV Export")
    print("=" * 80)
    print()
    
    # Read CSV data
    csv_path = "sales-summary-2025-11-01-2025-12-03.csv"
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return
    
    print("📊 Analyzing CSV data...")
    csv_totals = calculate_csv_totals(csv_path)
    print(f"  Date range: {csv_totals['date_range']}")
    print(f"  Number of days: {csv_totals['num_days']}")
    print(f"  Total Gross Sales: {csv_totals['total_gross']:,.2f}")
    print(f"  Total Refunds: {csv_totals['total_refunds']:,.2f}")
    print(f"  Total Discounts: {csv_totals['total_discounts']:,.2f}")
    print(f"  Total Net Sales: {csv_totals['total_net']:,.2f}")
    print()
    
    # Determine date range for API fetch
    # CSV shows Nov 1 - Dec 3, 2025
    # Let's fetch both November and December to compare
    # First, let's check what the current date actually is
    today = date.today()
    print(f"📅 Current date: {today}")
    print()
    
    # Fetch November 2025 data
    nov_start = date(2025, 11, 1)
    nov_end = date(2025, 11, 30)
    
    # Fetch December 2025 data (up to today if we're in 2025, or full month if future)
    dec_start = date(2025, 12, 1)
    dec_end = date(2025, 12, 31) if today.year >= 2025 else date(2025, 12, 3)
    
    print("🌐 Fetching November 2025 data from Loyverse API...")
    nov_receipts = fetch_receipts_from_api(LOYVERSE_TOKEN, nov_start, nov_end)
    
    print("🌐 Fetching December 2025 data from Loyverse API...")
    dec_receipts = fetch_receipts_from_api(LOYVERSE_TOKEN, dec_start, dec_end)
    
    if not nov_receipts and not dec_receipts:
        print("⚠️ No receipts fetched from API")
        return
    
    # Calculate sales from API receipts
    nov_total_sales, nov_total_refunds, nov_total_discounts, nov_types = calculate_sales_from_receipts(nov_receipts)
    dec_total_sales, dec_total_refunds, dec_total_discounts, dec_types = calculate_sales_from_receipts(dec_receipts)
    
    print("📈 API Results:")
    print(f"  November:")
    print(f"    Total Receipts: {len(nov_receipts)}")
    print(f"    Receipt Types: {nov_types}")
    print(f"    Total Refunds: {nov_total_refunds:,.2f}")
    print(f"    Total Discounts: {nov_total_discounts:,.2f}")
    print(f"    Total Net Sales: {nov_total_sales:,.2f}")
    print()
    print(f"  December:")
    print(f"    Total Receipts: {len(dec_receipts)}")
    print(f"    Receipt Types: {dec_types}")
    print(f"    Total Refunds: {dec_total_refunds:,.2f}")
    print(f"    Total Discounts: {dec_total_discounts:,.2f}")
    print(f"    Total Net Sales: {dec_total_sales:,.2f}")
    print()
    
    # Try different calculations for dashboard comparison
    print("🔍 Alternative Calculations (for Dashboard 99.91k):")
    # Maybe dashboard shows gross sales without refunds?
    dec_gross = sum(float(r.get("total_money", 0) or 0) for r in dec_receipts if r.get("type", "").lower() != "refund")
    print(f"  December Gross (no refunds): {dec_gross:,.2f}")
    print(f"  Difference from dashboard: {dec_gross - 99910:,.2f}")
    print()
    
    # Maybe dashboard shows Dec 1-2 only?
    dec_1_2_receipts = [r for r in dec_receipts if r.get("created_at")]
    dec_1_2_receipts_filtered = []
    for receipt in dec_1_2_receipts:
        created_at = receipt.get("created_at")
        if created_at:
            receipt_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            receipt_dt_bkk = receipt_dt.astimezone(pytz.timezone("Asia/Bangkok"))
            if receipt_dt_bkk.date() <= date(2025, 12, 2):
                dec_1_2_receipts_filtered.append(receipt)
    
    if dec_1_2_receipts_filtered:
        dec_1_2_sales, _, _, _ = calculate_sales_from_receipts(dec_1_2_receipts_filtered)
        print(f"  December 1-2 only: {dec_1_2_sales:,.2f}")
        print(f"  Difference from dashboard: {dec_1_2_sales - 99910:,.2f}")
        print()
    
    # Compare with CSV
    print("=" * 80)
    print("COMPARISON")
    print("=" * 80)
    print()
    
    # For December only (from CSV, Dec 1-3)
    csv_dec_df = pd.read_csv(csv_path)
    # Parse dates - format is "3/12/25" (day/month/year)
    csv_dec_df['parsed_date'] = pd.to_datetime(csv_dec_df['วันที่'], format='%d/%m/%y')
    csv_dec_df = csv_dec_df[csv_dec_df['parsed_date'].dt.month == 12]
    
    csv_dec_net = csv_dec_df['ยอดขายสุทธิ'].sum()
    
    # CSV November data
    csv_nov_df = pd.read_csv(csv_path)
    csv_nov_df['parsed_date'] = pd.to_datetime(csv_nov_df['วันที่'], format='%d/%m/%y')
    csv_nov_df_only = csv_nov_df[csv_nov_df['parsed_date'].dt.month == 11]
    csv_nov_net = csv_nov_df_only['ยอดขายสุทธิ'].sum()
    
    print("📅 November 2025 Comparison:")
    print(f"  CSV (Nov 1-30): {csv_nov_net:,.2f}")
    print(f"  API (Nov 1-30): {nov_total_sales:,.2f}")
    print(f"  Difference:     {nov_total_sales - csv_nov_net:,.2f}")
    print()
    
    print("📅 December 1-3 Comparison:")
    print(f"  CSV (Dec 1-3): {csv_dec_net:,.2f}")
    print(f"  API (Dec 1-3): {dec_total_sales:,.2f}")
    print(f"  Difference:    {dec_total_sales - csv_dec_net:,.2f}")
    print()
    
    # Full December month comparison with dashboard
    print("📊 Dashboard Comparison (99.91k):")
    print(f"  API (Full Dec 2025): {dec_total_sales:,.2f}")
    print(f"  Dashboard shows:     99,910.00")
    print(f"  Difference:          {dec_total_sales - 99910:,.2f}")
    print()
    print(f"  API (Nov 2025):      {nov_total_sales:,.2f}")
    print(f"  Dashboard (99.91k) could be November?")
    print(f"  Difference:          {nov_total_sales - 99910:,.2f}")
    print()
    
    # Also check full CSV period
    print("📋 Full CSV Period (Nov 1 - Dec 3):")
    print(f"  CSV Total: {csv_totals['total_net']:,.2f}")
    print()
    
    # Detailed breakdown by day for December
    print("Daily Breakdown (December):")
    print("-" * 80)
    daily_receipts = {}
    for receipt in dec_receipts:
        # Parse receipt date
        created_at = receipt.get("created_at")
        if created_at:
            receipt_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            receipt_dt_bkk = receipt_dt.astimezone(pytz.timezone("Asia/Bangkok"))
            day_key = receipt_dt_bkk.date()
            
            if day_key not in daily_receipts:
                daily_receipts[day_key] = []
            daily_receipts[day_key].append(receipt)
    
    for day in sorted(daily_receipts.keys()):
        day_receipts = daily_receipts[day]
        day_sales, day_refunds, day_discounts, _ = calculate_sales_from_receipts(day_receipts)
        print(f"{day.strftime('%d/%m/%y')}: {day_sales:,.2f} ({len(day_receipts)} receipts)")

if __name__ == "__main__":
    main()

