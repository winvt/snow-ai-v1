import sqlite3
import pandas as pd
import pytz
from datetime import datetime

def check_nov12_duplicates():
    db_path = 'loyverse_data.db'
    conn = sqlite3.connect(db_path)
    
    # Fetch receipts for Nov 12 (Bangkok Time)
    # Nov 12 00:00 BKK = Nov 11 17:00 UTC
    # Nov 13 00:00 BKK = Nov 12 17:00 UTC
    query = """
    SELECT 
        receipt_number,
        receipt_date,
        total_money,
        created_at,
        receipt_id
    FROM receipts
    WHERE receipt_date >= '2025-11-11' AND receipt_date <= '2025-11-13'
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert to datetime
    df['dt_utc'] = pd.to_datetime(df['created_at'])
    bangkok_tz = pytz.timezone('Asia/Bangkok')
    df['dt_bkk'] = df['dt_utc'].dt.tz_convert(bangkok_tz)
    
    # Filter for Nov 12
    start_date = bangkok_tz.localize(datetime(2025, 11, 12))
    end_date = bangkok_tz.localize(datetime(2025, 11, 13))
    
    nov12_df = df[(df['dt_bkk'] >= start_date) & (df['dt_bkk'] < end_date)].copy()
    
    print(f"Total Receipts on Nov 12: {len(nov12_df)}")
    
    # Check for duplicates based on (created_at, total_money)
    # Note: receipt_number might be different if they are different entries in API but same logical receipt?
    # Or if receipt_number is same?
    
    # Check duplicate receipt numbers
    dup_numbers = nov12_df[nov12_df.duplicated('receipt_number', keep=False)]
    if not dup_numbers.empty:
        print(f"\n⚠️ Found {len(dup_numbers)} receipts with duplicate Receipt Numbers:")
        print(dup_numbers[['receipt_number', 'total_money', 'created_at']].sort_values('receipt_number'))
    else:
        print("\n✅ No duplicate Receipt Numbers found.")

    # Check duplicate (created_at, total_money)
    # This catches cases where receipt_number might be different (or null?) but it's the same transaction
    dup_content = nov12_df[nov12_df.duplicated(['created_at', 'total_money'], keep=False)]
    if not dup_content.empty:
        print(f"\n⚠️ Found {len(dup_content)} receipts with same Timestamp & Amount:")
        print(dup_content[['receipt_number', 'total_money', 'created_at']].sort_values('created_at').head(20))
    else:
        print("\n✅ No duplicate Timestamp & Amount found.")

if __name__ == "__main__":
    check_nov12_duplicates()
