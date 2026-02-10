#!/usr/bin/env python3
"""
Database initialization script for Render deployment
Ensures database tables are created before the app starts
"""

import os
import sys
from database import LoyverseDB

def main():
    print("🔧 Initializing database...")
    
    # Get database path from environment or use default
    db_path = os.getenv('DATABASE_PATH', 'loyverse_data.db')
    
    try:
        # Initialize database (this creates tables if they don't exist)
        db = LoyverseDB(db_path)
        
        # Verify tables exist
        if db.verify_tables_exist():
            print("✅ Database initialization successful")
            print(f"📁 Database path: {db_path}")
            
            # Get basic stats
            stats = db.get_database_stats()
            print(f"📊 Database stats:")
            print(f"   - Customers: {stats['customers']}")
            print(f"   - Receipts: {stats['receipts']}")
            print(f"   - Line items: {stats['line_items']}")
            print(f"   - Categories: {stats['categories']}")
            print(f"   - Items: {stats['items']}")
            
            return 0
        else:
            print("❌ Database initialization failed - tables not created")
            return 1
            
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
