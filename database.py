"""
Database module for persistent local storage of Loyverse data
"""
import sqlite3
import pandas as pd
from datetime import datetime
import json

class LoyverseDB:
    def __init__(self, db_path=None):
        # Use persistent disk path if available, otherwise local path
        if db_path is None:
            import os
            # Check for DATABASE_PATH environment variable first (Render persistent disk)
            env_db_path = os.getenv('DATABASE_PATH')
            if env_db_path:
                # Create directory if it doesn't exist
                try:
                    os.makedirs(os.path.dirname(env_db_path), exist_ok=True)
                    self.db_path = env_db_path
                    print(f"✅ Using persistent disk database: {self.db_path}")
                except (OSError, PermissionError) as e:
                    print(f"⚠️ Warning: Could not create database directory {os.path.dirname(env_db_path)}: {e}")
                    # Fallback to current directory - CRITICAL: Actually use the fallback path
                    self.db_path = "loyverse_data.db"
                    print(f"🔄 Falling back to local database: {self.db_path}")
            else:
                # Fallback to current directory (works on Render free tier)
                self.db_path = "loyverse_data.db"
                print(f"📁 Using local database: {self.db_path}")
        else:
            self.db_path = db_path
            print(f"📁 Using specified database: {self.db_path}")
        self.init_database()
    
    def get_connection(self):
        """Create a database connection"""
        try:
            return sqlite3.connect(self.db_path)
        except sqlite3.OperationalError as e:
            if "unable to open database file" in str(e):
                # Try to create the directory and file
                import os
                try:
                    os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
                    return sqlite3.connect(self.db_path)
                except Exception as create_error:
                    print(f"❌ Error creating database directory: {create_error}")
                    # If we're using persistent disk path, try fallback to local
                    if self.db_path.startswith('/opt/render'):
                        print("🔄 Persistent disk failed, trying local fallback...")
                        fallback_path = "loyverse_data.db"
                        try:
                            self.db_path = fallback_path
                            print(f"✅ Switched to fallback database: {self.db_path}")
                            return sqlite3.connect(self.db_path)
                        except Exception as fallback_error:
                            print(f"❌ Fallback database also failed: {fallback_error}")
                    # Last resort: in-memory database
                    print("⚠️ Falling back to in-memory database (data will be lost on restart)")
                    return sqlite3.connect(":memory:")
            else:
                raise e
    
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            print(f"✅ Database connection established for: {self.db_path}")
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            raise e
        
        # Customers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT,
                customer_code TEXT,
                email TEXT,
                phone TEXT,
                total_visits INTEGER,
                total_spent REAL,
                first_visit TEXT,
                last_visit TEXT,
                last_updated TEXT,
                raw_data TEXT
            )
        """)
        
        # Receipts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                receipt_id TEXT PRIMARY KEY,
                receipt_number TEXT,
                receipt_date TEXT,
                created_at TEXT,
                updated_at TEXT,
                store_id TEXT,
                customer_id TEXT,
                employee_id TEXT,
                total_money REAL,
                total_tax REAL,
                total_discount REAL,
                receipt_type TEXT,
                source TEXT,
                dining_option TEXT,
                location TEXT,
                raw_data TEXT,
                last_updated TEXT
            )
        """)
        
        # Line items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS line_items (
                line_item_id TEXT PRIMARY KEY,
                receipt_id TEXT,
                item_id TEXT,
                variant_id TEXT,
                item_name TEXT,
                sku TEXT,
                quantity REAL,
                price REAL,
                total_money REAL,
                cost REAL,
                FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id)
            )
        """)
        
        # Payments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id TEXT,
                payment_type_id TEXT,
                payment_name TEXT,
                payment_type TEXT,
                money_amount REAL,
                paid_at TEXT,
                FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id)
            )
        """)
        
        # Metadata table for tracking last sync
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                last_updated TEXT
            )
        """)
        
        # Payment types table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payment_types (
                payment_type_id TEXT PRIMARY KEY,
                name TEXT,
                type TEXT,
                last_updated TEXT
            )
        """)
        
        # Stores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stores (
                store_id TEXT PRIMARY KEY,
                name TEXT,
                address_line1 TEXT,
                address_line2 TEXT,
                city TEXT,
                country TEXT,
                phone TEXT,
                last_updated TEXT,
                raw_data TEXT
            )
        """)
        
        # Employees table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                last_updated TEXT,
                raw_data TEXT
            )
        """)
        
        # Categories table (your 23 locations!)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id TEXT PRIMARY KEY,
                name TEXT,
                color TEXT,
                last_updated TEXT
            )
        """)
        
        # Items table (products with category/location link)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_id TEXT PRIMARY KEY,
                variant_id TEXT,
                name TEXT,
                sku TEXT,
                category_id TEXT,
                price REAL,
                cost REAL,
                last_updated TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(category_id)
            )
        """)
        
        # Manual product categories table (user overrides)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_product_categories (
                product_name TEXT PRIMARY KEY,
                category TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_date ON receipts(receipt_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_store ON receipts(store_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_type ON receipts(receipt_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_created ON receipts(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_receipt ON line_items(receipt_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_line_items_item ON line_items(item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_receipt ON payments(receipt_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id)")
        
        conn.commit()
        conn.close()
        print(f"✅ Database tables initialized successfully for: {self.db_path}")
    
    def verify_tables_exist(self):
        """Verify that all required tables exist"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if customers table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
            if not cursor.fetchone():
                print("❌ Customers table does not exist")
                return False
            
            # Check other critical tables
            required_tables = ['receipts', 'line_items', 'payment_types', 'stores', 'employees']
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if not cursor.fetchone():
                    print(f"❌ {table} table does not exist")
                    return False
            
            conn.close()
            print("✅ All required tables exist")
            return True
            
        except Exception as e:
            print(f"❌ Error verifying tables: {e}")
            return False
    
    # ===== CUSTOMER METHODS =====
    
    def save_customers(self, customers):
        """Save or update customers in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for customer in customers:
            cursor.execute("""
                INSERT OR REPLACE INTO customers (
                    customer_id, name, customer_code, email, phone,
                    total_visits, total_spent, first_visit, last_visit,
                    last_updated, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer.get('id'),
                customer.get('name'),
                customer.get('customer_code'),
                customer.get('email'),
                customer.get('phone'),
                customer.get('total_visits'),
                customer.get('total_spent'),
                customer.get('first_visit'),
                customer.get('last_visit'),
                datetime.now().isoformat(),
                json.dumps(customer)
            ))
        
        conn.commit()
        conn.close()
        return len(customers)
    
    def get_all_customers(self):
        """Get all customers from database"""
        conn = self.get_connection()
        df = pd.read_sql_query(
            "SELECT customer_id, name, customer_code, email, phone FROM customers",
            conn
        )
        conn.close()
        return df
    
    def get_customer_map(self):
        """Get customer ID to name mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT customer_id, name, customer_code FROM customers")
        
        customer_map = {}
        for row in cursor.fetchall():
            customer_id, name, customer_code = row
            display_name = name if name else customer_code if customer_code else "Unknown"
            customer_map[customer_id] = display_name
        
        conn.close()
        return customer_map
    
    def get_customer_count(self):
        """Get total number of customers in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM customers")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ===== RECEIPT METHODS =====
    
    def save_receipts(self, receipts):
        """Save or update receipts with line items and payments"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for receipt in receipts:
            receipt_id = receipt.get('id') or receipt.get('receipt_number')
            
            # Save receipt
            cursor.execute("""
                INSERT OR REPLACE INTO receipts (
                    receipt_id, receipt_number, receipt_date, created_at, updated_at,
                    store_id, customer_id, employee_id, total_money, total_tax,
                    total_discount, receipt_type, source, dining_option, location, 
                    raw_data, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                receipt_id,
                receipt.get('receipt_number'),
                receipt.get('receipt_date'),
                receipt.get('created_at'),
                receipt.get('updated_at'),
                receipt.get('store_id'),
                receipt.get('customer_id'),
                receipt.get('employee_id'),
                receipt.get('total_money'),
                receipt.get('total_tax'),
                receipt.get('total_discount'),
                receipt.get('receipt_type'),
                receipt.get('source'),
                receipt.get('dining_option'),
                receipt.get('dining_option'),  # Use dining_option as location
                json.dumps(receipt),
                datetime.now().isoformat()
            ))
            
            # Delete old line items and payments for this receipt
            cursor.execute("DELETE FROM line_items WHERE receipt_id = ?", (receipt_id,))
            cursor.execute("DELETE FROM payments WHERE receipt_id = ?", (receipt_id,))
            
            # Save line items
            for line_item in receipt.get('line_items', []):
                cursor.execute("""
                    INSERT INTO line_items (
                        line_item_id, receipt_id, item_id, variant_id, item_name,
                        sku, quantity, price, total_money, cost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    line_item.get('id'),
                    receipt_id,
                    line_item.get('item_id'),
                    line_item.get('variant_id'),
                    line_item.get('item_name'),
                    line_item.get('sku'),
                    line_item.get('quantity'),
                    line_item.get('price'),
                    line_item.get('total_money'),
                    line_item.get('cost')
                ))
            
            # Save payments
            for payment in receipt.get('payments', []):
                cursor.execute("""
                    INSERT INTO payments (
                        receipt_id, payment_type_id, payment_name,
                        payment_type, money_amount, paid_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    receipt_id,
                    payment.get('payment_type_id'),
                    payment.get('name'),
                    payment.get('type'),
                    payment.get('money_amount'),
                    payment.get('paid_at')
                ))
        
        conn.commit()
        conn.close()
        return len(receipts)
    
    def get_receipts_dataframe(self, start_date=None, end_date=None, store_id=None):
        """Get receipts as DataFrame for dashboard with location from categories"""
        conn = self.get_connection()
        
        # Optimized query with better indexing hints
        query = """
            SELECT 
                r.created_at as date,
                r.store_id,
                r.customer_id,
                r.receipt_number as bill_number,
                r.dining_option,
                r.employee_id,
                r.receipt_type,
                li.item_id,
                li.sku,
                li.item_name as item,
                li.quantity,
                li.price,
                li.total_money as line_total,
                r.total_money as receipt_total,
                r.total_discount as receipt_discount,
                r.total_tax as receipt_tax,
                i.category_id,
                c.name as location,
                GROUP_CONCAT(p.payment_type_id, '+') as bill_type
            FROM receipts r
            LEFT JOIN line_items li ON r.receipt_id = li.receipt_id
            LEFT JOIN payments p ON r.receipt_id = p.receipt_id
            LEFT JOIN items i ON li.item_id = i.item_id
            LEFT JOIN categories c ON i.category_id = c.category_id
            WHERE 1=1
            -- include refunds; we will handle sign in app layer
        """
        
        params = []
        
        if start_date:
            query += " AND DATE(r.created_at) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(r.created_at) <= ?"
            params.append(end_date)
        
        if store_id:
            query += " AND r.store_id = ?"
            params.append(store_id)
        
        query += " GROUP BY r.receipt_id, li.line_item_id"
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    
    def get_receipt_count(self):
        """Get total number of receipts in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM receipts")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_date_range(self):
        """Get the date range of receipts in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MIN(created_at), MAX(created_at) 
            FROM receipts 
            WHERE created_at IS NOT NULL
        """)
        result = cursor.fetchone()
        conn.close()
        return result
    
    # ===== SYNC METADATA =====
    
    def update_sync_time(self, key, value=None):
        """Update last sync time for a key"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_metadata (key, value, last_updated)
            VALUES (?, ?, ?)
        """, (key, value or "", datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_last_sync_time(self, key):
        """Get last sync time for a key"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT last_updated FROM sync_metadata WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    # ===== PAYMENT TYPES METHODS =====
    
    def save_payment_types(self, payment_types):
        """Save or update payment types in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for pt in payment_types:
            cursor.execute("""
                INSERT OR REPLACE INTO payment_types (
                    payment_type_id, name, type, last_updated
                ) VALUES (?, ?, ?, ?)
            """, (
                pt.get('id'),
                pt.get('name'),
                pt.get('type'),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        return len(payment_types)
    
    def get_payment_types_map(self):
        """Get payment type ID to name mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT payment_type_id, name FROM payment_types")
        
        payment_map = {}
        for row in cursor.fetchall():
            payment_id, name = row
            payment_map[payment_id] = name if name else "Unknown Payment"
        
        conn.close()
        return payment_map
    
    def get_payment_type_count(self):
        """Get total number of payment types"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM payment_types")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ===== STORES METHODS =====
    
    def save_stores(self, stores):
        """Save or update stores in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for store in stores:
            address = store.get('address', {})
            
            # Handle address as either string or dict
            if isinstance(address, str):
                address_line1 = address
                address_line2 = None
                city = None
                country = None
            elif isinstance(address, dict):
                address_line1 = address.get('line_1')
                address_line2 = address.get('line_2')
                city = address.get('city')
                country = address.get('country')
            else:
                address_line1 = None
                address_line2 = None
                city = None
                country = None
            
            cursor.execute("""
                INSERT OR REPLACE INTO stores (
                    store_id, name, address_line1, address_line2, city, 
                    country, phone, last_updated, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                store.get('id'),
                store.get('name'),
                address_line1,
                address_line2,
                city,
                country,
                store.get('phone'),
                datetime.now().isoformat(),
                json.dumps(store)
            ))
        
        conn.commit()
        conn.close()
        return len(stores)
    
    def get_stores_map(self):
        """Get store ID to name mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT store_id, name FROM stores")
        
        store_map = {}
        for row in cursor.fetchall():
            store_id, name = row
            store_map[store_id] = name if name else "Unknown Store"
        
        conn.close()
        return store_map
    
    def get_store_count(self):
        """Get total number of stores"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stores")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ===== EMPLOYEES METHODS =====
    
    def save_employees(self, employees):
        """Save or update employees in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for emp in employees:
            cursor.execute("""
                INSERT OR REPLACE INTO employees (
                    employee_id, name, email, phone, last_updated, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                emp.get('id'),
                emp.get('name'),
                emp.get('email'),
                emp.get('phone'),
                datetime.now().isoformat(),
                json.dumps(emp)
            ))
        
        conn.commit()
        conn.close()
        return len(employees)
    
    def get_employees_map(self):
        """Get employee ID to name mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT employee_id, name FROM employees")
        
        employee_map = {}
        for row in cursor.fetchall():
            emp_id, name = row
            employee_map[emp_id] = name if name else "Unknown Employee"
        
        conn.close()
        return employee_map
    
    def get_employee_count(self):
        """Get total number of employees"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM employees")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ===== CATEGORIES METHODS =====
    
    def save_categories(self, categories):
        """Save or update categories (locations) in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for cat in categories:
            cursor.execute("""
                INSERT OR REPLACE INTO categories (
                    category_id, name, color, last_updated
                ) VALUES (?, ?, ?, ?)
            """, (
                cat.get('id'),
                cat.get('name'),
                cat.get('color'),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        return len(categories)
    
    def get_categories_map(self):
        """Get category ID to name (location) mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT category_id, name FROM categories")
        
        category_map = {}
        for row in cursor.fetchall():
            cat_id, name = row
            category_map[cat_id] = name if name else "Uncategorized"
        
        conn.close()
        return category_map
    
    def get_category_count(self):
        """Get total number of categories"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM categories")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ===== ITEMS METHODS =====
    
    def save_items(self, items):
        """Save or update items in database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        for item in items:
            # Get first variant for basic info
            variants = item.get('variants', [])
            variant = variants[0] if variants else {}
            
            cursor.execute("""
                INSERT OR REPLACE INTO items (
                    item_id, variant_id, name, sku, category_id, 
                    price, cost, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get('id'),
                variant.get('variant_id'),
                item.get('item_name') or item.get('name'),
                variant.get('sku'),
                item.get('category_id'),
                variant.get('price'),
                variant.get('cost'),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        return len(items)
    
    # ===== MANUAL PRODUCT CATEGORIES METHODS =====
    
    def save_manual_categories(self, manual_categories):
        """Save manual product categories to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        current_time = datetime.now().isoformat()
        
        for product_name, category in manual_categories.items():
            cursor.execute("""
                INSERT OR REPLACE INTO manual_product_categories (
                    product_name, category, created_at, updated_at
                ) VALUES (?, ?, ?, ?)
            """, (
                product_name,
                category,
                current_time,  # created_at (will be updated if exists)
                current_time   # updated_at
            ))
        
        conn.commit()
        conn.close()
        return len(manual_categories)
    
    def get_manual_categories(self):
        """Get all manual product categories from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT product_name, category FROM manual_product_categories")
        
        manual_categories = {}
        for row in cursor.fetchall():
            product_name, category = row
            manual_categories[product_name] = category
        
        conn.close()
        return manual_categories
    
    def clear_manual_categories(self):
        """Clear all manual product categories"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM manual_product_categories")
        conn.commit()
        conn.close()
    
    def get_item_category_map(self):
        """Get item ID to category ID mapping"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item_id, category_id FROM items WHERE category_id IS NOT NULL")
        
        item_map = {}
        for row in cursor.fetchall():
            item_id, category_id = row
            item_map[item_id] = category_id
        
        conn.close()
        return item_map
    
    def get_item_location_map(self):
        """Get item ID to location name mapping (joins items -> categories)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.item_id, c.name 
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.category_id
            WHERE i.category_id IS NOT NULL
        """)
        
        item_location_map = {}
        for row in cursor.fetchall():
            item_id, location_name = row
            item_location_map[item_id] = location_name if location_name else "Uncategorized"
        
        conn.close()
        return item_location_map
    
    def get_item_count(self):
        """Get total number of items"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    # ===== UTILITY METHODS =====
    
    def get_database_stats(self):
        """Get database statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Customer count
        cursor.execute("SELECT COUNT(*) FROM customers")
        stats['customers'] = cursor.fetchone()[0]
        
        # Receipt count
        cursor.execute("SELECT COUNT(*) FROM receipts")
        stats['receipts'] = cursor.fetchone()[0]
        
        # Line item count
        cursor.execute("SELECT COUNT(*) FROM line_items")
        stats['line_items'] = cursor.fetchone()[0]
        
        # Payment types count
        cursor.execute("SELECT COUNT(*) FROM payment_types")
        stats['payment_types'] = cursor.fetchone()[0]
        
        # Stores count
        cursor.execute("SELECT COUNT(*) FROM stores")
        stats['stores'] = cursor.fetchone()[0]
        
        # Employees count
        cursor.execute("SELECT COUNT(*) FROM employees")
        stats['employees'] = cursor.fetchone()[0]
        
        # Categories count (locations!)
        cursor.execute("SELECT COUNT(*) FROM categories")
        stats['categories'] = cursor.fetchone()[0]
        
        # Items count
        cursor.execute("SELECT COUNT(*) FROM items")
        stats['items'] = cursor.fetchone()[0]
        
        # Date range
        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM receipts")
        date_range = cursor.fetchone()
        stats['date_range'] = date_range
        
        # Last sync times
        cursor.execute("SELECT key, last_updated FROM sync_metadata")
        stats['last_syncs'] = dict(cursor.fetchall())
        
        conn.close()
        return stats
    
    def clear_all_data(self):
        """Clear all data from database (keep structure)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM customers")
        cursor.execute("DELETE FROM receipts")
        cursor.execute("DELETE FROM line_items")
        cursor.execute("DELETE FROM payments")
        cursor.execute("DELETE FROM sync_metadata")
        
        conn.commit()
        conn.close()

