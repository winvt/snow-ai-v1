"""
Unified ReferenceData class for managing all lookup data (customers, stores, payment types, etc.)
Simplifies data access throughout the application
"""

class ReferenceData:
    """
    Central cache for all reference/lookup data
    Provides clean interface for mapping IDs to human-readable names
    """
    
    def __init__(self, db):
        """
        Initialize with database connection
        Loads all reference data maps on startup
        """
        self.db = db
        self._load_all_maps()
    
    def _load_all_maps(self):
        """Load all mapping dictionaries from database"""
        self.customers = self.db.get_customer_map()
        self.payment_types = self.db.get_payment_types_map()
        self.stores = self.db.get_stores_map()
        self.employees = self.db.get_employees_map()
    
    def refresh(self):
        """Reload all maps from database (call after sync)"""
        self._load_all_maps()
    
    # === Customer Methods ===
    
    def get_customer_name(self, customer_id):
        """Get customer name by ID, returns 'Unknown Customer' if not found"""
        if not customer_id or customer_id == 'nan' or customer_id == 'None':
            return "Walk-in Customer"
        return self.customers.get(str(customer_id), "Unknown Customer")
    
    def has_customers(self):
        """Check if any customers are loaded"""
        return len(self.customers) > 0
    
    # === Payment Type Methods ===
    
    def get_payment_name(self, payment_id):
        """Get payment type name by ID"""
        if not payment_id or payment_id == 'nan':
            return "Unknown Payment"
        return self.payment_types.get(str(payment_id), "Unknown Payment")
    
    def get_payment_names(self, payment_ids_string):
        """
        Get payment names from comma/plus separated string of IDs
        Example: "id1+id2" -> "Cash+Card"
        """
        if not payment_ids_string or pd.isna(payment_ids_string):
            return "Unknown"
        
        ids = str(payment_ids_string).split('+')
        names = [self.get_payment_name(pid.strip()) for pid in ids if pid.strip()]
        return '+'.join(names) if names else "Unknown"
    
    def has_payment_types(self):
        """Check if any payment types are loaded"""
        return len(self.payment_types) > 0
    
    # === Store Methods ===
    
    def get_store_name(self, store_id):
        """Get store name by ID"""
        if not store_id or store_id == 'nan':
            return "Unknown Store"
        return self.stores.get(str(store_id), "Unknown Store")
    
    def has_stores(self):
        """Check if any stores are loaded"""
        return len(self.stores) > 0
    
    # === Employee Methods ===
    
    def get_employee_name(self, employee_id):
        """Get employee name by ID"""
        if not employee_id or employee_id == 'nan':
            return "Unknown Employee"
        return self.employees.get(str(employee_id), "Unknown Employee")
    
    def has_employees(self):
        """Check if any employees are loaded"""
        return len(self.employees) > 0
    
    # === Batch Operations ===
    
    def enrich_dataframe(self, df):
        """
        Add human-readable name columns to a DataFrame
        
        Args:
            df: DataFrame with ID columns (customer_id, store_id, etc.)
        
        Returns:
            DataFrame with additional name columns
        """
        import pandas as pd
        
        df = df.copy()
        
        # Add customer names
        if 'customer_id' in df.columns and self.has_customers():
            df['customer_name'] = df['customer_id'].astype(str).map(
                lambda x: self.get_customer_name(x)
            )
        
        # Add payment names
        if 'bill_type' in df.columns and self.has_payment_types():
            df['payment_name'] = df['bill_type'].apply(
                lambda x: self.get_payment_names(x)
            )
        
        # Add store names
        if 'store_id' in df.columns and self.has_stores():
            df['store_name'] = df['store_id'].astype(str).map(
                lambda x: self.get_store_name(x)
            )
        
        # Add employee names
        if 'employee_id' in df.columns and self.has_employees():
            df['employee_name'] = df['employee_id'].astype(str).map(
                lambda x: self.get_employee_name(x)
            )
        
        return df
    
    # === Status Methods ===
    
    def get_status_summary(self):
        """Get summary of loaded reference data"""
        return {
            'customers': len(self.customers),
            'payment_types': len(self.payment_types),
            'stores': len(self.stores),
            'employees': len(self.employees),
            'total': len(self.customers) + len(self.payment_types) + len(self.stores) + len(self.employees)
        }
    
    def is_fully_loaded(self):
        """Check if all reference data is loaded"""
        return (self.has_customers() and 
                self.has_payment_types() and 
                self.has_stores())
    
    def get_missing_data_types(self):
        """Get list of missing reference data types"""
        missing = []
        if not self.has_customers():
            missing.append("Customers")
        if not self.has_payment_types():
            missing.append("Payment Types")
        if not self.has_stores():
            missing.append("Stores")
        if not self.has_employees():
            missing.append("Employees")
        return missing


# Import pandas for type hints
import pandas as pd

