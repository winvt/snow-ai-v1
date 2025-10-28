#!/usr/bin/env python3
"""
Setup script to create an empty database with proper structure
This is for fresh deployments on Render
"""

import os
import sys
from database import LoyverseDB

def create_empty_database():
    """Create an empty database with all required tables"""
    print("🔧 Creating empty database...")
    
    # Get database path from environment or use default
    db_path = os.getenv('DATABASE_PATH', 'loyverse_data.db')
    
    try:
        # Remove existing database if it exists
        if os.path.exists(db_path):
            print(f"🗑️ Removing existing database: {db_path}")
            os.remove(db_path)
        
        # Create new database with tables
        db = LoyverseDB(db_path)
        
        # Verify tables exist
        if db.verify_tables_exist():
            print("✅ Empty database created successfully")
            print(f"📁 Database path: {db_path}")
            
            # Get basic stats (should all be 0)
            stats = db.get_database_stats()
            print(f"📊 Database stats:")
            print(f"   - Customers: {stats['customers']}")
            print(f"   - Receipts: {stats['receipts']}")
            print(f"   - Line items: {stats['line_items']}")
            print(f"   - Categories: {stats['categories']}")
            print(f"   - Items: {stats['items']}")
            
            print("\n🎯 Next steps:")
            print("1. Deploy this to Render")
            print("2. Use the Settings tab to sync data from Loyverse API")
            print("3. The sync will populate the database with your actual data")
            
            return True
        else:
            print("❌ Database creation failed - tables not created")
            return False
            
    except Exception as e:
        print(f"❌ Database creation error: {e}")
        return False

if __name__ == "__main__":
    success = create_empty_database()
    sys.exit(0 if success else 1)
