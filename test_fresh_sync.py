import os
import pandas as pd
from database import LoyverseDB
from verify_november_sales import fetch_november_receipts
from datetime import datetime

def main():
    # 1. Setup Fresh DB
    db_path = "loyverse_data.db"
    if os.path.exists(db_path):
        print(f"⚠️ Removing existing {db_path} for fresh test...")
        os.remove(db_path)
    
    print("🆕 Initializing fresh database...")
    db = LoyverseDB(db_path)
    
    # 2. Fetch Data
    print("📥 Fetching November receipts from API...")
    receipts = fetch_november_receipts()
    
    # 3. Save to DB
    print(f"💾 Saving {len(receipts)} receipts to database...")
    count = db.save_receipts(receipts)
    print(f"✅ Saved {count} receipts.")
    
    # 4. Analyze DB Content
    print("🔍 Analyzing database content...")
    conn = db.get_connection()
    
    # Check for duplicates by content (created_at + total_money)
    query = """
        SELECT created_at, total_money, COUNT(*) as count, GROUP_CONCAT(receipt_id) as ids
        FROM receipts
        GROUP BY created_at, total_money
        HAVING count > 1
        ORDER BY count DESC
    """
    df_dupes = pd.read_sql_query(query, conn)
    
    print(f"\n📊 Duplicate Analysis (Same Time & Amount):")
    if not df_dupes.empty:
        print(f"❌ Found {len(df_dupes)} groups of duplicates!")
        print(df_dupes.head(10))
        print(f"Total potential duplicate receipts: {df_dupes['count'].sum() - len(df_dupes)}")
    else:
        print("✅ No content duplicates found.")
        
    # Check Total Sales vs CSV
    query_sales = """
        SELECT DATE(created_at) as date, SUM(total_money) as total_sales
        FROM receipts
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    df_sales = pd.read_sql_query(query_sales, conn)
    conn.close()
    
    print("\n💰 DB Sales vs CSV:")
    # Load CSV for comparison
    csv_file = "sales-summary-2025-11-01-2025-11-30.csv"
    if os.path.exists(csv_file):
        df_csv = pd.read_csv(csv_file)
        # Basic cleanup of CSV date for matching
        # Assuming CSV is DD/MM/YY
        # We'll just print the DB totals for the user to compare visually or implement strict matching if needed
        print(df_sales)
        print(f"\nTotal DB Sales: {df_sales['total_sales'].sum():,.2f}")
    else:
        print("⚠️ CSV file not found for comparison.")

if __name__ == "__main__":
    main()
