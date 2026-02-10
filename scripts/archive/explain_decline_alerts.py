#!/usr/bin/env python3
"""
Explain customer decline alerts for November 2
"""
from database import LoyverseDB
import pandas as pd
from datetime import date
import pytz
from daily_briefing import detect_customer_decline_daily, compute_signed_net

db = LoyverseDB()

# Customer names from alerts
customer_names = [
    'SI-14 Eat Me',
    'Chaolay-ชาวเล ชั้น1',
    'A-3เฮลตี้ พลัส(โรงA)',
    'D-3 Delight (สถาปัตย์)'
]

print("=" * 70)
print("Customer Decline Alert Explanation - November 2, 2025")
print("=" * 70)
print("\nHow decline is calculated:")
print("1. November 2 is a SUNDAY")
print("2. Compares: This Sunday (Nov 2) vs Previous Sunday (Oct 26)")
print("3. Formula: ((This Sunday - Previous Sunday) / Previous Sunday) × 100%")
print("4. Alert triggered if decline > 50%")
print("\n" + "=" * 70)

# Get customer map
customer_map = db.get_customer_map()
reverse_map = {v: k for k, v in customer_map.items()}

# Get all receipts
df = db.get_receipts_dataframe()
if not df.empty:
    # Convert dates
    df_dates = pd.to_datetime(df['date'])
    if df_dates.dt.tz is None:
        df_dates = df_dates.dt.tz_localize('UTC')
    df['day'] = df_dates.dt.tz_convert('Asia/Bangkok').dt.date
    df['day'] = pd.to_datetime(df['day'])
    df, _ = compute_signed_net(df)
    
    # November 2, 2025 is a Sunday (6)
    nov2 = date(2025, 11, 2)
    nov2_dow = nov2.weekday()  # Sunday = 6
    
    print(f"\nTarget Date: {nov2} ({['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][nov2_dow]})")
    
    for customer_name in customer_names:
        print(f"\n{'=' * 70}")
        print(f"Customer: {customer_name}")
        print('=' * 70)
        
        # Find customer ID
        customer_id = None
        for cid, name in customer_map.items():
            if customer_name.lower() in name.lower() or name.lower() in customer_name.lower():
                customer_id = cid
                print(f"Customer ID: {cid}")
                break
        
        if not customer_id:
            print(f"⚠️ Customer not found in database")
            continue
        
        # Get customer data
        cust_df = df[df['customer_id'] == customer_id].copy()
        cust_df = cust_df.sort_values('day')
        
        if cust_df.empty:
            print("⚠️ No transactions found")
            continue
        
        # Filter to same day of week (Sunday = 6)
        cust_df['day_of_week'] = cust_df['day'].dt.dayofweek
        same_dow_data = cust_df[cust_df['day_of_week'] == nov2_dow]
        
        if len(same_dow_data) < 2:
            print(f"⚠️ Not enough Sunday transactions (need at least 2)")
            print(f"   Found {len(same_dow_data)} Sunday transaction(s)")
            continue
        
        # Get Sunday totals
        metric_col = "signed_net" if "signed_net" in same_dow_data.columns else "line_total"
        sunday_totals = same_dow_data.groupby(same_dow_data['day'].dt.date)[metric_col].sum().sort_index()
        
        if len(sunday_totals) < 2:
            print(f"⚠️ Not enough Sunday data points")
            continue
        
        # Get last 2 Sundays
        latest_date = sunday_totals.index[-1]
        previous_date = sunday_totals.index[-2]
        
        latest_amount = float(sunday_totals.iloc[-1])
        previous_amount = float(sunday_totals.iloc[-2])
        
        print(f"\n📅 Comparison:")
        print(f"   Previous Sunday ({previous_date}): ฿{previous_amount:,.2f}")
        print(f"   Latest Sunday   ({latest_date}): ฿{latest_amount:,.2f}")
        
        if previous_amount == 0:
            print(f"\n⚠️ Previous Sunday had zero sales")
            print(f"   Cannot calculate percentage decline")
            continue
        
        # Calculate decline
        change = latest_amount - previous_amount
        decline_pct = (change / previous_amount) * 100
        
        print(f"\n📊 Calculation:")
        print(f"   Change: ฿{change:,.2f} ({change:+,.2f})")
        print(f"   Decline: {abs(decline_pct):.1f}%")
        
        if decline_pct < -50:
            print(f"\n⚠️ ALERT: Sales dropped by {abs(decline_pct):.1f}%")
            print(f"   This is a significant decline (>50%)")
            
            # Show what percentage of previous they spent
            percent_of_previous = (latest_amount / previous_amount) * 100
            print(f"   Current spending is {percent_of_previous:.1f}% of previous Sunday")
        else:
            print(f"\n✅ No alert: Decline is {abs(decline_pct):.1f}% (less than 50%)")
        
        # Show all Sunday transactions for context
        print(f"\n📋 All Sunday transactions for this customer:")
        sunday_transactions = same_dow_data[same_dow_data['day'].dt.date.isin([previous_date, latest_date])].copy()
        sunday_transactions['date_str'] = sunday_transactions['day'].dt.date
        for date_val in [previous_date, latest_date]:
            day_data = sunday_transactions[sunday_transactions['date_str'] == date_val]
            if not day_data.empty:
                total = day_data[metric_col].sum()
                count = len(day_data)
                print(f"   {date_val} ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][date_val.weekday()]}): ฿{total:,.2f} ({count} transaction(s))")

print(f"\n\n{'=' * 70}")
print("Summary:")
print("=" * 70)
print("Decline alerts are generated when:")
print("1. Daily report compares same day of week (Sunday vs previous Sunday)")
print("2. Sales drop by more than 50%")
print("3. Formula: ((Current - Previous) / Previous) × 100")
print("\nExample:")
print("  Previous Sunday: ฿10,000")
print("  Current Sunday: ฿1,250")
print("  Decline: ((1,250 - 10,000) / 10,000) × 100 = -87.5%")
print("  → Alert: 87.5% decline")
print("\nNote: Negative decline means sales decreased.")
print("=" * 70)




