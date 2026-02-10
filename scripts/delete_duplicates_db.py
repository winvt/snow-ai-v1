import sqlite3
import pandas as pd

def delete_duplicates():
    db_path = 'loyverse_data.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 Finding duplicates to delete...")
    
    # Logic: Find groups of (created_at, total_money) with count > 1
    # Keep the one with the lowest receipt_id (or highest? doesn't matter much, let's keep one)
    # Actually, let's keep the one with the 'smallest' receipt_id string just to be deterministic
    
    query = """
    SELECT 
        receipt_id,
        created_at,
        total_money
    FROM receipts
    WHERE receipt_date >= '2025-11-11' AND receipt_date <= '2025-11-13'
    """
    
    df = pd.read_sql_query(query, conn)
    
    # Identify duplicates
    # We want to keep the FIRST occurrence and mark others for deletion
    # Sorting by receipt_id ensures determinism
    df = df.sort_values('receipt_id')
    
    # duplicated() returns True for all duplicates except the first occurrence
    duplicates = df[df.duplicated(['created_at', 'total_money'], keep='first')]
    
    if duplicates.empty:
        print("✅ No duplicates found to delete.")
        conn.close()
        return

    print(f"⚠️ Found {len(duplicates)} duplicates to delete.")
    
    ids_to_delete = duplicates['receipt_id'].tolist()
    
    # Delete from database
    # 1. Delete line items
    print("🗑️ Deleting line items...")
    placeholders = ','.join(['?'] * len(ids_to_delete))
    cursor.execute(f"DELETE FROM line_items WHERE receipt_id IN ({placeholders})", ids_to_delete)
    
    # 2. Delete payments
    print("🗑️ Deleting payments...")
    cursor.execute(f"DELETE FROM payments WHERE receipt_id IN ({placeholders})", ids_to_delete)
    
    # 3. Delete receipts
    print("🗑️ Deleting receipts...")
    cursor.execute(f"DELETE FROM receipts WHERE receipt_id IN ({placeholders})", ids_to_delete)
    
    conn.commit()
    conn.close()
    
    print(f"✅ Successfully deleted {len(ids_to_delete)} duplicate receipts.")

if __name__ == "__main__":
    delete_duplicates()
