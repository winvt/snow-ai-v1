#!/usr/bin/env python3
"""
Test script to verify database persistence behavior
"""

import os
import sys
from database import LoyverseDB

def test_database_persistence():
    """Test database creation and persistence"""
    
    print("🧪 Testing Database Persistence...")
    print("=" * 50)
    
    # Check if database file exists before initialization
    db_path = "loyverse_data.db"
    exists_before = os.path.exists(db_path)
    print(f"📁 Database file exists before init: {exists_before}")
    
    # Initialize database
    print("🔧 Initializing database...")
    db = LoyverseDB()
    
    # Check if database file exists after initialization
    exists_after = os.path.exists(db_path)
    print(f"📁 Database file exists after init: {exists_after}")
    
    # Check table creation
    print("📊 Checking table creation...")
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    table_names = [table[0] for table in tables]
    
    print(f"📋 Tables created: {len(table_names)}")
    for table in table_names:
        print(f"   - {table}")
    
    # Check if we have any data
    print("\n📈 Checking data counts...")
    try:
        receipt_count = db.get_receipt_count()
        customer_count = db.get_customer_count()
        print(f"   - Receipts: {receipt_count}")
        print(f"   - Customers: {customer_count}")
    except Exception as e:
        print(f"   - Error checking counts: {e}")
    
    conn.close()
    
    # File size check
    if exists_after:
        file_size = os.path.getsize(db_path)
        print(f"📏 Database file size: {file_size:,} bytes")
    
    print("\n✅ Database persistence test completed!")
    print("\n💡 Key Points:")
    print("   - Database file is created automatically")
    print("   - Tables are created with 'CREATE TABLE IF NOT EXISTS'")
    print("   - Data persists between application runs")
    print("   - On Render free tier, database resets on deployment")

if __name__ == "__main__":
    test_database_persistence()
