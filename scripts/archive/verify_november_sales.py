import pandas as pd
import requests
import os
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

def parse_csv(filepath):
    """Parse the sales summary CSV."""
    print(f"📂 Reading CSV: {filepath}")
    df = pd.read_csv(filepath)
    
    # Rename columns for easier access
    # วันที่,ยอดขายรวม,การคืนเงิน,ส่วนลด,ยอดขายสุทธิ,...
    df = df.rename(columns={
        'วันที่': 'date_str',
        'ยอดขายสุทธิ': 'net_sales_csv'
    })
    
    # Parse date (DD/MM/YY)
    def parse_date(d_str):
        return datetime.strptime(d_str, '%d/%m/%y').date()
        
    df['date'] = df['date_str'].apply(parse_date)
    return df[['date', 'net_sales_csv']]

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
    
    # Retry logic
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
                    break # Try next attempt
                    
                data = resp.json()
                receipts = data.get('receipts', [])
                day_receipts.extend(receipts)
                
                cursor = data.get('cursor')
                if not cursor:
                    return day_receipts # Success
                
                time.sleep(0.1)
            
            # If we exit while loop without returning, it means we broke due to error
            # so we continue to next attempt
            
        except Exception as e:
            print(f"   ⚠️ Exception fetching {date_obj}: {e}")
            time.sleep(1)
    
    print(f"❌ Failed to fetch complete data for {date_obj}")
    return day_receipts # Return what we have

def fetch_november_receipts():
    """Fetch all receipts for November 2025 day by day."""
    print("📅 Fetching receipts for November 2025 (Day by Day)...")
    
    all_receipts = []
    # Iterate from Nov 1 to Nov 30
    start_date = datetime(2025, 11, 1).date()
    end_date = datetime(2025, 11, 30).date()
    
    current_date = start_date
    while current_date <= end_date:
        print(f"   Fetching {current_date}...", end='\r')
        day_receipts = fetch_receipts_for_day(current_date)
        all_receipts.extend(day_receipts)
        current_date += timedelta(days=1)
        
    print(f"\n✅ Total receipts fetched: {len(all_receipts)}")
    return all_receipts

def process_receipts(receipts):
    """Aggregate receipts by date."""
    daily_sales = {}
    tz = pytz.timezone('Asia/Bangkok')
    
    for r in receipts:
        # Parse created_at (UTC)
        created_at_str = r['created_at']
        if created_at_str.endswith('Z'):
            created_at_str = created_at_str[:-1] + '+00:00'
        
        dt_utc = datetime.fromisoformat(created_at_str)
        dt_bkk = dt_utc.astimezone(tz)
        date_key = dt_bkk.date()
        
        # Sum total_money (Net sales usually corresponds to total_money in simple cases, 
        # but strictly it's total_money - refunds. For now assuming total_money matches 'Net Sales' 
        # based on previous context, or we might need to adjust for refunds if receipt_type is REFUND)
        
        amount = float(r.get('total_money', 0))
        
        # If receipt_type is REFUND, the amount is usually negative in total_money or handled separately.
        # Loyverse API 'total_money' for REFUND is typically negative.
        # Let's check receipt_type just in case.
        if r.get('receipt_type') == 'REFUND':
             # Ensure it's treated as negative if it's positive in the API (it usually is negative)
             # But let's trust total_money first.
             pass

        daily_sales[date_key] = daily_sales.get(date_key, 0) + amount
        
    return daily_sales

def main():
    csv_file = "sales-summary-2025-11-01-2025-11-30.csv"
    if not os.path.exists(csv_file):
        print(f"❌ CSV file not found: {csv_file}")
        return

    # 1. Load CSV Data
    df_csv = parse_csv(csv_file)
    
    # 2. Fetch API Data
    receipts = fetch_november_receipts()
    
    # 3. Process API Data
    api_sales_map = process_receipts(receipts)
    
    # 4. Compare
    print("\n📊 COMPARISON REPORT (November 2025)")
    print(f"{'Date':<12} | {'CSV Net Sales':<15} | {'API Sales':<15} | {'Diff':<15} | {'Status'}")
    print("-" * 75)
    
    total_csv = 0
    total_api = 0
    
    # Sort by date
    all_dates = sorted(df_csv['date'].unique())
    
    for d in all_dates:
        csv_val = df_csv[df_csv['date'] == d]['net_sales_csv'].sum()
        api_val = api_sales_map.get(d, 0.0)
        
        diff = api_val - csv_val
        total_csv += csv_val
        total_api += api_val
        
        status = "✅ OK"
        if abs(diff) > 1.0:
            if diff > 0:
                status = "🔴 API Higher"
            else:
                status = "🔵 CSV Higher"
        
        print(f"{d} | {csv_val:,.2f}       | {api_val:,.2f}       | {diff:+,.2f}       | {status}")

    print("-" * 75)
    print(f"{'TOTAL':<12} | {total_csv:,.2f}       | {total_api:,.2f}       | {total_api - total_csv:+,.2f}")

if __name__ == "__main__":
    main()
