import requests
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.io as pio
import os
import re
from datetime import datetime, timedelta
import pytz
from database import LoyverseDB
from utils.reference_data import ReferenceData
from utils import charts

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# ===== TRANSLATION DICTIONARIES =====
TRANSLATIONS = {
    "English": {
        "load_database": "Load Database",
        "loaded_success": "Loaded {total_receipts} receipts, {line_items} line items",
        "no_cached_data": "No cached data. Use Settings to sync data first.",
        "navigation": "Navigation",
        "daily_sales": "Daily Sales",
        "by_location": "By Location", 
        "by_product": "By Product",
        "by_customer": "By Customer",
        "credit": "Credit",
        "interactive_data": "Interactive Data",
        "transaction_log": "Transaction Log",
        "customer_invoice": "Customer Invoice",
        "ice_forecast": "Ice Forecast",
        "crm": "CRM",
        "settings_preferences": "Settings",
        "date_range_selector": "Date Range",
        "quick_shortcuts": "Quick Shortcuts",
        "today": "Today",
        "yesterday": "Yesterday",
        "last_3_days": "Last 3 Days",
        "last_week": "Last Week",
        "last_2_weeks": "Last 2 Weeks",
        "last_30_days": "Last 30 Days",
        "this_week": "This Week",
        "this_month": "This Month",
        "last_month": "Last Month",
        "last_3_months": "Last 3 Months",
        "this_year": "This Year",
        "all_data": "All Data",
        "start_date": "Start Date",
        "end_date": "End Date",
        "apply_range": "Apply",
        "current_selection": "{start_date} to {end_date} ({days} days)",
        "api_information": "API Information",
        "viewing_data_from": "Viewing data from",
        "daily_sales_analysis": "Daily Sales Analysis",
        "sales_by_location": "Sales by Location",
        "product_analysis": "Product Analysis",
        "customer_analysis": "Customer Analysis",
        "credit_management": "Credit Management",
        "interactive_data_explorer": "Interactive Data Explorer",
        "transaction_log": "Transaction Log",
        "customer_invoice_generator": "Customer Invoice Generator",
        "ice_forecast_dashboard": "Ice Forecast",
        "crm_dashboard": "Customer Relationship Management",
        
        # Password Authentication
        "login_required": "Snow AI Dashboard",
        "enter_password": "Enter password to access dashboard",
        "password_placeholder": "Enter password...",
        "login_button": "Sign In",
        "clear_button": "Clear",
        "incorrect_password": "Incorrect password. Please try again.",
        "contact_admin": "Contact administrator for access information",
        "logout": "Sign Out",
        
        # Settings & Preferences
        "appearance": "Appearance",
        "theme_mode": "Theme Mode",
        "light": "Light",
        "dark": "Dark",
        "font_size": "Font Size",
        "small": "Small",
        "medium": "Medium",
        "large": "Large",
        "compact_mode": "Compact Mode",
        "data_management": "Data Management",
        "sync_receipts": "Sync Receipts from API",
        "sync_missing_data": "Sync Missing Data",
        "sync_all_metadata": "Sync All Metadata",
        "extended_sync_options": "Extended Sync Options",
        "custom_date_range_sync": "Custom Date Range Sync",
        "display_preferences": "Display Preferences",
        "data_backup": "Data Backup",
        "api_connection": "API & Connection",
        "sync_data_operations": "Data Sync & Operations",
        "advanced_options": "Advanced Options",
        "maintenance": "Maintenance",
        
        # Key Metrics
        "key_metrics": "Key Metrics",
        "total_sales": "Total Sales",
        "total_items": "Total Items",
        "unique_customers": "Unique Customers",
        "avg_transaction_value": "Avg Transaction Value",
        "sales_growth": "Sales Growth",
        "sales_overview": "Sales Overview",
        "daily_discounts": "Daily Discounts",
        "day_of_week_analysis": "Day of Week Analysis",
        "time_period_analysis": "Time Period Analysis",
        
        # Product Analysis
        "product_category_summary": "Product Category Summary",
        "sales_distribution": "Sales Distribution",
        "category_summary_table": "Category Summary Table",
        "sales_by_category": "Sales by Category",
        "all_products_by_category": "All Products by Category",
        "edit_product_categories": "Edit Product Categories",
        "select_product_to_edit": "Select product to edit:",
        "change_category_to": "Change category to:",
        "current_product_breakdown": "Current Product Breakdown",
        
        # Common terms
        "date": "Date",
        "sales": "Sales",
        "quantity": "Quantity",
        "amount": "Amount",
        "total": "Total",
        "average": "Average",
        "growth": "Growth",
        "transactions": "Transactions",
        "customers": "Customers",
        "products": "Products",
        "locations": "Locations",
        "categories": "Categories",
        "discounts": "Discounts",
        "refunds": "Refunds",
        "net_sales": "Net Sales",
        "gross_sales": "Gross Sales",
        "items_sold": "Items Sold",
        "active_days": "Active Days",
        "first_visit": "First Visit",
        "last_visit": "Last Visit",
        "total_spent": "Total Spent",
        "avg_per_transaction": "Avg per Transaction",
        "avg_items_per_transaction": "Avg Items per Transaction",
        "peak_hours": "Peak Hours",
        "slowest_hours": "Slowest Hours",
        "forecast": "Forecast",
        "trend": "Trend",
        "analysis": "Analysis",
        "summary": "Summary",
        "details": "Details",
        "overview": "Overview",
        "breakdown": "Breakdown",
        "distribution": "Distribution",
        "comparison": "Comparison",
        "performance": "Performance",
        "insights": "Insights",
        "recommendations": "Recommendations",
        
        # KPI Metrics
        "avg_daily_sales": "Avg Daily Sales",
        "avg_transaction": "Avg Transaction",
        "avg_items_per_day": "Avg Items / Day",
        "avg_customers_per_day": "Avg Customers / Day",
        "total_sales_period": "Total Sales (Period)",
        "total_items_period": "Total Items (Period)",
        "unique_customers_period": "Unique Customers (Period)",
        "total_transactions_period": "Total Transactions (Period)",
        "sales_growth_period": "Sales Growth",
        "transaction_growth_period": "Transaction Growth",
        "customer_growth_period": "Customer Growth",
        "item_growth_period": "Item Growth",
        "settings_sync_caption": "Sync settings are prioritized for daily operations and reconciliation.",
        "settings_sync_header": "Sync Settings",
        "settings_sync_last_date": "Sync from last date",
        "settings_sync_last_date_help": "Intelligently sync from the latest stored transaction up to now.",
        "settings_sync_metadata": "Sync metadata",
        "settings_sync_metadata_help": "Fetch customers, payment types, stores, employees, categories, and items.",
        "settings_sync_metadata_running": "Syncing metadata...",
        "settings_sync_metadata_done": "Metadata sync complete: {total} records updated.",
        "settings_custom_range": "Custom range",
        "settings_theme_locked_light": "Theme is locked to Light on this deployment.",
        "settings_store_filter": "Store ID filter (optional)",
        "settings_store_filter_help": "Leave empty to sync all stores.",
        "settings_sync_preview_caption": "Will sync {days} day(s): {start_date} -> {end_date}",
        "settings_sync_custom_range": "Sync custom range",
        "settings_invalid_date_range": "Start date must be before or equal to end date.",
        "settings_sync_results": "Sync Results & Debug",
        "settings_sync_results_empty": "No sync run yet in this session.",
        "settings_last_mode": "Sync mode",
        "settings_last_range": "Date range",
        "settings_fetched_count": "Fetched",
        "settings_saved_count": "Saved",
        "settings_duplicates": "Duplicate skips",
        "settings_collisions": "Collision signals",
        "settings_new_transactions": "New transactions",
        "settings_debug_console": "Debug console",
        "settings_imported_snapshot": "Imported Data Snapshot",
        "settings_db_receipts": "Receipts",
        "settings_db_line_items": "Line items",
        "settings_db_range": "Data range",
        "settings_recent_imports": "Recent imported receipts",
        "settings_no_receipts_preview": "No receipts found in database yet.",
        "settings_basic_preferences": "Basic Preferences",
        "settings_language": "Language"
    },
    "Thai": {
        "load_database": "โหลดฐานข้อมูล",
        "loaded_success": "โหลดเสร็จสิ้น {total_receipts} ใบเสร็จ, {line_items} รายการ",
        "no_cached_data": "ไม่มีข้อมูลแคช ใช้การตั้งค่าเพื่อซิงค์ข้อมูลก่อน",
        "navigation": "เมนูนำทาง",
        "daily_sales": "ยอดขายรายวัน",
        "by_location": "แยกตามสถานที่", 
        "by_product": "แยกตามสินค้า",
        "by_customer": "แยกตามลูกค้า",
        "credit": "เครดิต",
        "interactive_data": "ข้อมูลแบบโต้ตอบ",
        "transaction_log": "บันทึกการทำรายการ",
        "customer_invoice": "ใบแจ้งหนี้ลูกค้า",
        "ice_forecast": "พยากรณ์น้ำแข็ง",
        "crm": "CRM",
        "settings_preferences": "การตั้งค่า",
        "date_range_selector": "ช่วงวันที่",
        "quick_shortcuts": "ทางลัด",
        "today": "วันนี้",
        "yesterday": "เมื่อวาน",
        "last_3_days": "3 วันที่ผ่านมา",
        "last_week": "สัปดาห์ที่แล้ว",
        "last_2_weeks": "2 สัปดาห์ที่แล้ว",
        "last_30_days": "30 วันที่ผ่านมา",
        "this_week": "สัปดาห์นี้",
        "this_month": "เดือนนี้",
        "last_month": "เดือนที่แล้ว",
        "last_3_months": "3 เดือนที่ผ่านมา",
        "this_year": "ปีนี้",
        "all_data": "ข้อมูลทั้งหมด",
        "start_date": "วันที่เริ่มต้น",
        "end_date": "วันที่สิ้นสุด",
        "apply_range": "ใช้งาน",
        "current_selection": "{start_date} ถึง {end_date} ({days} วัน)",
        "api_information": "ข้อมูล API",
        "viewing_data_from": "กำลังดูข้อมูลจาก",
        "daily_sales_analysis": "การวิเคราะห์ยอดขายรายวัน",
        "sales_by_location": "ยอดขายแยกตามสถานที่",
        "product_analysis": "การวิเคราะห์สินค้า",
        "customer_analysis": "การวิเคราะห์ลูกค้า",
        "credit_management": "การจัดการเครดิต",
        "interactive_data_explorer": "เครื่องมือสำรวจข้อมูลแบบโต้ตอบ",
        "transaction_log": "บันทึกการทำรายการ",
        "customer_invoice_generator": "เครื่องมือสร้างใบแจ้งหนี้ลูกค้า",
        "ice_forecast_dashboard": "พยากรณ์น้ำแข็ง",
        "crm_dashboard": "การจัดการความสัมพันธ์ลูกค้า",
        
        # Password Authentication
        "login_required": "Snow AI Dashboard",
        "enter_password": "กรอกรหัสผ่านเพื่อเข้าถึงแดชบอร์ด",
        "password_placeholder": "กรอกรหัสผ่าน...",
        "login_button": "เข้าสู่ระบบ",
        "clear_button": "ล้าง",
        "incorrect_password": "รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่",
        "contact_admin": "ติดต่อผู้ดูแลระบบเพื่อขอข้อมูลการเข้าถึง",
        "logout": "ออกจากระบบ",
        
        # Settings & Preferences
        "appearance": "การแสดงผล",
        "theme_mode": "โหมดธีม",
        "light": "สว่าง",
        "dark": "มืด",
        "font_size": "ขนาดตัวอักษร",
        "small": "เล็ก",
        "medium": "กลาง",
        "large": "ใหญ่",
        "compact_mode": "โหมดกะทัดรัด",
        "data_management": "การจัดการข้อมูล",
        "sync_receipts": "ซิงค์ใบเสร็จจาก API",
        "sync_missing_data": "ซิงค์ข้อมูลที่ขาดหาย",
        "sync_all_metadata": "ซิงค์ข้อมูลทั้งหมด",
        "extended_sync_options": "ตัวเลือกการซิงค์แบบขยาย",
        "custom_date_range_sync": "ช่วงวันที่กำหนดเองสำหรับการซิงค์",
        "display_preferences": "การตั้งค่าการแสดงผล",
        "data_backup": "การสำรองข้อมูล",
        "api_connection": "API และการเชื่อมต่อ",
        "sync_data_operations": "การซิงค์และการดำเนินการข้อมูล",
        "advanced_options": "ตัวเลือกขั้นสูง",
        "maintenance": "การบำรุงรักษา",
        
        # Key Metrics
        "key_metrics": "ตัวชี้วัดหลัก",
        "total_sales": "ยอดขายรวม",
        "total_items": "รายการรวม",
        "unique_customers": "ลูกค้าไม่ซ้ำ",
        "avg_transaction_value": "มูลค่าเฉลี่ยต่อรายการ",
        "sales_growth": "การเติบโตของยอดขาย",
        "sales_overview": "ภาพรวมยอดขาย",
        "daily_discounts": "ส่วนลดรายวัน",
        "day_of_week_analysis": "การวิเคราะห์ตามวันในสัปดาห์",
        "time_period_analysis": "การวิเคราะห์ช่วงเวลา",
        
        # Product Analysis
        "product_category_summary": "สรุปหมวดหมู่สินค้า",
        "sales_distribution": "การกระจายยอดขาย",
        "category_summary_table": "ตารางสรุปหมวดหมู่",
        "sales_by_category": "ยอดขายแยกตามหมวดหมู่",
        "all_products_by_category": "สินค้าทั้งหมดแยกตามหมวดหมู่",
        "edit_product_categories": "แก้ไขหมวดหมู่สินค้า",
        "select_product_to_edit": "เลือกสินค้าที่จะแก้ไข:",
        "change_category_to": "เปลี่ยนหมวดหมู่เป็น:",
        "current_product_breakdown": "การแบ่งสินค้าปัจจุบัน",
        
        # Common terms
        "date": "วันที่",
        "sales": "ยอดขาย",
        "quantity": "จำนวน",
        "amount": "จำนวนเงิน",
        "total": "รวม",
        "average": "เฉลี่ย",
        "growth": "การเติบโต",
        "transactions": "รายการ",
        "customers": "ลูกค้า",
        "products": "สินค้า",
        "locations": "สถานที่",
        "categories": "หมวดหมู่",
        "discounts": "ส่วนลด",
        "refunds": "การคืนเงิน",
        "net_sales": "ยอดขายสุทธิ",
        "gross_sales": "ยอดขายรวม",
        "items_sold": "รายการที่ขาย",
        "active_days": "วันที่ใช้งาน",
        "first_visit": "เยี่ยมครั้งแรก",
        "last_visit": "เยี่ยมครั้งล่าสุด",
        "total_spent": "ใช้จ่ายรวม",
        "avg_per_transaction": "เฉลี่ยต่อรายการ",
        "avg_items_per_transaction": "เฉลี่ยรายการต่อรายการ",
        "peak_hours": "ชั่วโมงเร่งด่วน",
        "slowest_hours": "ชั่วโมงที่ช้าที่สุด",
        "forecast": "พยากรณ์",
        "trend": "แนวโน้ม",
        "analysis": "การวิเคราะห์",
        "summary": "สรุป",
        "details": "รายละเอียด",
        "overview": "ภาพรวม",
        "breakdown": "การแบ่ง",
        "distribution": "การกระจาย",
        "comparison": "การเปรียบเทียบ",
        "performance": "ประสิทธิภาพ",
        "insights": "ข้อมูลเชิงลึก",
        "recommendations": "คำแนะนำ",
        
        # KPI Metrics
        "avg_daily_sales": "ยอดขายเฉลี่ยต่อวัน",
        "avg_transaction": "รายการเฉลี่ย",
        "avg_items_per_day": "รายการเฉลี่ยต่อวัน",
        "avg_customers_per_day": "ลูกค้าเฉลี่ยต่อวัน",
        "total_sales_period": "ยอดขายรวมในระยะเวลา",
        "total_items_period": "รายการรวมในระยะเวลา",
        "unique_customers_period": "ลูกค้าไม่ซ้ำในระยะเวลา",
        "total_transactions_period": "รายการรวมในระยะเวลา",
        "sales_growth_period": "การเติบโตของยอดขาย",
        "transaction_growth_period": "การเติบโตของรายการ",
        "customer_growth_period": "การเติบโตของลูกค้า",
        "item_growth_period": "การเติบโตของรายการ",
        "settings_sync_caption": "ให้ความสำคัญกับการตั้งค่าซิงค์สำหรับการใช้งานประจำวันและการกระทบยอด",
        "settings_sync_header": "การตั้งค่าการซิงค์",
        "settings_sync_last_date": "ซิงค์จากวันที่ล่าสุด",
        "settings_sync_last_date_help": "ซิงค์อย่างชาญฉลาดจากรายการล่าสุดที่จัดเก็บไว้จนถึงปัจจุบัน",
        "settings_sync_metadata": "ซิงค์เมทาดาทา",
        "settings_sync_metadata_help": "ดึงข้อมูลลูกค้า ประเภทการชำระเงิน สาขา พนักงาน หมวดหมู่ และสินค้า",
        "settings_sync_metadata_running": "กำลังซิงค์เมทาดาทา...",
        "settings_sync_metadata_done": "ซิงค์เมทาดาทาเสร็จสิ้น: อัปเดต {total} รายการ",
        "settings_custom_range": "ช่วงวันที่กำหนดเอง",
        "settings_theme_locked_light": "ธีมถูกล็อกเป็นโหมดสว่างสำหรับดีพลอยนี้",
        "settings_store_filter": "กรองด้วย Store ID (ไม่บังคับ)",
        "settings_store_filter_help": "เว้นว่างไว้เพื่อซิงค์ทุกสาขา",
        "settings_sync_preview_caption": "จะซิงค์ {days} วัน: {start_date} -> {end_date}",
        "settings_sync_custom_range": "ซิงค์ช่วงวันที่กำหนดเอง",
        "settings_invalid_date_range": "วันที่เริ่มต้นต้องน้อยกว่าหรือเท่ากับวันที่สิ้นสุด",
        "settings_sync_results": "ผลการซิงค์และดีบัก",
        "settings_sync_results_empty": "ยังไม่มีการซิงค์ในเซสชันนี้",
        "settings_last_mode": "โหมดการซิงค์",
        "settings_last_range": "ช่วงวันที่",
        "settings_fetched_count": "ที่ดึงมา",
        "settings_saved_count": "ที่บันทึก",
        "settings_duplicates": "รายการซ้ำที่ข้าม",
        "settings_collisions": "สัญญาณชนกัน",
        "settings_new_transactions": "ธุรกรรมใหม่",
        "settings_debug_console": "คอนโซลดีบัก",
        "settings_imported_snapshot": "สรุปข้อมูลที่นำเข้า",
        "settings_db_receipts": "ใบเสร็จ",
        "settings_db_line_items": "รายการบรรทัด",
        "settings_db_range": "ช่วงข้อมูล",
        "settings_recent_imports": "ใบเสร็จที่นำเข้าล่าสุด",
        "settings_no_receipts_preview": "ยังไม่พบใบเสร็จในฐานข้อมูล",
        "settings_basic_preferences": "การตั้งค่าพื้นฐาน",
        "settings_language": "ภาษา"
    }
}

# ===== FUNCTION DEFINITIONS (Must be before use) =====

def get_text(key, **kwargs):
    """Get translated text for the current language"""
    lang = st.session_state.get('language', 'English')
    template = TRANSLATIONS[lang].get(key, TRANSLATIONS['English'].get(key, key))
    return template.format(**kwargs) if kwargs else template


# Section/layout headings that were previously hardcoded in English.
HEADING_TRANSLATIONS = {
    "English": {
        "reference_data": "Reference Data",
        "individual_syncs": "Individual Syncs",
        "receipt_data_management": "Receipt Data Management",
        "query_settings": "Query Settings",
        "location_performance_details": "Location Performance Details",
        "location_trends_over_time": "Location Trends Over Time",
        "peak_hours_by_location": "Peak Hours Analysis by Location",
        "customer_details": "Customer Details",
        "customer_segments": "Customer Segments",
        "outstanding_by_customer": "### Outstanding Balance by Customer",
        "credit_sales_by_location": "### Credit Sales by Location",
        "credit_vs_cash_trend": "### Credit vs Cash Sales Trend",
        "cash_vs_credit_overview": "### Cash vs Credit Overview",
        "export_credit_reports": "### Export Credit Reports",
        "quantity_vs_total_sales": "Quantity vs Total Sales",
        "manual_checklist_upload_reconcile": "### Manual Checklist Upload & Reconciliation",
        "reconciliation_analysis": "### Reconciliation Analysis",
        "discrepancies_found": "#### Discrepancies Found",
        "select_customer": "### Select Customer",
        "select_invoice_period": "### Select Invoice Period",
        "invoice_title": "## INVOICE",
        "itemized_transactions": "### Itemized Transactions",
        "summary_by_product": "### Summary by Product",
        "payment_methods_used": "### Payment Methods Used",
        "download_invoice": "### Download Invoice",
        "print_view": "## PRINT VIEW",
        "ice_forecast_by_location": "### Ice Forecast by Location",
        "detailed_analysis_by_location": "### Detailed Analysis by Location",
        "current_forecast_metrics": "#### Current Forecast Metrics",
        "loading_recommendations": "#### Loading Recommendations",
        "calculation_method": "#### Calculation Method",
        "top_customers": "### Top Customers",
        "customer_alerts": "### Customer Alerts",
        "customer_management": "### Customer Management",
        "recent_transaction_history": "**Recent Transaction History**",
        "data_import_reconciliation": "Data Import & Reconciliation",
        "import_range": "### 1) Import Range",
        "pos_csv_input": "### 2) POS CSV Input",
        "daily_reconciliation": "### 3) Daily Reconciliation",
        "delta_diagnostics": "### 4) Delta Diagnostics",
        "by_receipt_type_db": "**By Receipt Type (DB)**",
        "by_store_db": "**By Store (DB)**",
        "by_payment_db": "**By Payment (DB)**",
        "candidate_exclusion_set": "### 5) Candidate Exclusion Set (Heuristic)",
        "exclusion_simulator": "### 6) Exclusion Simulator",
        "db_daily_totals_without_csv": "DB daily totals (without CSV):",
        "import_manual_categories": "#### Import Manual Categories",
    },
    "Thai": {
        "reference_data": "ข้อมูลอ้างอิง",
        "individual_syncs": "ซิงค์รายส่วน",
        "receipt_data_management": "การจัดการข้อมูลใบเสร็จ",
        "query_settings": "การตั้งค่าการค้นหา",
        "location_performance_details": "รายละเอียดประสิทธิภาพตามสถานที่",
        "location_trends_over_time": "แนวโน้มตามสถานที่ตามเวลา",
        "peak_hours_by_location": "วิเคราะห์ชั่วโมงเร่งด่วนแยกตามสถานที่",
        "customer_details": "รายละเอียดลูกค้า",
        "customer_segments": "กลุ่มลูกค้า",
        "outstanding_by_customer": "### ยอดค้างชำระแยกตามลูกค้า",
        "credit_sales_by_location": "### ยอดขายเครดิตแยกตามสถานที่",
        "credit_vs_cash_trend": "### แนวโน้มยอดขายเครดิตเทียบเงินสด",
        "cash_vs_credit_overview": "### ภาพรวมเงินสดเทียบเครดิต",
        "export_credit_reports": "### ส่งออกรายงานเครดิต",
        "quantity_vs_total_sales": "ปริมาณเทียบยอดขายรวม",
        "manual_checklist_upload_reconcile": "### อัปโหลดเช็กลิสต์เพื่อตรวจสอบ",
        "reconciliation_analysis": "### การวิเคราะห์การกระทบยอด",
        "discrepancies_found": "#### พบความคลาดเคลื่อน",
        "select_customer": "### เลือกลูกค้า",
        "select_invoice_period": "### เลือกช่วงเวลาใบแจ้งหนี้",
        "invoice_title": "## ใบแจ้งหนี้",
        "itemized_transactions": "### รายการธุรกรรมแบบแยกรายการ",
        "summary_by_product": "### สรุปแยกตามสินค้า",
        "payment_methods_used": "### วิธีการชำระเงินที่ใช้",
        "download_invoice": "### ดาวน์โหลดใบแจ้งหนี้",
        "print_view": "## มุมมองสำหรับพิมพ์",
        "ice_forecast_by_location": "### พยากรณ์น้ำแข็งแยกตามสถานที่",
        "detailed_analysis_by_location": "### วิเคราะห์เชิงลึกแยกตามสถานที่",
        "current_forecast_metrics": "#### ตัวชี้วัดพยากรณ์ปัจจุบัน",
        "loading_recommendations": "#### คำแนะนำการโหลดสินค้า",
        "calculation_method": "#### วิธีการคำนวณ",
        "top_customers": "### ลูกค้าอันดับต้น",
        "customer_alerts": "### การแจ้งเตือนลูกค้า",
        "customer_management": "### การจัดการลูกค้า",
        "recent_transaction_history": "**ประวัติธุรกรรมล่าสุด**",
        "data_import_reconciliation": "นำเข้าข้อมูลและกระทบยอด",
        "import_range": "### 1) ช่วงวันที่นำเข้า",
        "pos_csv_input": "### 2) ข้อมูลนำเข้า CSV จาก POS",
        "daily_reconciliation": "### 3) การกระทบยอดรายวัน",
        "delta_diagnostics": "### 4) วิเคราะห์ผลต่าง",
        "by_receipt_type_db": "**แยกตามประเภทใบเสร็จ (DB)**",
        "by_store_db": "**แยกตามสาขา (DB)**",
        "by_payment_db": "**แยกตามการชำระเงิน (DB)**",
        "candidate_exclusion_set": "### 5) ชุดรายการที่แนะนำให้ตัดออก (ฮิวริสติก)",
        "exclusion_simulator": "### 6) ตัวจำลองการตัดออก",
        "db_daily_totals_without_csv": "ยอดรวมรายวันจาก DB (ไม่มี CSV):",
        "import_manual_categories": "#### นำเข้าหมวดหมู่แบบกำหนดเอง",
    },
}


def get_heading(key):
    """Get localized UI heading text."""
    lang = st.session_state.get("language", "English")
    return HEADING_TRANSLATIONS.get(lang, {}).get(
        key,
        HEADING_TRANSLATIONS["English"].get(key, key),
    )

# ========= CONFIG =========
LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN", "d18826e6c76345888204b310aaca1351")
BASE_URL = "https://api.loyverse.com/v1.0/receipts"
PAGE_LIMIT = 250
FORCE_LIGHT_THEME = os.getenv("STREAMLIT_THEME_BASE", "").lower() == "light"

THEME_LIGHT = "Light"
THEME_DARK = "Dark"

THEME_STYLE_TOKENS = {
    THEME_LIGHT: {
        "css_vars": {
            "bg-app": "#f8fafc",
            "bg-surface": "#ffffff",
            "bg-surface-raised": "#ffffff",
            "border-default": "#e2e8f0",
            "border-subtle": "#f1f5f9",
            "text-primary": "#0f172a",
            "text-secondary": "#475569",
            "text-muted": "#94a3b8",
            "text-faint": "#cbd5e1",
            "accent": "#3b82f6",
            "accent-hover": "#2563eb",
            "accent-subtle": "rgba(59,130,246,0.08)",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "metric-bg": "#ffffff",
        },
        "plotly": {
            "template": "plotly_white",
            "font_color": "#475569",
            "title_color": "#0f172a",
            "grid_color": "#f1f5f9",
            "line_color": "#e2e8f0",
            "tick_color": "#64748b",
            "hover_bg": "#0f172a",
            "hover_font": "#f1f5f9",
        },
    },
    THEME_DARK: {
        "css_vars": {
            "bg-app": "#0b1220",
            "bg-surface": "#162033",
            "bg-surface-raised": "#243449",
            "border-default": "rgba(148,163,184,0.30)",
            "border-subtle": "rgba(148,163,184,0.18)",
            "text-primary": "#f8fafc",
            "text-secondary": "#d1d9e6",
            "text-muted": "#a5b4c9",
            "text-faint": "#8798b0",
            "accent": "#7cb8ff",
            "accent-hover": "#5fa5ff",
            "accent-subtle": "rgba(124,184,255,0.20)",
            "success": "#34d399",
            "warning": "#fbbf24",
            "error": "#f87171",
            "metric-bg": "#131e31",
        },
        "plotly": {
            "template": "plotly_dark",
            "font_color": "#c7d4e6",
            "title_color": "#f8fafc",
            "grid_color": "#30435f",
            "line_color": "#4e647f",
            "tick_color": "#b3c0d4",
            "hover_bg": "#162033",
            "hover_font": "#f1f5f9",
        },
    },
}


def resolve_theme_mode():
    """Single source of truth for active theme mode."""
    if FORCE_LIGHT_THEME:
        return THEME_LIGHT
    mode = st.session_state.get("theme_mode", THEME_LIGHT)
    return mode if mode in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT


def apply_theme_mode(mode):
    """Centralized theme mutation logic."""
    st.session_state.theme_mode = THEME_LIGHT if FORCE_LIGHT_THEME else mode


def get_theme_styles():
    return THEME_STYLE_TOKENS[resolve_theme_mode()]
# ==========================

st.set_page_config(page_title="Snow AI Dashboard", layout="wide")

# ========= PASSWORD AUTHENTICATION =========
PASSWORD = "snowbomb"

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Password authentication
if not st.session_state.authenticated:
    # Inject login-specific styling
    st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] { background: #f8fafc; }
        .login-container {
            max-width: 380px;
            margin: 80px auto 0 auto;
            padding: 40px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        .login-brand {
            text-align: center;
            margin-bottom: 32px;
        }
        .login-brand h1 {
            font-size: 24px;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #0f172a;
            margin: 0 0 4px 0;
        }
        .login-brand p {
            font-size: 13px;
            color: #64748b;
            margin: 0;
        }
    </style>
    """, unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1.2, 1.6, 1.2])
    
    with col2:
        st.markdown("""
        <div class="login-brand">
            <h1>Snow AI</h1>
            <p>Enter your password to continue</p>
        </div>
        """, unsafe_allow_html=True)
        password_input = st.text_input("Password", type="password", placeholder=get_text("password_placeholder"), label_visibility="collapsed")
        
        if st.button(get_text("login_button"), type="primary", use_container_width=True):
            if password_input == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error(get_text("incorrect_password"))
        
        st.caption(get_text("contact_admin"))
    
    # Stop execution here if not authenticated
    st.stop()

# ========= MAIN APP LOGIC =========
# Initialize session state for selected tab
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "Daily Sales"  # Will be updated after language is set

# Initialize theme
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = THEME_LIGHT
apply_theme_mode(resolve_theme_mode())

# Initialize language
if 'language' not in st.session_state:
    st.session_state.language = "English"

# ========= DESIGN SYSTEM CSS =========
# Direction: Sophistication & Trust + Data & Analysis
# Foundation: Cool (slate), Accent: Blue, Depth: Borders-only, Radius: Sharp (4-8px)
def get_design_system_css():
    """Generate comprehensive design system CSS."""
    # Font size from user preference
    font_sizes = {
        "Small": "12px", "Medium": "14px", "Large": "16px",
        "เล็ก": "12px", "กลาง": "14px", "ใหญ่": "16px"
    }
    base_font = font_sizes.get(st.session_state.get('font_size', 'Medium'), "14px")
    compact = st.session_state.get('compact_mode', False)
    css_var_map = get_theme_styles()["css_vars"]
    css_vars = "\n".join([f"            --{k}: {v};" for k, v in css_var_map.items()])

    return f"""
    <style>
        :root {{
            {css_vars}
            --font-sans: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, sans-serif;
            --font-mono: "SF Mono", "Cascadia Code", "Fira Code", "JetBrains Mono", monospace;
            --radius-sm: 4px;
            --radius-md: 6px;
            --radius-lg: 8px;
            --shadow-subtle: 0 1px 2px rgba(0,0,0,0.04);
            --transition: 150ms cubic-bezier(0.25, 1, 0.5, 1);
        }}

        /* ---- Global ---- */
        html, body, [class*="css"] {{
            font-family: var(--font-sans);
            font-size: {base_font};
        }}
        .stApp {{
            background-color: var(--bg-app);
            color: var(--text-primary);
        }}
        .stApp [data-testid="stHeader"] {{
            background: transparent;
        }}

        /* ---- Main content area ---- */
        .block-container {{
            padding-top: {'1.5rem' if compact else '2rem'} !important;
            padding-bottom: {'1rem' if compact else '2rem'} !important;
            max-width: 1200px;
        }}
        {''.join(['''
        .element-container {
            margin-bottom: 0.4rem !important;
        }
        ''' if compact else ''])}

        /* ---- Typography ---- */
        h1 {{
            font-weight: 600 !important;
            letter-spacing: -0.02em !important;
            color: var(--text-primary) !important;
            font-size: 1.75rem !important;
        }}
        h2 {{
            font-weight: 600 !important;
            letter-spacing: -0.02em !important;
            color: var(--text-primary) !important;
            font-size: 1.35rem !important;
        }}
        h3 {{
            font-weight: 600 !important;
            letter-spacing: -0.01em !important;
            color: var(--text-primary) !important;
            font-size: 1.1rem !important;
        }}
        p, li, [data-testid="stMarkdownContainer"] span {{
            color: var(--text-secondary);
        }}

        /* ---- Sidebar ---- */
        [data-testid="stSidebar"] {{
            background-color: var(--bg-surface) !important;
            border-right: 1px solid var(--border-default) !important;
        }}
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color: var(--text-primary);
            font-size: 13px;
        }}
        [data-testid="stSidebar"] h1 {{
            font-size: 1.25rem !important;
            font-weight: 600 !important;
            letter-spacing: -0.02em !important;
        }}
        [data-testid="stSidebar"] h2 {{
            font-size: 1rem !important;
            font-weight: 500 !important;
            color: var(--text-muted) !important;
            text-transform: uppercase;
            letter-spacing: 0.04em !important;
            font-size: 11px !important;
        }}
        [data-testid="stSidebar"] hr {{
            border-color: var(--border-subtle) !important;
            margin: 12px 0 !important;
        }}

        /* ---- Buttons ---- */
        .stButton > button {{
            border-radius: var(--radius-md) !important;
            font-weight: 500 !important;
            font-size: 13px !important;
            padding: 6px 16px !important;
            border: 1px solid var(--border-default) !important;
            transition: all var(--transition) !important;
            letter-spacing: 0 !important;
        }}
        .stButton > button span {{
            color: inherit !important;
        }}
        .stButton > button[kind="primary"] {{
            background-color: var(--accent) !important;
            border-color: var(--accent) !important;
            color: #ffffff !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            background-color: var(--accent-hover) !important;
            border-color: var(--accent-hover) !important;
        }}
        .stButton > button[kind="secondary"] {{
            background-color: var(--bg-surface) !important;
            color: var(--text-primary) !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            background-color: var(--accent-subtle) !important;
            color: var(--accent) !important;
            border-color: var(--accent) !important;
        }}

        /* Sidebar nav buttons - tighter */
        [data-testid="stSidebar"] .stButton > button {{
            padding: 8px 12px !important;
            font-size: 13px !important;
            text-align: left !important;
            justify-content: flex-start !important;
        }}

        /* ---- Metric cards ---- */
        [data-testid="stMetric"] {{
            background: var(--metric-bg);
            border: 1px solid var(--border-default);
            border-radius: var(--radius-lg);
            padding: 16px !important;
            min-height: 116px;
            display: flex;
            align-items: center;
        }}
        [data-testid="stMetric"] > div {{
            width: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        [data-testid="stMetricLabel"] {{
            font-size: 12px !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        [data-testid="stMetricValue"] {{
            font-family: var(--font-mono) !important;
            font-weight: 600 !important;
            font-size: 1.5rem !important;
            color: var(--text-primary) !important;
            font-variant-numeric: tabular-nums;
        }}
        [data-testid="stMetricDelta"] {{
            font-family: var(--font-mono) !important;
            font-size: 12px !important;
            min-height: 20px;
        }}

        /* ---- Data tables ---- */
        [data-testid="stDataFrame"] {{
            border: 1px solid var(--border-default) !important;
            border-radius: var(--radius-lg) !important;
            overflow: hidden;
        }}
        [data-testid="stDataFrame"] td {{
            font-family: var(--font-mono);
            font-variant-numeric: tabular-nums;
            font-size: 13px;
        }}
        [data-testid="stDataFrame"] th {{
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
            text-transform: uppercase;
            font-size: 11px !important;
            letter-spacing: 0.04em;
        }}

        /* ---- Expanders ---- */
        [data-testid="stExpander"] {{
            border: 1px solid var(--border-default) !important;
            border-radius: var(--radius-lg) !important;
            background: var(--bg-surface);
        }}
        [data-testid="stExpander"] summary {{
            font-weight: 500;
            font-size: 14px;
            color: var(--text-primary);
        }}

        /* ---- Form inputs ---- */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stDateInput > div > div > input {{
            border-radius: var(--radius-md) !important;
            border-color: var(--border-default) !important;
            font-size: 13px !important;
            background-color: var(--bg-surface) !important;
            color: var(--text-primary) !important;
        }}
        .stTextInput > div > div > input:focus,
        .stDateInput > div > div > input:focus {{
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px var(--accent) !important;
        }}
        .stTextInput label, .stSelectbox label, .stDateInput label {{
            font-size: 12px !important;
            font-weight: 500 !important;
            color: var(--text-secondary) !important;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}

        /* ---- Alerts ---- */
        .stAlert {{
            border-radius: var(--radius-md) !important;
            font-size: 13px !important;
        }}

        /* ---- Horizontal rules ---- */
        hr {{
            border-color: var(--border-subtle) !important;
        }}

        /* ---- Plotly charts ---- */
        .js-plotly-plot {{
            border-radius: var(--radius-lg);
        }}

        /* ---- Tabs ---- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 0 !important;
            border-bottom: 1px solid var(--border-default);
        }}
        .stTabs [data-baseweb="tab"] {{
            font-size: 13px !important;
            font-weight: 500 !important;
            padding: 8px 16px !important;
        }}

        /* ---- Quick date selector buttons ---- */
        .date-shortcuts .stButton > button {{
            font-size: 12px !important;
            padding: 4px 8px !important;
            border-radius: var(--radius-sm) !important;
        }}

        /* ---- Download buttons ---- */
        .stDownloadButton > button {{
            border-radius: var(--radius-md) !important;
            font-size: 13px !important;
        }}

        /* ---- Captions ---- */
        .stCaption {{
            color: var(--text-muted) !important;
            font-size: 12px !important;
        }}

        /* ---- Progress bar ---- */
        .stProgress > div > div > div {{
            background-color: var(--accent) !important;
        }}

        /* ---- Selectbox/multiselect ---- */
        [data-baseweb="select"] {{
            border-radius: var(--radius-md) !important;
        }}
        [data-baseweb="select"] > div {{
            background-color: var(--bg-surface) !important;
            color: var(--text-primary) !important;
            border-color: var(--border-default) !important;
        }}
        [data-baseweb="select"] input {{
            color: var(--text-primary) !important;
        }}
        [data-baseweb="select"] svg {{
            color: var(--text-secondary) !important;
        }}
        .stDateInput [data-baseweb="input"] {{
            background-color: var(--bg-surface) !important;
            border-color: var(--border-default) !important;
        }}
        .stDateInput [data-baseweb="input"] input {{
            color: var(--text-primary) !important;
            -webkit-text-fill-color: var(--text-primary) !important;
        }}

        /* ---- Success/Info/Warning/Error boxes ---- */
        div[data-testid="stNotification"] {{
            border-radius: var(--radius-md) !important;
            font-size: 13px;
        }}
    </style>
    """

# Inject the design system
st.markdown(get_design_system_css(), unsafe_allow_html=True)

# Plotly chart theme - consistent with design system
plotly_style = get_theme_styles()["plotly"]
pio.templates.default = plotly_style["template"]
CHART_LAYOUT = dict(
    template=pio.templates.default,
    font=dict(
        family="-apple-system, BlinkMacSystemFont, Inter, Segoe UI, sans-serif",
        size=12,
        color=plotly_style["font_color"],
    ),
    title=dict(font=dict(size=14, color=plotly_style["title_color"]), x=0, xanchor="left"),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(
        gridcolor=plotly_style["grid_color"],
        linecolor=plotly_style["line_color"],
        tickfont=dict(size=11, color=plotly_style["tick_color"]),
    ),
    yaxis=dict(
        gridcolor=plotly_style["grid_color"],
        linecolor=plotly_style["line_color"],
        tickfont=dict(size=11, color=plotly_style["tick_color"]),
    ),
    margin=dict(l=48, r=16, t=40, b=40),
    colorway=["#3b82f6", "#64748b", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"],
    hoverlabel=dict(
        bgcolor=plotly_style["hover_bg"],
        font_size=12,
        font_color=plotly_style["hover_font"],
    ),
)


def apply_chart_layout(fig, **extra_layout):
    """Apply centralized chart theme, then optional chart-specific layout."""
    fig.update_layout(**CHART_LAYOUT)
    if extra_layout:
        fig.update_layout(**extra_layout)
    return fig

# ===== TRANSLATION DICTIONARIES =====

def initialize_selected_tab():
    """Initialize selected tab with proper translation"""
    if st.session_state.get('selected_tab') in ["📅 Daily Sales", "📅 ยอดขายรายวัน", "Daily Sales", "ยอดขายรายวัน"]:
        st.session_state.selected_tab = get_text("daily_sales")
    if st.session_state.get('selected_tab') in ["Settings", "การตั้งค่า"]:
        st.session_state.selected_tab = get_text("settings_preferences")

# ===== FUNCTION DEFINITIONS (Must be before use) =====

# --- Fetch customers from Loyverse API ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_customers(token):
    """Fetch all customers from Loyverse API"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = "https://api.loyverse.com/v1.0/customers"
    
    all_customers = []
    cursor = None
    limit = 250
    
    while True:
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            
        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code != 200:
                st.error(f"Error fetching customers: {res.status_code} - {res.text}")
                break
                
            data = res.json()
            customers = data.get("customers", [])
            all_customers.extend(customers)
            
            cursor = data.get("cursor")
            if not cursor:
                break
                
        except Exception as e:
            st.error(f"Exception fetching customers: {str(e)}")
            break
    
    return all_customers

# --- Fetch payment types ---
@st.cache_data(ttl=3600)  # Cache for 1 hour (payment types rarely change)
def fetch_all_payment_types(token):
    """Fetch all payment types from Loyverse API"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = "https://api.loyverse.com/v1.0/payment_types"
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            st.error(f"Error fetching payment types: {res.status_code}")
            return []
        
        data = res.json()
        return data.get("payment_types", [])
    except Exception as e:
        st.error(f"Exception fetching payment types: {str(e)}")
        return []

# --- Fetch stores ---
@st.cache_data(ttl=3600)  # Cache for 1 hour (stores rarely change)
def fetch_all_stores(token):
    """Fetch all stores from Loyverse API"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = "https://api.loyverse.com/v1.0/stores"
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            st.error(f"Error fetching stores: {res.status_code}")
            return []
        
        data = res.json()
        return data.get("stores", [])
    except Exception as e:
        st.error(f"Exception fetching stores: {str(e)}")
        return []

# --- Fetch employees ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_employees(token):
    """Fetch all employees from Loyverse API"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = "https://api.loyverse.com/v1.0/employees"
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            st.error(f"Error fetching employees: {res.status_code}")
            return []
        
        data = res.json()
        return data.get("employees", [])
    except Exception as e:
        st.error(f"Exception fetching employees: {str(e)}")
        return []

# --- Fetch categories ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_categories(token):
    """Fetch all categories from Loyverse API (your 23 locations!)"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = "https://api.loyverse.com/v1.0/categories"
    
    try:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            st.error(f"Error fetching categories: {res.status_code}")
            return []
        
        data = res.json()
        return data.get("categories", [])
    except Exception as e:
        st.error(f"Exception fetching categories: {str(e)}")
        return []

# --- Fetch items ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_all_items(token):
    """Fetch all items from Loyverse API (links products to categories/locations)"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = "https://api.loyverse.com/v1.0/items"
    
    all_items = []
    cursor = None
    limit = 250
    
    while True:
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            
        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code != 200:
                st.error(f"Error fetching items: {res.status_code}")
                break
                
            data = res.json()
            items = data.get("items", [])
            all_items.extend(items)
            
            cursor = data.get("cursor")
            if not cursor:
                break
                
        except Exception as e:
            st.error(f"Exception fetching items: {str(e)}")
            break
    
    return all_items

# --- Loyverse Importer Class (Robust & Idempotent) ---
class LoyverseImporter:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def check_exists(self, created_at, total_money, receipt_number=None):
        """
        Check if receipt exists by (created_at + total_money) or receipt_number.
        Returns existing ID if found, None otherwise.
        """
        # Search window: +/- 1 second to be safe, or exact match
        params = {
            "created_at_min": created_at,
            "created_at_max": created_at,
            "limit": 20
        }
        
        try:
            res = requests.get(BASE_URL, headers=self.headers, params=params, timeout=10)
            if res.status_code == 200:
                candidates = res.json().get('receipts', [])
                for r in candidates:
                    # 1. Check receipt number if provided (Strongest check)
                    if receipt_number and r.get('receipt_number') == receipt_number:
                        return r.get('id') or "EXISTING_NO_ID"
                    
                    # 2. Check total money (Secondary check)
                    # Note: Float comparison needs epsilon, but API returns string or float
                    api_total = float(r.get('total_money', 0))
                    if abs(api_total - float(total_money)) < 0.01:
                        return r.get('id') or "EXISTING_NO_ID"
                        
            return None
        except Exception as e:
            print(f"⚠️ Check failed: {e}")
            return "CHECK_FAILED"

    def import_receipt(self, receipt_data):
        """
        Import a single receipt idempotently.
        """
        created_at = receipt_data.get('created_at')
        total_money = receipt_data.get('total_money')
        receipt_number = receipt_data.get('receipt_number')
        
        if not created_at or total_money is None:
            print("❌ Invalid data: Missing created_at or total_money")
            return False

        # 1. Idempotency Check
        existing_id = self.check_exists(created_at, total_money, receipt_number)
        if existing_id == "CHECK_FAILED":
             print(f"⚠️ Skipped due to check failure: {created_at} - {total_money}")
             return False
        if existing_id:
            print(f"⏭️ Skipped duplicate: {created_at} - {total_money} (ID: {existing_id})")
            return True # Treated as success

        # 2. Create
        try:
            res = requests.post(BASE_URL, headers=self.headers, json=receipt_data, timeout=10)
            if res.status_code == 201:
                new_id = res.json().get('id')
                print(f"✅ Created: {created_at} - {total_money} (ID: {new_id})")
                return True
            else:
                print(f"❌ Failed to create: {res.status_code} - {res.text}")
                return False
        except Exception as e:
            print(f"❌ Network error: {e}")
            return False

# --- Helper: API call with pagination for receipts ---
def fetch_all_receipts(token, start_date, end_date, store_id=None, limit=250, render_ui=True, debug_sink=None):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    
    # Handle both date and datetime objects
    if isinstance(start_date, datetime):
        # If it's already a datetime, use it directly
        start_datetime_utc = start_date
        if start_datetime_utc.tzinfo is None:
            start_datetime_utc = pytz.UTC.localize(start_datetime_utc)
        elif start_datetime_utc.tzinfo != pytz.UTC:
            start_datetime_utc = start_datetime_utc.astimezone(pytz.UTC)
    else:
        # Convert GMT+7 date to UTC for API call
        gmt_plus_7 = pytz.timezone('Asia/Bangkok')  # GMT+7 timezone
        start_datetime_gmt7 = gmt_plus_7.localize(datetime.combine(start_date, datetime.min.time()))
        start_datetime_utc = start_datetime_gmt7.astimezone(pytz.UTC)
    
    if isinstance(end_date, datetime):
        # If it's already a datetime, use it directly
        end_datetime_utc = end_date
        if end_datetime_utc.tzinfo is None:
            end_datetime_utc = pytz.UTC.localize(end_datetime_utc)
        elif end_datetime_utc.tzinfo != pytz.UTC:
            end_datetime_utc = end_datetime_utc.astimezone(pytz.UTC)
    else:
        # Convert GMT+7 date to UTC (end of day in GMT+7)
        gmt_plus_7 = pytz.timezone('Asia/Bangkok')  # GMT+7 timezone
        end_datetime_gmt7 = gmt_plus_7.localize(datetime.combine(end_date, datetime.max.time()))
        end_datetime_utc = end_datetime_gmt7.astimezone(pytz.UTC)
    
    params = {
        "created_at_min": start_datetime_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        "created_at_max": end_datetime_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
        "limit": limit
    }
    if store_id:
        params["store_id"] = store_id

    if debug_sink is not None:
        debug_sink["date_range_gmt7"] = {"start": str(start_date), "end": str(end_date)}
        debug_sink["api_range_utc"] = {
            "start": start_datetime_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end_datetime_utc.strftime("%Y-%m-%d %H:%M:%S"),
        }
        debug_sink["store_filter"] = store_id if store_id else "All stores"

    # Debug console output
    if render_ui:
        with st.expander("🔍 Debug Console", expanded=False):
            st.write(f"**Token:** {token[:10]}...{token[-10:]}")
            st.write(f"**Date Range (GMT+7):** {start_date} to {end_date}")
            st.write(f"**API Range (UTC):** {start_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"**Store Filter:** {store_id if store_id else 'All stores'}")
    
    all_receipts = []
    cursor = None
    page_count = 0
    progress_bar = st.progress(0) if render_ui else None
    status_text = st.empty() if render_ui else None

    while True:
        page_count += 1
        if status_text is not None:
            status_text.text(f"Pages loaded: {page_count - 1} | Receipts loaded: {len(all_receipts)}")
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            res = requests.get(BASE_URL, headers=headers, params=params)
            
            if res.status_code != 200:
                if render_ui:
                    st.error(f"❌ **Error {res.status_code}:** {res.text}")
                if debug_sink is not None:
                    debug_sink["error"] = f"Error {res.status_code}: {res.text}"
                break
                
            data = res.json()
            receipts = data.get("receipts", [])
            
            all_receipts.extend(receipts)
            cursor = data.get("cursor")
            if status_text is not None:
                status_text.text(f"Pages loaded: {page_count} | Receipts loaded: {len(all_receipts)}")
            
            if progress_bar is not None:
                progress_bar.progress(min(page_count * 20, 100))
            
            if not cursor:
                if status_text is not None:
                    status_text.text(f"✅ Completed! Pages loaded: {page_count} | Receipts loaded: {len(all_receipts)}")
                break
                
        except Exception as e:
            if render_ui:
                st.error(f"❌ **Exception:** {str(e)}")
            if debug_sink is not None:
                debug_sink["error"] = f"Exception: {str(e)}"
            break
    
    if progress_bar is not None:
        progress_bar.progress(100)
    if debug_sink is not None:
        debug_sink["pages_fetched"] = page_count
        debug_sink["receipts_found"] = len(all_receipts)
    return all_receipts

# --- Helper: Convert UTC timestamp to GMT+7 date ---
def convert_utc_to_gmt7_date(utc_timestamp):
    """Convert UTC timestamp to GMT+7 date for display"""
    if not utc_timestamp:
        return None
    
    try:
        # Parse UTC timestamp
        if isinstance(utc_timestamp, str):
            # Handle different timestamp formats
            if 'T' in utc_timestamp:
                if utc_timestamp.endswith('Z'):
                    utc_dt = datetime.fromisoformat(utc_timestamp.replace('Z', '+00:00'))
                else:
                    utc_dt = datetime.fromisoformat(utc_timestamp)
            else:
                utc_dt = datetime.fromisoformat(utc_timestamp)
        else:
            utc_dt = utc_timestamp
            
        # Ensure it's timezone aware (UTC)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.UTC.localize(utc_dt)
        elif utc_dt.tzinfo != pytz.UTC:
            utc_dt = utc_dt.astimezone(pytz.UTC)
        
        # Convert to GMT+7
        gmt_plus_7 = pytz.timezone('Asia/Bangkok')
        gmt7_dt = utc_dt.astimezone(gmt_plus_7)
        
        return gmt7_dt.date()
    except Exception as e:
        # Fallback to original parsing
        return parse_date_safe(utc_timestamp)

# --- Helper: Parse date string safely ---
def parse_date_safe(date_str):
    """Safely parse date string that might be in various formats"""
    if not date_str:
        return None
    
    # Remove timezone info and try different formats
    clean_date = date_str.split('T')[0]  # Get just the date part
    
    try:
        # Try parsing as simple date
        return datetime.strptime(clean_date, '%Y-%m-%d').date()
    except ValueError:
        try:
            # Try parsing as ISO format
            return datetime.fromisoformat(clean_date).date()
        except ValueError:
            # Last resort: try to extract just the date part
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_str)
            if date_match:
                return datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
            return None


# --- Product category mapping helpers ---
HARDCODED_CATEGORY_OVERRIDES = {
    "หลอด": "🧊 หลอดเล็ก (Small Tube)",
    "ป่น20kg": "🧊 ป่น (Crushed Ice)",
    "coolcorner": "🧊 หลอดเล็ก (Small Tube)",
    "น้ําแข็งถุงใส13kg": "🧊 หลอดเล็ก (Small Tube)",
    "น้ำแข็งถุงใส13kg": "🧊 หลอดเล็ก (Small Tube)",
    "ถุงใส20kg": "🧊 หลอดเล็ก (Small Tube)",
    "eatamare20kg": "🧊 หลอดเล็ก (Small Tube)",
    "ถุงใส13kg": "🧊 หลอดเล็ก (Small Tube)",
    "บดซีฟู๊ด": "🧊 ป่น (Crushed Ice)",
    "ถุงใส": "🧊 หลอดเล็ก (Small Tube)",
}


def normalize_product_name(product_name):
    if pd.isna(product_name):
        return ""
    return re.sub(r"[\s\.\-_/]+", "", str(product_name).lower())


def categorize_ice_product_name(product_name, manual_categories=None):
    """Categorize products using manual overrides, hardcoded map, then keyword fallback."""
    if pd.isna(product_name):
        return "📦 อื่นๆ (Other)"

    product_raw = str(product_name)
    if manual_categories and product_raw in manual_categories:
        return manual_categories[product_raw]

    product_key = normalize_product_name(product_raw)
    if product_key in HARDCODED_CATEGORY_OVERRIDES:
        return HARDCODED_CATEGORY_OVERRIDES[product_key]

    product_str = product_raw.lower()
    if "ป่น" in product_str:
        return "🧊 ป่น (Crushed Ice)"
    if "หลอดเล็ก" in product_str or ("หลอด" in product_str and "เล็ก" in product_str):
        return "🧊 หลอดเล็ก (Small Tube)"
    if "หลอดใหญ่" in product_str or ("หลอด" in product_str and "ใหญ่" in product_str):
        return "🧊 หลอดใหญ่ (Large Tube)"
    return "📦 อื่นๆ (Other)"

# --- Helper: Get smart sync date range ---
def get_smart_sync_range(db):
    """Get intelligent sync date range based on existing data - starts from exact latest timestamp"""
    date_range = db.get_date_range()
    
    # Debug information
    with st.expander("🔍 Sync Missing Data Debug", expanded=False):
        st.write(f"**Raw date range from DB:** {date_range}")
        if date_range and date_range[1]:
            st.write(f"**Latest timestamp:** {date_range[1]}")
    
    if date_range and date_range[1]:  # If we have data, start from exact latest timestamp
        latest_timestamp = date_range[1]
        
        try:
            # Parse the latest timestamp as UTC
            if latest_timestamp.endswith('Z'):
                latest_utc = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
            else:
                latest_utc = datetime.fromisoformat(latest_timestamp)
            
            # Ensure it's timezone aware (UTC)
            if latest_utc.tzinfo is None:
                latest_utc = pytz.UTC.localize(latest_utc)
            elif latest_utc.tzinfo != pytz.UTC:
                latest_utc = latest_utc.astimezone(pytz.UTC)
            
            # Start from latest timestamp + 1 second to avoid duplicates
            start_utc = latest_utc + timedelta(seconds=1)
            end_utc = datetime.now(pytz.UTC)
            
            # Convert to GMT+7 for display
            gmt_plus_7 = pytz.timezone('Asia/Bangkok')
            start_gmt7 = start_utc.astimezone(gmt_plus_7)
            end_gmt7 = end_utc.astimezone(gmt_plus_7)
            
            # Convert to date objects for the return (API will handle precise timestamps)
            start_date = start_gmt7.date()
            end_date = end_gmt7.date()
            
            # Debug info
            with st.expander("🔍 Sync Missing Data Debug", expanded=False):
                st.write(f"**Raw date range from DB:** {date_range}")
                st.write(f"**Latest timestamp (UTC):** {latest_utc}")
                st.write(f"**Start timestamp (UTC):** {start_utc}")
                st.write(f"**End timestamp (UTC):** {end_utc}")
                st.write(f"**Start date (GMT+7):** {start_date}")
                st.write(f"**End date (GMT+7):** {end_date}")
            
            # If start is in the future, sync last 7 days instead
            if start_date > end_date:
                end_date = datetime.today().date()
                start_date = end_date - timedelta(days=7)
                return start_date, end_date, f"Start date was in future, syncing last 7 days from {end_date}"
            
            return start_date, end_date, f"Continuing from exact timestamp {latest_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
        except Exception as e:
            # If we can't parse the timestamp, fall back to last 30 days
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=30)
            return start_date, end_date, f"Could not parse latest timestamp '{latest_timestamp}': {str(e)}. Syncing last 30 days"
    else:  # If no data, start from 30 days ago
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date, "No existing data, syncing last 30 days"

# ===== END FUNCTION DEFINITIONS =====

# Initialize database
try:
    db = LoyverseDB()
    print(f"✅ Database initialized successfully at: {db.db_path}")
    
    # Verify tables exist
    if not db.verify_tables_exist():
        print("⚠️ Some tables missing, reinitializing database...")
        db.init_database()
        db.verify_tables_exist()
        
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    # Create a fallback database
    db = LoyverseDB("loyverse_data.db")
    print(f"✅ Fallback database created at: {db.db_path}")

# Initialize reference data
if 'ref_data' not in st.session_state:
    try:
        st.session_state.ref_data = ReferenceData(db)
        print("✅ Reference data initialized successfully")
    except Exception as e:
        print(f"⚠️ Reference data initialization failed: {e}")
        # Create empty reference data
        st.session_state.ref_data = ReferenceData(db)
ref_data = st.session_state.ref_data

# Ensure customer map is always initialized for customer analysis/rendering.
if 'customer_map' not in st.session_state:
    st.session_state.customer_map = db.get_customer_map() or {}
customer_map = st.session_state.get('customer_map', {})

# Ensure manual product categories are always available across tabs.
if 'manual_categories' not in st.session_state:
    st.session_state.manual_categories = db.get_manual_categories() or {}

# Initialize selected tab with proper translation
initialize_selected_tab()

# ========== SIDEBAR NAVIGATION ==========
st.sidebar.markdown("""
<div style="padding: 4px 0 8px 0;">
    <span style="font-size: 18px; font-weight: 600; letter-spacing: -0.02em; color: var(--text-primary, #0f172a);">Snow AI</span>
</div>
""", unsafe_allow_html=True)

# Load Database + Language row
load_col, lang_col1, lang_col2 = st.sidebar.columns([2, 1, 1])
with load_col:
    if st.button(get_text("load_database"), key="load_db_main", use_container_width=True, type="primary"):
        try:
            if not db.verify_tables_exist():
                st.sidebar.error("Database tables not initialized.")
                st.stop()
            df = db.get_receipts_dataframe()
            if not df.empty:
                st.session_state.receipts_df = df
                total_receipts = db.get_receipt_count()
                st.sidebar.success(get_text("loaded_success", total_receipts=total_receipts, line_items=len(df)))
            else:
                st.sidebar.warning(get_text("no_cached_data"))
        except Exception as e:
            st.sidebar.error(f"Database error: {str(e)}")

with lang_col1:
    if st.button("EN", key="lang_english", 
                type="primary" if st.session_state.language == "English" else "secondary",
                use_container_width=True):
        st.session_state.language = "English"
        st.rerun()

with lang_col2:
    if st.button("TH", key="lang_thai",
                type="primary" if st.session_state.language == "Thai" else "secondary", 
                use_container_width=True):
        st.session_state.language = "Thai"
        st.rerun()

st.sidebar.markdown("---")

# Dedicated import/reconciliation workspace
DATA_IMPORT_TAB = "Data Import & Reconciliation"
SETTINGS_TAB = get_text("settings_preferences")

# Tab navigation buttons
tabs = [
    get_text("daily_sales"),
    get_text("by_location"), 
    get_text("by_product"),
    get_text("by_customer"),
    get_text("credit"),
    get_text("interactive_data"),
    get_text("transaction_log"),
    get_text("customer_invoice"),
    get_text("ice_forecast"),
    get_text("crm"),
]

for tab in tabs:
    if st.sidebar.button(tab, key=f"nav_{tab}", use_container_width=True, 
                        type="primary" if st.session_state.selected_tab == tab else "secondary"):
        st.session_state.selected_tab = tab
        st.rerun()

st.sidebar.markdown("---")

# Logout at bottom
if st.sidebar.button(get_text("logout"), key="logout_btn", use_container_width=True, type="secondary"):
    st.session_state.authenticated = False
    st.rerun()

# Keep Settings button directly below Sign Out
if st.sidebar.button(
    get_text("settings_preferences"),
    key="open_settings_btn",
    use_container_width=True,
    type="primary" if st.session_state.selected_tab == SETTINGS_TAB else "secondary",
):
    st.session_state.selected_tab = SETTINGS_TAB
    st.rerun()

if st.sidebar.button(
    DATA_IMPORT_TAB,
    key="open_reconciliation_btn",
    use_container_width=True,
    type="primary" if st.session_state.selected_tab == DATA_IMPORT_TAB else "secondary",
):
    st.session_state.selected_tab = DATA_IMPORT_TAB
    st.rerun()

with st.sidebar.expander("Sync", expanded=False):
    if st.button(
        get_text("settings_sync_last_date"),
        key="sidebar_sync_last_date_btn",
        use_container_width=True,
        type="primary",
    ):
        sync_start, sync_end, sync_msg = get_smart_sync_range(db)
        st.session_state.sync_start_date = sync_start
        st.session_state.sync_end_date = sync_end
        st.session_state.sync_mode = "last_date"
        st.session_state.trigger_sync = True
        st.session_state.is_sync_missing = True
        st.session_state.sync_status_banner = {
            "level": "info",
            "message": f"{sync_msg} ({sync_start} -> {sync_end})",
        }

# Full Settings tab - sync-first, simplified layout
if st.session_state.selected_tab == SETTINGS_TAB:
    st.subheader(get_text("settings_preferences"))
    st.caption(get_text("settings_sync_caption"))

    if "last_sync_report" not in st.session_state:
        st.session_state.last_sync_report = None

    # 1) Sync Settings
    st.markdown(f"### {get_text('settings_sync_header')}")

    sync_col1, sync_col2 = st.columns([1, 2])
    with sync_col1:
        if st.button(
            get_text("settings_sync_last_date"),
            help=get_text("settings_sync_last_date_help"),
            key="settings_sync_last_date_btn",
            use_container_width=True,
            type="primary",
        ):
            sync_start, sync_end, sync_msg = get_smart_sync_range(db)
            st.session_state.sync_start_date = sync_start
            st.session_state.sync_end_date = sync_end
            st.session_state.sync_mode = "last_date"
            st.session_state.trigger_sync = True
            st.session_state.is_sync_missing = True
            st.info(f"{sync_msg} ({sync_start} -> {sync_end})")

        if st.button(
            get_text("settings_sync_metadata"),
            help=get_text("settings_sync_metadata_help"),
            key="settings_sync_metadata_btn",
            use_container_width=True,
        ):
            with st.spinner(get_text("settings_sync_metadata_running")):
                total_synced = 0

                customers = fetch_all_customers(LOYVERSE_TOKEN)
                if customers:
                    total_synced += db.save_customers(customers)

                payment_types = fetch_all_payment_types(LOYVERSE_TOKEN)
                if payment_types:
                    total_synced += db.save_payment_types(payment_types)

                stores = fetch_all_stores(LOYVERSE_TOKEN)
                if stores:
                    total_synced += db.save_stores(stores)

                employees = fetch_all_employees(LOYVERSE_TOKEN)
                if employees:
                    total_synced += db.save_employees(employees)

                categories = fetch_all_categories(LOYVERSE_TOKEN)
                if categories:
                    total_synced += db.save_categories(categories)

                items = fetch_all_items(LOYVERSE_TOKEN)
                if items:
                    total_synced += db.save_items(items)

                ref_data.refresh()

            st.success(get_text("settings_sync_metadata_done", total=total_synced))
            st.rerun()

    with sync_col2:
        st.markdown(f"**{get_text('settings_custom_range')}**")
        custom_col1, custom_col2 = st.columns(2)
        default_start = st.session_state.get("sync_start_date", datetime.today().date() - timedelta(days=30))
        if hasattr(default_start, "date"):
            default_start = default_start.date()
        default_end = st.session_state.get("sync_end_date", datetime.today().date())
        if hasattr(default_end, "date"):
            default_end = default_end.date()

        with custom_col1:
            sync_start = st.date_input(
                get_text("start_date"),
                value=default_start,
                min_value=datetime(2020, 1, 1).date(),
                max_value=datetime.today().date(),
                key="settings_sync_start_date",
            )
        with custom_col2:
            sync_end = st.date_input(
                get_text("end_date"),
                value=default_end,
                min_value=datetime(2020, 1, 1).date(),
                max_value=datetime.today().date(),
                key="settings_sync_end_date",
            )

        sync_store_filter = st.text_input(
            get_text("settings_store_filter"),
            value=st.session_state.get("sync_store_filter", ""),
            help=get_text("settings_store_filter_help"),
            key="settings_store_filter",
        )
        st.session_state.sync_store_filter = sync_store_filter

        st.session_state.sync_start_date = sync_start
        st.session_state.sync_end_date = sync_end
        st.caption(
            get_text(
                "settings_sync_preview_caption",
                start_date=sync_start.isoformat(),
                end_date=sync_end.isoformat(),
                days=(sync_end - sync_start).days + 1,
            )
        )
        if st.button(
            get_text("settings_sync_custom_range"),
            key="settings_sync_custom_btn",
            use_container_width=True,
        ):
            if sync_start > sync_end:
                st.error(get_text("settings_invalid_date_range"))
            else:
                st.session_state.sync_mode = "custom_range"
                st.session_state.trigger_sync = True
                st.session_state.is_sync_missing = False

    sync_status = st.session_state.get("sync_status_banner")
    if sync_status and sync_status.get("message"):
        level = sync_status.get("level", "info")
        message = sync_status.get("message")
        if level == "success":
            st.success(message)
        elif level == "warning":
            st.warning(message)
        elif level == "error":
            st.error(message)
        else:
            st.info(message)

    # Sync fetch status indicator (shown above Sync Results & Debug)
    if st.session_state.get("trigger_sync", False):
        st.caption("Fetching receipts from Loyverse API...")
    latest_report = st.session_state.get("last_sync_report") or {}
    fetch_debug = latest_report.get("fetch_debug") or {}
    if fetch_debug:
        pages = fetch_debug.get("pages_fetched")
        receipts_loaded = fetch_debug.get("receipts_found")
        if pages is not None and receipts_loaded is not None:
            st.caption(f"Pages loaded: {pages} | Receipts loaded: {receipts_loaded}")

    st.markdown("---")

    # 2) Sync Results & Debug
    st.markdown(f"### {get_text('settings_sync_results')}")
    last_sync_report = st.session_state.get("last_sync_report")
    if last_sync_report:
        rcol1, rcol2, rcol3 = st.columns(3)
        rcol1.metric(get_text("settings_last_mode"), last_sync_report.get("mode", "-"))
        rcol2.metric(get_text("settings_fetched_count"), f"{last_sync_report.get('fetched_count', 0):,}")
        rcol3.metric(get_text("settings_saved_count"), f"{last_sync_report.get('saved_count', 0):,}")

        rcol4, rcol5, rcol6 = st.columns(3)
        rcol4.metric(get_text("settings_duplicates"), f"{last_sync_report.get('duplicate_skips', 0):,}")
        rcol5.metric(get_text("settings_collisions"), f"{last_sync_report.get('collision_signals', 0):,}")
        rcol6.metric(get_text("settings_new_transactions"), f"{last_sync_report.get('new_transactions', 0):,}")

        st.caption(
            f"{get_text('settings_last_range')}: "
            f"{last_sync_report.get('sync_start_date', '-')}"
            f" -> {last_sync_report.get('sync_end_date', '-')}"
        )

        with st.expander(get_text("settings_debug_console"), expanded=False):
            st.json(last_sync_report)
    else:
        st.info(get_text("settings_sync_results_empty"))

    with st.expander("API Endpoints Used", expanded=False):
        token_preview = f"{LOYVERSE_TOKEN[:10]}...{LOYVERSE_TOKEN[-10:]}" if LOYVERSE_TOKEN else "Not configured"
        st.markdown(f"""
### **Fetch Receipts**
**Endpoint:** `GET /v1.0/receipts`  
**Called when:** You run sync/import actions

**Parameters:**
- `created_at_min` - Start date/time (UTC)
- `created_at_max` - End date/time (UTC)
- `limit` - 250 receipts per page
- `store_id` - Optional store filter
- `cursor` - For pagination

**Returns:** Receipt data including:
- Receipt details (number, date, total)
- Line items (products, quantities, prices)
- Payments (payment types, amounts)
- Customer IDs, store IDs, employee IDs

---

### **Fetch Customers**
**Endpoint:** `GET /v1.0/customers`  
**Called when:** Customer sync/load operations

**Parameters:**
- `limit` - 250 customers per page
- `cursor` - For pagination

**Returns:** Customer data including:
- Customer ID (UUID)
- Customer name
- Customer code (numeric POS ID)
- Email, phone, address
- Visit history, total spent

---

### **Authentication**
- Uses Bearer Token: `{token_preview}`
- All requests include `Authorization` header

### **Data Processing**
1. Fetches all receipts in date range (with pagination)
2. Flattens nested JSON into flat table structure
3. Maps customer UUIDs to names
4. Calculates aggregations for charts

### **Full Documentation**
See `API_REFERENCE.md` for complete details, response examples, and curl commands.
""")

    st.markdown("---")

    # 3) Imported Data Snapshot
    st.markdown(f"### {get_text('settings_imported_snapshot')}")
    try:
        conn = db.get_connection()
        receipt_count_df = pd.read_sql_query("SELECT COUNT(*) AS c FROM receipts", conn)
        line_count_df = pd.read_sql_query("SELECT COUNT(*) AS c FROM line_items", conn)
        recent_receipts = pd.read_sql_query(
            """
            SELECT
                receipt_number,
                store_id,
                receipt_type,
                total_money,
                total_discount,
                COALESCE(receipt_date, created_at) AS event_ts
            FROM receipts
            ORDER BY COALESCE(receipt_date, created_at) DESC
            LIMIT 20
            """,
            conn,
        )
        conn.close()
        db_date_range = db.get_date_range()

        snapshot_col1, snapshot_col2, snapshot_col3 = st.columns(3)
        snapshot_col1.metric(get_text("settings_db_receipts"), f"{int(receipt_count_df['c'].iloc[0]):,}")
        snapshot_col2.metric(get_text("settings_db_line_items"), f"{int(line_count_df['c'].iloc[0]):,}")
        if db_date_range and db_date_range[0] and db_date_range[1]:
            snapshot_col3.metric(get_text("settings_db_range"), f"{db_date_range[0][:10]} -> {db_date_range[1][:10]}")
        else:
            snapshot_col3.metric(get_text("settings_db_range"), "-")

        st.markdown(f"**{get_text('settings_recent_imports')}**")
        if recent_receipts.empty:
            st.info(get_text("settings_no_receipts_preview"))
        else:
            st.dataframe(recent_receipts, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Snapshot unavailable: {str(e)}")

    st.markdown("---")

    # 4) Basic Preferences
    st.markdown(f"### {get_text('settings_basic_preferences')}")
    current_theme = resolve_theme_mode()

    col1, col2 = st.columns(2)
    with col1:
        if st.button(get_text('light'), use_container_width=True, 
                    type="primary" if current_theme == THEME_LIGHT else "secondary"):
            apply_theme_mode(THEME_LIGHT)
            st.rerun()
    
    with col2:
        if FORCE_LIGHT_THEME:
            st.button(get_text('dark'), use_container_width=True, disabled=True)
        else:
            if st.button(get_text('dark'), use_container_width=True,
                        type="primary" if current_theme == THEME_DARK else "secondary"):
                apply_theme_mode(THEME_DARK)
                st.rerun()
    if FORCE_LIGHT_THEME:
        st.caption(get_text("settings_theme_locked_light"))

    # Language selector
    language = st.radio(
        get_text("settings_language"),
        ["English", "Thai"],
        index=0 if st.session_state.language == "English" else 1,
        horizontal=True,
        key="settings_language_radio",
    )
    if language != st.session_state.language:
        st.session_state.language = language
        st.rerun()

# Store settings values in session state for use outside the expander
if 'sync_start_date' in st.session_state:
    start_date = st.session_state.sync_start_date
else:
    start_date = datetime.today() - timedelta(days=7)

if 'sync_end_date' in st.session_state:
    end_date = st.session_state.sync_end_date
else:
    end_date = datetime.today()

if 'sync_store_filter' in st.session_state:
    store_filter = st.session_state.sync_store_filter
else:
    store_filter = ""


def set_sync_status(level, message):
    """Persist sync banner so it renders under settings sync buttons."""
    st.session_state.sync_status_banner = {"level": level, "message": message}

# ========== MAIN CONTENT ==========

# Get database stats for date navigator
try:
    db_stats = db.get_database_stats()
except Exception as e:
    st.error(f"❌ Database error: {str(e)}")
    st.info("💡 Database tables may not be initialized. Check deployment logs.")
    db_stats = {'customers': 0, 'receipts': 0, 'categories': 0, 'items': 0, 'date_range': [None, None]}

if st.session_state.selected_tab != SETTINGS_TAB:
    # Enhanced Date Selector
    st.markdown(f"### {get_text('date_range_selector')}")

    if db_stats['date_range'][0]:
        min_date = pd.to_datetime(db_stats['date_range'][0]).date()
        max_date = pd.to_datetime(db_stats['date_range'][1]).date()

        # Initialize session state for date selector
        if 'date_selector_start' not in st.session_state:
            st.session_state.date_selector_start = max_date - timedelta(days=7)
        if 'date_selector_end' not in st.session_state:
            st.session_state.date_selector_end = max_date

        # Ensure session state values are within valid range
        st.session_state.date_selector_start = max(min_date, min(max_date, st.session_state.date_selector_start))
        st.session_state.date_selector_end = max(min_date, min(max_date, st.session_state.date_selector_end))

        # Quick shortcut buttons - split into two rows for better spacing/readability
        def _apply_quick_range(quick_start, quick_end):
            st.session_state.date_selector_start = quick_start
            st.session_state.date_selector_end = quick_end
            st.session_state.view_start_date = quick_start
            st.session_state.view_end_date = quick_end
            st.rerun()

        row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
        with row1_col1:
            if st.button(get_text("today"), key="quick_today", use_container_width=True):
                _apply_quick_range(max_date, max_date)
        with row1_col2:
            if st.button(get_text("yesterday"), key="quick_yesterday", use_container_width=True):
                yesterday = max_date - timedelta(days=1)
                _apply_quick_range(yesterday, yesterday)
        with row1_col3:
            if st.button(get_text("last_week"), key="quick_last_week", use_container_width=True):
                week_start = max(min_date, max_date - timedelta(days=6))
                _apply_quick_range(week_start, max_date)
        with row1_col4:
            if st.button(get_text("this_month"), key="quick_this_month", use_container_width=True):
                month_start = max_date.replace(day=1)
                _apply_quick_range(month_start, max_date)

        row2_col1, row2_col2, row2_col3, row2_col4 = st.columns(4)
        with row2_col1:
            if st.button(get_text("last_month"), key="quick_last_month", use_container_width=True):
                if max_date.month == 1:
                    last_month_start = max_date.replace(year=max_date.year - 1, month=12, day=1)
                else:
                    last_month_start = max_date.replace(month=max_date.month - 1, day=1)
                if last_month_start.month == 12:
                    next_month = last_month_start.replace(year=last_month_start.year + 1, month=1, day=1)
                else:
                    next_month = last_month_start.replace(month=last_month_start.month + 1, day=1)
                last_month_end = next_month - timedelta(days=1)
                _apply_quick_range(last_month_start, last_month_end)
        with row2_col2:
            if st.button(get_text("last_3_months"), key="quick_last_3_months", use_container_width=True):
                if max_date.month <= 3:
                    start_month = max_date.month + 9
                    start_year = max_date.year - 1
                else:
                    start_month = max_date.month - 3
                    start_year = max_date.year
                three_months_start = max_date.replace(year=start_year, month=start_month, day=1)
                _apply_quick_range(three_months_start, max_date)
        with row2_col3:
            if st.button(get_text("this_year"), key="quick_this_year", use_container_width=True):
                year_start = max_date.replace(month=1, day=1)
                _apply_quick_range(year_start, max_date)
        with row2_col4:
            if st.button(get_text("all_data"), key="quick_all_data", use_container_width=True):
                _apply_quick_range(min_date, max_date)

        # Date range inputs
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            start_date = st.date_input(
                get_text("start_date"),
                value=st.session_state.date_selector_start,
                min_value=min_date,
                max_value=max_date,
                key="enhanced_start_date"
            )

        with col2:
            end_date = st.date_input(
                get_text("end_date"),
                value=st.session_state.date_selector_end,
                min_value=min_date,
                max_value=max_date,
                key="enhanced_end_date"
            )

        with col3:
            st.write("")  # Spacing
            st.write("")  # Spacing
            if st.button(get_text("apply_range"), key="apply_date_range", type="primary"):
                # Store selected dates in session state
                st.session_state.view_start_date = start_date
                st.session_state.view_end_date = end_date
                st.session_state.date_selector_start = start_date
                st.session_state.date_selector_end = end_date
                st.rerun()

        # Show current selection as a subtle caption
        if 'view_start_date' in st.session_state and 'view_end_date' in st.session_state:
            days_diff = (st.session_state.view_end_date - st.session_state.view_start_date).days + 1
            st.caption(
                get_text(
                    'current_selection',
                    start_date=st.session_state.view_start_date.strftime('%Y-%m-%d'),
                    end_date=st.session_state.view_end_date.strftime('%Y-%m-%d'),
                    days=days_diff,
                )
            )
    else:
        st.info("No cached data. Load data first to use date navigator.")

# Handle data loading button actions from settings
sync_data = st.session_state.get('trigger_sync', False)
load_db = st.session_state.get('trigger_load', False)
clear_db = st.session_state.get('trigger_clear', False)

# Clear database
if clear_db:
    db.clear_all_data()
    st.success("✅ Database cleared")
    st.session_state.trigger_clear = False
    st.rerun()

# Sync data from API
if sync_data:
    # Use the sync date range from the new controls
    sync_start_date = st.session_state.get('sync_start_date', datetime.today() - timedelta(days=30))
    sync_end_date = st.session_state.get('sync_end_date', datetime.today())
    # Normalize DB date filters to date-only values for all sync modes.
    if hasattr(sync_start_date, 'date'):
        sync_start_date = sync_start_date.date()
    if hasattr(sync_end_date, 'date'):
        sync_end_date = sync_end_date.date()
    sync_mode = st.session_state.get("sync_mode", "custom_range")
    sync_report = {
        "mode": sync_mode,
        "sync_start_date": sync_start_date.isoformat(),
        "sync_end_date": sync_end_date.isoformat(),
        "store_filter": store_filter or "",
        "fetched_count": 0,
        "saved_count": 0,
        "duplicate_skips": 0,
        "duplicate_by_id": 0,
        "duplicate_by_receipt_number": 0,
        "collision_signals": 0,
        "existing_count": 0,
        "new_count": 0,
        "new_transactions": 0,
    }
    set_sync_status("info", f"🔄 Syncing receipts from {sync_start_date} to {sync_end_date}")
    
    # Handle precise timestamps for sync missing data
    if st.session_state.get('is_sync_missing', False):
        # For sync missing data, we need to get the precise timestamps
        # Re-call get_smart_sync_range to get the exact UTC timestamps
        start_date, end_date, message = get_smart_sync_range(db)
        
        # Get the precise timestamps from the database
        date_range = db.get_date_range()
        if date_range and date_range[1]:
            latest_timestamp = date_range[1]
            try:
                # Parse the latest timestamp as UTC
                if latest_timestamp.endswith('Z'):
                    latest_utc = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
                else:
                    latest_utc = datetime.fromisoformat(latest_timestamp)
                
                # Ensure it's timezone aware (UTC)
                if latest_utc.tzinfo is None:
                    latest_utc = pytz.UTC.localize(latest_utc)
                elif latest_utc.tzinfo != pytz.UTC:
                    latest_utc = latest_utc.astimezone(pytz.UTC)
                
                # Start from latest timestamp + 1 second to avoid duplicates
                sync_start_datetime = latest_utc + timedelta(seconds=1)
                sync_end_datetime = datetime.now(pytz.UTC)
                api_start = sync_start_datetime
                api_end = sync_end_datetime
            except Exception as e:
                # Fallback: use Bangkok calendar dates for API (same as custom sync)
                api_start = sync_start_date
                api_end = sync_end_date
        else:
            # Fallback: use Bangkok calendar dates for API
            api_start = sync_start_date
            api_end = sync_end_date
        
        # Clear the flag
        st.session_state.is_sync_missing = False
    else:
        # For custom/range sync: user picks Bangkok calendar dates.
        # Pass DATE objects so fetch_all_receipts converts Bangkok -> UTC correctly.
        # (Previously we passed naive datetime and it was treated as UTC, missing
        # 00:00-06:59 Bangkok and misaligning with POS export.)
        api_start = sync_start_date
        api_end = sync_end_date
    sync_report["api_range"] = {"start": str(api_start), "end": str(api_end)}
    
    # Check what's already in database for this range (DB stores UTC; we query by date strings)
    existing_df = db.get_receipts_dataframe(
        start_date=sync_start_date.isoformat(),
        end_date=sync_end_date.isoformat(),
        store_id=store_filter if store_filter else None
    )
    existing_count = len(existing_df) if not existing_df.empty else 0
    sync_report["existing_count"] = existing_count
    
    fetch_debug = {}
    with st.spinner(f"Fetching receipts from API ({sync_start_date} to {sync_end_date})..."):
        receipts = fetch_all_receipts(
            LOYVERSE_TOKEN,
            api_start,
            api_end,
            store_filter,
            render_ui=False,
            debug_sink=fetch_debug,
        )
    sync_report["fetch_debug"] = fetch_debug
    set_sync_status("info", f"🔍 Fetch completed: found {len(receipts) if receipts else 0} receipts.")
    sync_report["fetched_count"] = len(receipts) if receipts else 0
    
    if receipts:
        # --- DEDUP GUARDRAILS ---
        # Guardrail: never dedupe by (created_at + amount) alone because many
        # legitimate receipts can share the same second and value.
        conn = db.get_connection()
        existing_core_query = """
            SELECT receipt_id, receipt_number, store_id, created_at, receipt_date, total_money
            FROM receipts
            WHERE DATE(COALESCE(receipt_date, created_at)) >= ? AND DATE(COALESCE(receipt_date, created_at)) <= ?
        """
        query_params = [sync_start_date.isoformat(), sync_end_date.isoformat()]
        if store_filter:
            existing_core_query += " AND store_id = ?"
            query_params.append(store_filter)
        existing_core = pd.read_sql_query(existing_core_query, conn, params=query_params)
        conn.close()

        existing_receipt_ids = set(existing_core["receipt_id"].dropna().astype(str).tolist())
        existing_number_keys = set(
            zip(
                existing_core["store_id"].fillna("").astype(str),
                existing_core["receipt_number"].fillna("").astype(str),
            )
        )
        existing_time_amount_store_keys = set(
            zip(
                existing_core["created_at"].fillna("").astype(str),
                existing_core["total_money"].fillna(0).astype(float).round(2),
                existing_core["store_id"].fillna("").astype(str),
            )
        )

        unique_receipts = []
        duplicate_by_id_count = 0
        duplicate_by_number_count = 0
        suspicious_time_amount_collisions = 0

        for r in receipts:
            receipt_id = str(r.get("id") or r.get("receipt_number") or "")
            receipt_number = str(r.get("receipt_number") or "")
            receipt_store = str(r.get("store_id") or "")
            receipt_created = str(r.get("created_at") or "")
            receipt_total = round(float(r.get("total_money", 0) or 0), 2)

            if receipt_id and receipt_id in existing_receipt_ids:
                duplicate_by_id_count += 1
                continue

            if receipt_number and (receipt_store, receipt_number) in existing_number_keys:
                duplicate_by_number_count += 1
                continue

            # Guardrail signal only: we don't skip on this weak key.
            if (receipt_created, receipt_total, receipt_store) in existing_time_amount_store_keys:
                suspicious_time_amount_collisions += 1

            unique_receipts.append(r)
            if receipt_id:
                existing_receipt_ids.add(receipt_id)
            if receipt_number:
                existing_number_keys.add((receipt_store, receipt_number))

        skipped_duplicates = duplicate_by_id_count + duplicate_by_number_count
        sync_report["duplicate_skips"] = skipped_duplicates
        sync_report["duplicate_by_id"] = duplicate_by_id_count
        sync_report["duplicate_by_receipt_number"] = duplicate_by_number_count
        sync_report["collision_signals"] = suspicious_time_amount_collisions
        # Save to database (INSERT OR REPLACE = merge/upsert)
        saved_count = db.save_receipts(unique_receipts)
        db.update_sync_time('receipts', f"{saved_count} receipts")
        sync_report["saved_count"] = saved_count
        sync_report["unique_receipts_count"] = len(unique_receipts)

        # Post-sync integrity guardrail: duplicate receipt numbers in range.
        conn = db.get_connection()
        dup_num_query = """
            SELECT store_id, receipt_number, COUNT(*) AS c
            FROM receipts
            WHERE DATE(COALESCE(receipt_date, created_at)) >= ? AND DATE(COALESCE(receipt_date, created_at)) <= ?
              AND receipt_number IS NOT NULL
            GROUP BY store_id, receipt_number
            HAVING c > 1
            ORDER BY c DESC
            LIMIT 20
        """
        dup_num_df = pd.read_sql_query(
            dup_num_query,
            conn,
            params=[sync_start_date.isoformat(), sync_end_date.isoformat()],
        )
        conn.close()
        if not dup_num_df.empty:
            st.error(
                f"🚨 Guardrail: Found {len(dup_num_df)} duplicate receipt-number groups "
                f"in synced range ({sync_start_date} to {sync_end_date})."
            )
            with st.expander("Show duplicate receipt-number groups", expanded=False):
                st.dataframe(dup_num_df, use_container_width=True, hide_index=True)
        
        # Check if we added new data or just updated
        new_df = db.get_receipts_dataframe(
            start_date=sync_start_date.isoformat(),
            end_date=sync_end_date.isoformat(),
            store_id=store_filter if store_filter else None
        )
        new_count = len(new_df) if not new_df.empty else 0
        sync_report["new_count"] = new_count
        sync_report["new_transactions"] = max(0, new_count - existing_count)
        
        if new_count > existing_count:
            set_sync_status("success", f"✅ Added {new_count - existing_count} new transactions.")
        else:
            set_sync_status("success", f"✅ Sync completed. Updated {saved_count} receipts (no new data).")
        
        # Load ALL data from database (not just this date range)
        df = db.get_receipts_dataframe()
        st.session_state.receipts_df = df
    else:
        set_sync_status("warning", f"⚠️ No receipts found in range {sync_start_date} to {sync_end_date}.")
        sync_report["status"] = "no_receipts_found"
    
    st.session_state.last_sync_report = sync_report
    
    st.session_state.trigger_sync = False
    st.rerun()

# Load from database
if load_db:
    # Load ALL data from database (not filtered by date range)
    df = db.get_receipts_dataframe()
    
    if not df.empty:
        st.session_state.receipts_df = df
        total_receipts = db.get_receipt_count()
        st.success(f"✅ Loaded ALL data from database")
        st.info(f"📊 Total: {total_receipts} receipts, {len(df)} line items")
        st.caption("💡 Use Quick Date Navigator above to filter by date")
    else:
        st.warning("⚠️ No cached data. Click 'Sync' first.")
    
    st.session_state.trigger_load = False

# Check if we have data to display
if st.session_state.selected_tab != SETTINGS_TAB and 'receipts_df' in st.session_state and not st.session_state.receipts_df.empty:
    df = st.session_state.receipts_df
    
    if not df.empty:
        # --- Data Cleaning ---
        df["date"] = pd.to_datetime(df["date"])
        # Convert UTC timestamps to GMT+7 dates for proper display
        df["day"] = df["date"].apply(lambda x: convert_utc_to_gmt7_date(x) if pd.notna(x) else None)
        
        # Enrich with reference data (adds customer_name, payment_name, store_name, employee_name)
        df = ref_data.enrich_dataframe(df)
        
        # Apply quick date filter if set
        if 'view_start_date' in st.session_state and 'view_end_date' in st.session_state:
            view_start = st.session_state.view_start_date
            view_end = st.session_state.view_end_date
            df = df[(df['day'] >= view_start) & (df['day'] <= view_end)]
            
            if not df.empty:
                st.info(f"📅 Viewing data from {view_start} to {view_end} ({len(df)} transactions)")
            else:
                st.warning(f"⚠️ No data found for {view_start} to {view_end}")
        
        # Identify unknown customers for debugging
        if 'customer_name' in df.columns:
            unknown_customers = df[df["customer_name"] == "Unknown Customer"]["customer_id"].unique()
            if len(unknown_customers) > 0:
                with st.expander("⚠️ Unknown Customers Found", expanded=True):
                    st.write(f"Found {len(unknown_customers)} unknown customer IDs:")
                    unknown_df = pd.DataFrame({
                        "Customer ID": unknown_customers,
                        "Transactions": [df[df["customer_id"] == cid]["bill_number"].nunique() for cid in unknown_customers],
                        "Total Sales": [
                            (
                                df[df["customer_id"] == cid]
                                .groupby("bill_number", as_index=False)["signed_net"]
                                .first()["signed_net"]
                                .sum()
                            )
                            if "signed_net" in df.columns and "bill_number" in df.columns
                            else df[df["customer_id"] == cid]["line_total"].sum()
                            for cid in unknown_customers
                        ]
                    })
                    st.dataframe(unknown_df, use_container_width=True)
                    
                    st.write("**Manual Customer Mapping:**")
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        selected_unknown = st.selectbox("Select Unknown Customer ID:", unknown_customers)
                    with col2:
                        manual_name = st.text_input("Enter Customer Name:", key=f"manual_name_{selected_unknown}")
                    
                    if st.button("➕ Add Customer Name", key=f"add_{selected_unknown}"):
                        if manual_name and manual_name.strip():
                            customer_map[selected_unknown] = manual_name.strip()
                            st.session_state.customer_map = customer_map
                            df.loc[df["customer_id"] == selected_unknown, "customer_name"] = manual_name.strip()
                            st.success(f"✅ Mapped {selected_unknown[:8]}... to '{manual_name}'")
                            st.rerun()
                        else:
                            st.error("Please enter a customer name")
                    
                    st.caption("💡 These customer IDs exist in receipts but not in your customer list. They might be:")
                    st.caption("• Deleted customers")
                    st.caption("• Customers from a different store") 
                    st.caption("• Test/guest transactions")
                    st.caption("• Customers created after your last API fetch")
        else:
            df["customer_name"] = "No Customer Data"

        # --- Sidebar filters ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("Filters")
        
        # Location filter
        if "location" in df.columns:
            unique_locations = sorted(df["location"].dropna().unique())
            selected_location = st.sidebar.selectbox("Location", ["All"] + list(unique_locations))
            if selected_location != "All":
                df = df[df["location"] == selected_location]
        
        unique_stores = sorted(df["store_id"].dropna().unique())
        selected_store = st.sidebar.selectbox("Store", ["All"] + list(unique_stores))
        if selected_store != "All":
            df = df[df["store_id"] == selected_store]

        # Use payment_name (readable) if available, otherwise fall back to bill_type
        if "payment_name" in df.columns:
            unique_payments = sorted(df["payment_name"].dropna().unique())
            selected_payment = st.sidebar.selectbox("Payment Type", ["All"] + list(unique_payments))
            if selected_payment != "All":
                df = df[df["payment_name"] == selected_payment]
        else:
            unique_payments = sorted(df["bill_type"].dropna().unique())
            selected_payment = st.sidebar.selectbox("Payment Type", ["All"] + list(unique_payments))
            if selected_payment != "All":
                df = df[df["bill_type"] == selected_payment]

        # Canonical analysis frames:
        # - line_df: one row per line item
        # - receipt_df: one row per receipt (aggregated from line_df)
        line_df = df.copy()

        def build_receipt_frame(source_df):
            receipt_columns = [
                "day",
                "bill_number",
                "receipt_type",
                "signed_net",
                "receipt_discount",
                "customer_id",
                "customer_name",
                "store_id",
                "payment_name",
                "location",
                "date",
            ]
            if source_df.empty or "bill_number" not in source_df.columns:
                return pd.DataFrame(columns=receipt_columns)

            group_cols = ["bill_number"]
            if "day" in source_df.columns:
                group_cols.insert(0, "day")

            agg_map = {}
            for col in [
                "date",
                "receipt_type",
                "signed_net",
                "receipt_discount",
                "customer_id",
                "customer_name",
                "store_id",
                "payment_name",
                "location",
                "receipt_total",
            ]:
                if col in source_df.columns:
                    agg_map[col] = "first"

            receipt_df_local = source_df.groupby(group_cols, as_index=False).agg(agg_map)

            if "receipt_discount" in receipt_df_local.columns:
                receipt_df_local["receipt_discount"] = receipt_df_local["receipt_discount"].fillna(0)

            if (
                "signed_net" not in receipt_df_local.columns
                and {"receipt_total", "receipt_discount", "receipt_type"}.issubset(receipt_df_local.columns)
            ):
                receipt_net = (
                    receipt_df_local["receipt_total"].fillna(0)
                    - receipt_df_local["receipt_discount"].fillna(0)
                )
                is_refund = receipt_df_local["receipt_type"].astype(str).str.lower().eq("refund")
                receipt_df_local["signed_net"] = receipt_net.where(~is_refund, -receipt_net)
            elif "signed_net" not in receipt_df_local.columns and "line_total" in source_df.columns:
                line_sales = source_df.groupby(group_cols, as_index=False)["line_total"].sum()
                receipt_df_local = receipt_df_local.merge(line_sales, on=group_cols, how="left")
                receipt_df_local["signed_net"] = receipt_df_local["line_total"].fillna(0)
                receipt_df_local = receipt_df_local.drop(columns=["line_total"], errors="ignore")

            if "day" not in receipt_df_local.columns:
                receipt_df_local["day"] = None

            for col in receipt_columns:
                if col not in receipt_df_local.columns:
                    receipt_df_local[col] = None

            return receipt_df_local[receipt_columns]

        def compute_sales_kpis(receipt_frame, line_frame):
            """Trusted KPI source: money from receipt grain, quantity from line grain."""
            out = {
                "total_sales": 0.0,
                "total_items": 0.0,
                "unique_customers": 0,
                "transactions": 0,
            }
            if receipt_frame is None or line_frame is None:
                return out
            if not receipt_frame.empty and "signed_net" in receipt_frame.columns:
                out["total_sales"] = float(pd.to_numeric(receipt_frame["signed_net"], errors="coerce").fillna(0).sum())
            elif "line_total" in line_frame.columns:
                out["total_sales"] = float(pd.to_numeric(line_frame["line_total"], errors="coerce").fillna(0).sum())
            if "quantity" in line_frame.columns:
                out["total_items"] = float(pd.to_numeric(line_frame["quantity"], errors="coerce").fillna(0).sum())
            if "customer_id" in receipt_frame.columns:
                out["unique_customers"] = int(receipt_frame["customer_id"].dropna().nunique())
            elif "customer_id" in line_frame.columns:
                out["unique_customers"] = int(line_frame["customer_id"].dropna().nunique())
            if "bill_number" in receipt_frame.columns:
                out["transactions"] = int(receipt_frame["bill_number"].dropna().nunique())
            return out

        def build_reconciliation_monitor(receipt_frame, line_frame, tolerance=0.01):
            """
            Cross-check receipt totals against an independently rebuilt receipt frame
            from line-level rows. Any mismatch indicates aggregation drift.
            """
            if receipt_frame is None or line_frame is None or receipt_frame.empty:
                return {"ok": True, "message": "No data available for monitor."}
            rebuilt = build_receipt_frame(line_frame)
            r_sales = float(pd.to_numeric(receipt_frame.get("signed_net"), errors="coerce").fillna(0).sum())
            b_sales = float(pd.to_numeric(rebuilt.get("signed_net"), errors="coerce").fillna(0).sum())
            r_disc = float(pd.to_numeric(receipt_frame.get("receipt_discount"), errors="coerce").fillna(0).sum())
            b_disc = float(pd.to_numeric(rebuilt.get("receipt_discount"), errors="coerce").fillna(0).sum())
            r_txn = int(receipt_frame["bill_number"].dropna().nunique()) if "bill_number" in receipt_frame.columns else 0
            b_txn = int(rebuilt["bill_number"].dropna().nunique()) if "bill_number" in rebuilt.columns else 0
            sales_gap = r_sales - b_sales
            disc_gap = r_disc - b_disc
            txn_gap = r_txn - b_txn
            ok = abs(sales_gap) <= tolerance and abs(disc_gap) <= tolerance and txn_gap == 0
            return {
                "ok": ok,
                "sales_receipt": r_sales,
                "sales_rebuilt": b_sales,
                "sales_gap": sales_gap,
                "discount_receipt": r_disc,
                "discount_rebuilt": b_disc,
                "discount_gap": disc_gap,
                "txn_receipt": r_txn,
                "txn_rebuilt": b_txn,
                "txn_gap": txn_gap,
            }

        receipt_df = build_receipt_frame(line_df)
        df = line_df

        # --- KPI Cards ---
        kpi_summary = compute_sales_kpis(receipt_df, line_df)
        total_sales = kpi_summary["total_sales"]
        total_items = kpi_summary["total_items"]
        unique_customers = kpi_summary["unique_customers"]
        
        # Calculate bags per day
        if 'view_start_date' in st.session_state and 'view_end_date' in st.session_state:
            start_date = st.session_state.view_start_date
            end_date = st.session_state.view_end_date
            days_in_period = (end_date - start_date).days + 1
            bags_per_day = total_items / days_in_period if days_in_period > 0 else 0
        else:
            days_in_period = 1
            bags_per_day = total_items

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Sales", f"฿{total_sales:,.0f}")
        col2.metric("Items Sold", f"{total_items:,.0f}")
        col3.metric("Unique Customers", f"{unique_customers}")
        col4.metric("Bags / Day", f"{bags_per_day:.1f}", help=f"Average bags sold per day over {days_in_period} days")

        with st.expander("Aggregation Integrity Monitor", expanded=False):
            monitor = build_reconciliation_monitor(receipt_df, line_df)
            if monitor.get("ok"):
                st.success("Receipt-grain totals are consistent with rebuilt line->receipt totals.")
            else:
                st.error("Aggregation mismatch detected. Review before using totals for invoicing.")
            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric("Sales Gap", f"{monitor.get('sales_gap', 0):,.2f}")
            mcol2.metric("Discount Gap", f"{monitor.get('discount_gap', 0):,.2f}")
            mcol3.metric("Txn Gap", f"{monitor.get('txn_gap', 0)}")
            st.caption("Expected normal state: all three gaps are 0.")

        st.markdown("---")

        # --- Render selected tab content ---
        if st.session_state.selected_tab == get_text("daily_sales"):
            st.subheader(get_text("daily_sales_analysis"))
            
            # Use canonical receipt-level frame for sales KPIs/charts.
            receipt_day_sales = receipt_df.copy()
            
            # === ENHANCED KPI CARDS ===
            st.markdown(f"### {get_text('key_metrics')}")
            
            # Calculate daily aggregations using receipt-level signed net
            if receipt_day_sales is not None:
                # Sales and transaction/customer counts from receipt-level data
                sales_agg = receipt_day_sales.groupby("day", as_index=False).agg(
                    signed_net=("signed_net", "sum"),
                    bill_number=("bill_number", "nunique"),
                    customer_id=("customer_id", "nunique"),
                )
                # Items sold remains line-level quantity aggregation
                qty_agg = line_df.groupby("day", as_index=False).agg(quantity=("quantity", "sum"))
                daily_agg = sales_agg.merge(qty_agg, on="day", how="left")
                daily_agg = daily_agg[["day", "signed_net", "quantity", "bill_number", "customer_id"]]
                daily_agg.columns = ["day", "total_sales", "items", "transactions", "customers"]
            else:
                daily_agg = line_df.groupby("day").agg({
                    "line_total": "sum",
                    "quantity": "sum", 
                    "bill_number": "nunique",
                    "customer_id": "nunique"
                }).reset_index()
                daily_agg.columns = ["day", "total_sales", "items", "transactions", "customers"]
            
            # Calculate metrics for display
            total_days = len(daily_agg)
            avg_daily_sales = daily_agg["total_sales"].mean()
            avg_items_per_day = daily_agg["items"].mean()
            avg_transactions_per_day = daily_agg["transactions"].mean()
            avg_customers_per_day = daily_agg["customers"].mean()
            # Average transaction value based on receipt-level net (exclude refunds)
            if "signed_net" in receipt_day_sales.columns and "receipt_type" in receipt_day_sales.columns:
                per_receipt = receipt_day_sales[["bill_number", "receipt_type", "signed_net"]].copy()
                per_receipt = per_receipt[per_receipt["receipt_type"].str.lower() != "refund"]
                avg_transaction_value = per_receipt["signed_net"].mean() if not per_receipt.empty else 0
            elif "line_total" in df.columns:
                avg_transaction_value = line_df.groupby("bill_number")["line_total"].sum().mean()
            else:
                avg_transaction_value = 0
            
            # Calculate growth (last day vs previous day)
            if len(daily_agg) >= 2:
                last_day_sales = daily_agg.iloc[-1]["total_sales"]
                prev_day_sales = daily_agg.iloc[-2]["total_sales"]
                sales_delta = ((last_day_sales - prev_day_sales) / prev_day_sales * 100) if prev_day_sales > 0 else 0
                
                last_day_trans = daily_agg.iloc[-1]["transactions"]
                prev_day_trans = daily_agg.iloc[-2]["transactions"]
                trans_delta = ((last_day_trans - prev_day_trans) / prev_day_trans * 100) if prev_day_trans > 0 else 0
            else:
                sales_delta = 0
                trans_delta = 0
            
            # Display KPI cards
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    get_text('avg_daily_sales'), 
                    f"฿{avg_daily_sales:,.0f}",
                    delta=f"{sales_delta:+.1f}%" if sales_delta != 0 else None,
                    help="Average sales per day in selected period"
                )
            
            with col2:
                st.metric(
                    get_text('avg_transaction'), 
                    f"฿{avg_transaction_value:,.0f}",
                    delta=" ",
                    delta_color="off",
                    help="Average value per transaction"
                )
            
            with col3:
                st.metric(
                    get_text('avg_items_per_day'), 
                    f"{avg_items_per_day:,.0f}",
                    delta=" ",
                    delta_color="off",
                    help="Average items sold per day"
                )
            
            with col4:
                st.metric(
                    get_text('avg_customers_per_day'), 
                    f"{avg_customers_per_day:,.0f}",
                    delta=f"{trans_delta:+.1f}%" if trans_delta != 0 else None,
                    help="Average unique customers per day"
                )
            
            st.markdown("---")
            
            # === DAILY SALES CHARTS ===
            st.markdown(f"### {get_text('sales_overview')}")
            
            # Bar chart - Full width using receipt-level signed net
            if receipt_day_sales is not None:
                daily_sales = (
                    receipt_day_sales.groupby("day", as_index=False)["signed_net"]
                    .sum()
                    .rename(columns={"signed_net": "total"})
                )
            else:
                daily_sales = line_df.groupby("day")["line_total"].sum().reset_index().rename(columns={"line_total":"total"})
            
            fig = px.bar(daily_sales, x="day", y="total", title="Daily Sales Trend (Net Sales)", 
                        text_auto=True,
                        labels={"total": "Total Sales", "day": "Date"})
            fig.update_traces(textposition='outside', marker_color="#3b82f6")
            fig.update_layout(**CHART_LAYOUT, showlegend=False, height=450)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show discount information if available
            if 'receipt_discount' in receipt_day_sales.columns:
                total_discounts = receipt_day_sales["receipt_discount"].fillna(0).sum()
                if total_discounts > 0:
                    st.info(f"💰 **Total Discounts Applied:** ฿{total_discounts:,.2f}")
                    
                    # Show daily discount breakdown
                    daily_discounts = receipt_day_sales.groupby("day")["receipt_discount"].sum().reset_index()
                    daily_discounts.columns = ["day", "discounts"]
                    
                    if daily_discounts["discounts"].sum() > 0:
                        st.markdown(f"#### {get_text('daily_discounts')}")
                        fig_discounts = px.bar(daily_discounts, x="day", y="discounts", 
                                             title="Daily Discounts Applied",
                                             text_auto=True)
                        fig_discounts.update_traces(textposition='outside', marker_color="#ef4444")
                        fig_discounts.update_layout(**CHART_LAYOUT, showlegend=False, height=350)
                        st.plotly_chart(fig_discounts, use_container_width=True)
                else:
                    st.info("ℹ️ **No discounts found in the data**")
            
            # Line chart with hover details - receipt-level sales totals
            if receipt_day_sales is not None:
                sales_details = receipt_day_sales.groupby("day", as_index=False).agg(
                    signed_net=("signed_net", "sum"),
                    bill_number=("bill_number", "nunique"),
                )
                qty_details = line_df.groupby("day", as_index=False).agg(quantity=("quantity", "sum"))
                daily_details = sales_details.merge(qty_details, on="day", how="left")
                daily_details = daily_details.rename(
                    columns={
                        "day": "Date",
                        "signed_net": "Total Sales",
                        "quantity": "Items Sold",
                        "bill_number": "Transactions",
                    }
                )
            else:
                daily_details = line_df.groupby("day").agg({
                    "line_total": "sum",
                    "quantity": "sum",
                    "bill_number": "nunique"
                }).reset_index().rename(columns={"line_total":"Total Sales"})
                daily_details.columns = ["Date", "Total Sales", "Items Sold", "Transactions"]
            fig2 = px.line(daily_details, x="Date", y="Total Sales", 
                          title="Sales Trend Line",
                          markers=True,
                          hover_data=["Items Sold", "Transactions"])
            fig2.update_traces(line_color='#3b82f6', line_width=2, marker=dict(size=5))
            fig2.update_layout(**CHART_LAYOUT, height=400)
            st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("---")
            
            # === DAY OF WEEK ANALYSIS ===
            st.markdown(f"### {get_text('day_of_week_analysis')}")
            
            # Add day-of-week dimensions from receipt-level data.
            df_temp = receipt_day_sales.copy()
            df_temp["day_date"] = pd.to_datetime(df_temp["day"])
            df_temp["day_of_week"] = df_temp["day_date"].dt.day_name()
            df_temp["weekday_num"] = df_temp["day_date"].dt.dayofweek

            if 'signed_net' in df_temp.columns:
                dow_sales = df_temp.groupby(["day_of_week", "weekday_num"], as_index=False).agg(
                    total_sales=("signed_net", "sum"),
                    days_count=("day", "nunique"),
                    transactions=("bill_number", "nunique"),
                    customers=("customer_id", "nunique"),
                )
                qty_temp = line_df.copy()
                qty_temp["day_date"] = pd.to_datetime(qty_temp["day"])
                qty_temp["day_of_week"] = qty_temp["day_date"].dt.day_name()
                qty_temp["weekday_num"] = qty_temp["day_date"].dt.dayofweek
                dow_qty = qty_temp.groupby(["day_of_week", "weekday_num"], as_index=False).agg(items=("quantity", "sum"))
                dow_sales = dow_sales.merge(dow_qty, on=["day_of_week", "weekday_num"], how="left").fillna({"items": 0})
                dow_sales["avg_sales"] = dow_sales["total_sales"] / dow_sales["days_count"].replace(0, pd.NA)
            else:
                dow_sales = line_df.copy()
                dow_sales["day_date"] = pd.to_datetime(dow_sales["day"])
                dow_sales["day_of_week"] = dow_sales["day_date"].dt.day_name()
                dow_sales["weekday_num"] = dow_sales["day_date"].dt.dayofweek
                dow_sales = dow_sales.groupby(["day_of_week", "weekday_num"], as_index=False).agg(
                    total_sales=("line_total", "sum"),
                    avg_sales=("line_total", "mean"),
                    days_count=("day", "nunique"),
                    transactions=("bill_number", "nunique"),
                    customers=("customer_id", "nunique"),
                    items=("quantity", "sum"),
                )
            
            # Sort by weekday (Monday=0, Sunday=6)
            dow_sales = dow_sales.sort_values('weekday_num')
            
            # Calculate average per occurrence
            dow_sales['avg_per_occurrence'] = dow_sales['total_sales'] / dow_sales['days_count']
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                best_day = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmax(), 'day_of_week']
                best_day_sales = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmax(), 'avg_per_occurrence']
                st.metric("Best Day", best_day, f"฿{best_day_sales:,.0f} avg")
            
            with col2:
                worst_day = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmin(), 'day_of_week']
                worst_day_sales = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmin(), 'avg_per_occurrence']
                st.metric("Slowest Day", worst_day, f"฿{worst_day_sales:,.0f} avg")
            
            with col3:
                weekend_days = dow_sales[dow_sales['day_of_week'].isin(['Saturday', 'Sunday'])]
                weekday_days = dow_sales[~dow_sales['day_of_week'].isin(['Saturday', 'Sunday'])]
                weekend_avg = weekend_days['avg_per_occurrence'].mean() if len(weekend_days) > 0 else 0
                weekday_avg = weekday_days['avg_per_occurrence'].mean() if len(weekday_days) > 0 else 0
                diff_pct = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0
                st.metric("Weekend vs Weekday", f"{diff_pct:+.1f}%", 
                         f"Weekend: ฿{weekend_avg:,.0f}")
            
            # Charts
            col1, col2 = st.columns(2)
            
            with col1:
                # Bar chart - Average sales by day of week
                fig_dow = px.bar(
                    dow_sales, 
                    x='day_of_week', 
                    y='avg_per_occurrence',
                    title='Average Sales by Day of Week',
                    labels={'day_of_week': 'Day', 'avg_per_occurrence': 'Average Sales'},
                    text_auto=True
                )
                fig_dow.update_traces(texttemplate='฿%{y:,.0f}', textposition='outside', marker_color="#3b82f6")
                fig_dow.update_layout(**CHART_LAYOUT, showlegend=False, xaxis_tickangle=-45)
                st.plotly_chart(fig_dow, use_container_width=True)
            
            with col2:
                # Grouped bar chart - Multiple metrics
                fig_dow_multi = px.bar(
                    dow_sales,
                    x='day_of_week',
                    y=['transactions', 'customers'],
                    title='Transactions & Customers by Day',
                    labels={'value': 'Count', 'day_of_week': 'Day', 'variable': 'Metric'},
                    barmode='group'
                )
                fig_dow_multi.update_layout(**CHART_LAYOUT, xaxis_tickangle=-45, legend_title_text='')
                st.plotly_chart(fig_dow_multi, use_container_width=True)
            
            # Detailed table
            with st.expander("Detailed Day of Week Statistics"):
                display_dow = dow_sales[['day_of_week', 'total_sales', 'avg_per_occurrence', 'transactions', 'customers', 'items', 'days_count']].copy()
                display_dow.columns = ['Day', 'Total Sales', 'Avg per Day', 'Transactions', 'Customers', 'Items Sold', 'Days in Period']
                display_dow['Total Sales'] = display_dow['Total Sales'].apply(lambda x: f"฿{x:,.0f}")
                display_dow['Avg per Day'] = display_dow['Avg per Day'].apply(lambda x: f"฿{x:,.0f}")
                
                st.dataframe(display_dow, use_container_width=True, hide_index=True)
            
            # Insights
            st.caption(f"""**{best_day}** is busiest (฿{best_day_sales:,.0f} avg) · **{worst_day}** is slowest · Weekend sales {diff_pct:+.1f}% vs weekdays · {total_days} days analyzed""")

        elif st.session_state.selected_tab == get_text("by_location"):
            st.subheader(get_text("sales_by_location"))
            
            if "location" in line_df.columns and not line_df["location"].isna().all():
                # Location sales summary
                if "signed_net" in receipt_df.columns:
                    sales_by_location = (
                        receipt_df.groupby("location", as_index=False).agg(
                            **{
                                "Total Sales": ("signed_net", "sum"),
                                "Transactions": ("bill_number", "nunique"),
                                "Unique Customers": ("customer_id", "nunique"),
                            }
                        )
                    )
                else:
                    sales_by_location = (
                        line_df.groupby("location", as_index=False).agg(
                            **{
                                "Total Sales": ("line_total", "sum"),
                                "Transactions": ("bill_number", "nunique"),
                                "Unique Customers": ("customer_id", "nunique"),
                            }
                        )
                    )
                items_by_location = (
                    line_df.groupby("location", as_index=False)["quantity"].sum()
                    .rename(columns={"location": "Location", "quantity": "Items Sold"})
                )
                location_sales = sales_by_location.rename(columns={"location": "Location"}).merge(
                    items_by_location,
                    on="Location",
                    how="left",
                )
                location_sales = location_sales.sort_values("Total Sales", ascending=False)
                
                # Bar chart
                fig = px.bar(location_sales, x="Total Sales", y="Location",
                            orientation="h",
                            title="Sales by Location (ประเภท)",
                            color="Total Sales",
                            color_continuous_scale="Teal",
                            text_auto=True)
                apply_chart_layout(fig, yaxis={'categoryorder':'total ascending'}, height=600)
                st.plotly_chart(fig, use_container_width=True)
                
                # Pie chart
                col1, col2 = st.columns(2)
                with col1:
                    fig_pie = px.pie(location_sales, names="Location", values="Total Sales",
                                    title="Sales Distribution by Location",
                                    hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with col2:
                    fig_pie2 = px.pie(location_sales, names="Location", values="Transactions",
                                     title="Transaction Count by Location",
                                     hole=0.4,
                                     color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_pie2, use_container_width=True)
                
                # Location details table
                st.subheader(get_heading("location_performance_details"))
                location_sales["Avg Transaction"] = location_sales["Total Sales"] / location_sales["Transactions"]
                location_sales["Avg Items/Transaction"] = location_sales["Items Sold"] / location_sales["Transactions"]
                st.dataframe(location_sales.sort_values("Total Sales", ascending=False), 
                           use_container_width=True, hide_index=True)
                
                # Location trends over time
                st.subheader(get_heading("location_trends_over_time"))
                if "signed_net" in receipt_df.columns:
                    location_daily = receipt_df.groupby(["day", "location"])["signed_net"].sum().reset_index().rename(columns={"signed_net":"total"})
                else:
                    location_daily = line_df.groupby(["day", "location"])["line_total"].sum().reset_index().rename(columns={"line_total":"total"})

                # Use 7-day moving average to smooth daily volatility by location.
                location_daily["day"] = pd.to_datetime(location_daily["day"], errors="coerce")
                location_daily = location_daily.dropna(subset=["day"]).sort_values(["location", "day"])
                location_daily["ma_7d"] = (
                    location_daily
                    .groupby("location")["total"]
                    .transform(lambda s: s.rolling(window=7, min_periods=1).mean())
                )

                fig_trend = px.line(
                    location_daily,
                    x="day",
                    y="ma_7d",
                    color="location",
                    title="7-Day Moving Average Sales Trend by Location (Net Sales)",
                    markers=True,
                    labels={"ma_7d": "7-Day Avg Sales", "day": "Date"},
                )
                st.plotly_chart(fig_trend, use_container_width=True)

                # Alert if latest 7-day average declines by >30% vs previous 7-day window.
                decline_alerts = []
                for loc, loc_df in location_daily.groupby("location"):
                    loc_df = loc_df.sort_values("day")
                    if len(loc_df) < 14:
                        continue
                    latest_window = loc_df.tail(7)["total"]
                    previous_window = loc_df.tail(14).head(7)["total"]
                    latest_avg = float(latest_window.mean())
                    previous_avg = float(previous_window.mean())
                    if previous_avg <= 0:
                        continue
                    decline_pct = ((latest_avg - previous_avg) / previous_avg) * 100
                    if decline_pct <= -30:
                        decline_alerts.append(
                            {
                                "Location": loc,
                                "Previous 7d Avg": previous_avg,
                                "Latest 7d Avg": latest_avg,
                                "Change %": decline_pct,
                            }
                        )

                if decline_alerts:
                    alert_df = pd.DataFrame(decline_alerts).sort_values("Change %")
                    st.error("⚠️ Sales decline alert: one or more locations dropped more than 30% in the last week.")
                    st.dataframe(alert_df, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No location has declined by more than 30% in the last 7-day window.")
                
                st.markdown("---")
                
                # === PEAK HOURS ANALYSIS ===
                st.subheader(get_heading("peak_hours_by_location"))
                
                # Extract hour from timestamp
                df_hours_line = line_df.copy()
                df_hours_line['datetime'] = pd.to_datetime(df_hours_line['date'])
                df_hours_line['hour'] = df_hours_line['datetime'].dt.hour
                df_hours_receipt = receipt_df.copy()
                df_hours_receipt['datetime'] = pd.to_datetime(df_hours_receipt['date'])
                df_hours_receipt['hour'] = df_hours_receipt['datetime'].dt.hour
                
                # Location selector for peak hours
                peak_location_list = ["All Locations"] + sorted(line_df["location"].dropna().unique().tolist())
                selected_peak_location = st.selectbox(
                    "📍 Select Location for Peak Hours Analysis:",
                    peak_location_list,
                    key="peak_hours_location"
                )
                
                # Filter data
                if selected_peak_location == "All Locations":
                    hourly_receipt = df_hours_receipt.copy()
                    hourly_line = df_hours_line.copy()
                    analysis_title = "All Locations"
                else:
                    hourly_receipt = df_hours_receipt[df_hours_receipt["location"] == selected_peak_location].copy()
                    hourly_line = df_hours_line[df_hours_line["location"] == selected_peak_location].copy()
                    analysis_title = selected_peak_location
                
                if not hourly_receipt.empty:
                    # Aggregate by hour
                    if "signed_net" in hourly_receipt.columns:
                        hourly_sales = hourly_receipt.groupby('hour').agg({
                            'signed_net': 'sum',
                            'bill_number': 'nunique',
                            'customer_id': 'nunique',
                        }).reset_index()
                    else:
                        hourly_sales = hourly_receipt.groupby('hour').agg({
                            'line_total': 'sum',
                            'bill_number': 'nunique',
                            'customer_id': 'nunique',
                        }).reset_index()
                    hourly_items = hourly_line.groupby("hour", as_index=False)["quantity"].sum()
                    hourly_items.columns = ["hour", "quantity"]
                    hourly_sales = hourly_sales.merge(hourly_items, on="hour", how="left").fillna({"quantity": 0})
                    
                    # Calculate occurrences before renaming columns
                    hour_counts = hourly_receipt.groupby('hour').size().reset_index(name='occurrences')
                    hourly_sales = hourly_sales.merge(hour_counts, on='hour')
                    
                    # Now rename columns after merge
                    hourly_sales.columns = ['Hour', 'Sales', 'Transactions', 'Customers', 'Items', 'occurrences']
                    hourly_sales['Avg Sales'] = hourly_sales['Sales'] / hourly_sales['occurrences']
                    hourly_sales['Avg Transactions'] = hourly_sales['Transactions'] / hourly_sales['occurrences']
                    
                    # Identify peak hours
                    peak_hour = hourly_sales.loc[hourly_sales['Avg Sales'].idxmax(), 'Hour']
                    peak_sales = hourly_sales.loc[hourly_sales['Avg Sales'].idxmax(), 'Avg Sales']
                    slowest_hour = hourly_sales.loc[hourly_sales['Avg Sales'].idxmin(), 'Hour']
                    slowest_sales = hourly_sales.loc[hourly_sales['Avg Sales'].idxmin(), 'Avg Sales']
                    
                    # Display peak hour metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "🔥 Peak Hour", 
                            f"{peak_hour:02d}:00",
                            f"฿{peak_sales:,.0f} avg"
                        )
                    
                    with col2:
                        st.metric(
                            "😴 Slowest Hour", 
                            f"{slowest_hour:02d}:00",
                            f"฿{slowest_sales:,.0f} avg"
                        )
                    
                    with col3:
                        # Morning vs Afternoon vs Evening
                        morning = hourly_sales[hourly_sales['Hour'] < 12]['Avg Sales'].mean()
                        afternoon = hourly_sales[(hourly_sales['Hour'] >= 12) & (hourly_sales['Hour'] < 18)]['Avg Sales'].mean()
                        evening = hourly_sales[hourly_sales['Hour'] >= 18]['Avg Sales'].mean()
                        
                        best_period = max([('Morning', morning), ('Afternoon', afternoon), ('Evening', evening)], key=lambda x: x[1])
                        st.metric(
                            "⏰ Best Period",
                            best_period[0],
                            f"฿{best_period[1]:,.0f} avg"
                        )
                    
                    with col4:
                        total_hours_active = len(hourly_sales)
                        st.metric(
                            "📊 Active Hours",
                            f"{total_hours_active} hours",
                            f"of {24} total"
                        )
                    
                    # Charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Line chart - Sales by hour
                        fig_hourly = px.line(
                            hourly_sales,
                            x='Hour',
                            y='Avg Sales',
                            title=f'Average Sales by Hour - {analysis_title}',
                            markers=True,
                            labels={'Hour': 'Hour of Day (24h)', 'Avg Sales': 'Average Sales (฿)'}
                        )
                        fig_hourly.update_traces(line_color='#FF6B6B', line_width=3, marker_size=8)
                        fig_hourly.update_xaxes(dtick=1, range=[-0.5, 23.5])
                        fig_hourly.add_hline(
                            y=hourly_sales['Avg Sales'].mean(),
                            line_dash="dash",
                            line_color="gray",
                            annotation_text="Average"
                        )
                        st.plotly_chart(fig_hourly, use_container_width=True)
                    
                    with col2:
                        # Bar chart - Transactions by hour
                        fig_trans = px.bar(
                            hourly_sales,
                            x='Hour',
                            y='Avg Transactions',
                            title=f'Average Transactions by Hour - {analysis_title}',
                            labels={'Hour': 'Hour of Day (24h)', 'Avg Transactions': 'Avg Transactions'},
                            color='Avg Transactions',
                            color_continuous_scale='Viridis'
                        )
                        fig_trans.update_xaxes(dtick=1, range=[-0.5, 23.5])
                        st.plotly_chart(fig_trans, use_container_width=True)
                    
                    # Detailed hourly breakdown
                    with st.expander("📋 Detailed Hourly Statistics"):
                        # Format for display
                        display_hourly = hourly_sales[['Hour', 'Sales', 'Avg Sales', 'Transactions', 'Avg Transactions', 'Customers', 'Items', 'occurrences']].copy()
                        display_hourly['Hour'] = display_hourly['Hour'].apply(lambda x: f"{x:02d}:00")
                        display_hourly['Sales'] = display_hourly['Sales'].apply(lambda x: f"฿{x:,.0f}")
                        display_hourly['Avg Sales'] = display_hourly['Avg Sales'].apply(lambda x: f"฿{x:,.0f}")
                        display_hourly.columns = ['Hour', 'Total Sales', 'Avg per Occurrence', 'Total Trans', 'Avg Trans', 'Customers', 'Items', 'Days with Data']
                        
                        st.dataframe(display_hourly, use_container_width=True, hide_index=True)
                    
                    # Time period analysis
                    st.markdown("##### 📊 Time Period Analysis")
                    
                    # Define periods
                    periods = {
                        '🌅 Early Morning (6-9)': hourly_sales[(hourly_sales['Hour'] >= 6) & (hourly_sales['Hour'] < 9)]['Avg Sales'].sum(),
                        '☀️ Morning (9-12)': hourly_sales[(hourly_sales['Hour'] >= 9) & (hourly_sales['Hour'] < 12)]['Avg Sales'].sum(),
                        '🌤️ Afternoon (12-15)': hourly_sales[(hourly_sales['Hour'] >= 12) & (hourly_sales['Hour'] < 15)]['Avg Sales'].sum(),
                        '🌆 Late Afternoon (15-18)': hourly_sales[(hourly_sales['Hour'] >= 15) & (hourly_sales['Hour'] < 18)]['Avg Sales'].sum(),
                        '🌃 Evening (18-21)': hourly_sales[(hourly_sales['Hour'] >= 18) & (hourly_sales['Hour'] < 21)]['Avg Sales'].sum(),
                        '🌙 Night (21-24)': hourly_sales[(hourly_sales['Hour'] >= 21)]['Avg Sales'].sum(),
                    }
                    
                    period_df = pd.DataFrame(list(periods.items()), columns=['Period', 'Sales'])
                    period_df = period_df[period_df['Sales'] > 0]  # Only show periods with data
                    
                    if not period_df.empty:
                        fig_periods = px.bar(
                            period_df,
                            x='Sales',
                            y='Period',
                            orientation='h',
                            title=f'Sales by Time Period - {analysis_title}',
                            color='Sales',
                            color_continuous_scale='Sunset',
                            text_auto=True
                        )
                        fig_periods.update_traces(texttemplate='฿%{x:,.0f}', textposition='outside')
                        apply_chart_layout(fig_periods, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_periods, use_container_width=True)
                    
                    # Insights
                    st.info(f"""
                    **💡 Peak Hours Insights for {analysis_title}:**
                    - **Peak hour:** {peak_hour:02d}:00 with average sales of ฿{peak_sales:,.0f}
                    - **Slowest hour:** {slowest_hour:02d}:00 with average sales of ฿{slowest_sales:,.0f}
                    - **Best period:** {best_period[0]} (฿{best_period[1]:,.0f} average)
                    - **Recommendation:** Schedule more staff during {peak_hour:02d}:00-{peak_hour+2:02d}:00
                    """)
                else:
                    st.warning(f"⚠️ No data available for {selected_peak_location}")
                
            else:
                st.warning("⚠️ No location data available in receipts")

        elif st.session_state.selected_tab == get_text("by_product"):
            st.subheader(get_text("product_analysis"))
            
            # === PRODUCT CATEGORIZATION ===
            # Initialize manual categorizations from database if not exists in session state
            if 'manual_categories' not in st.session_state:
                st.session_state.manual_categories = db.get_manual_categories()
            
            # Categorize products into 3 main types
            def categorize_product(product_name):
                """Categorize products into main 3 types"""
                return categorize_ice_product_name(
                    product_name,
                    manual_categories=st.session_state.manual_categories,
                )
            
            # Apply categorization
            df_products = line_df.copy()
            df_products['product_category'] = df_products['item'].apply(categorize_product)
            
            # Aggregate by category
            category_sales = df_products.groupby('product_category').agg({
                'line_total': 'sum',
                'quantity': 'sum',
                'bill_number': 'nunique',
                'item': 'count'
            }).reset_index()
            category_sales.columns = ['Category', 'Total Sales', 'Quantity', 'Transactions', 'Items Sold']
            category_sales = category_sales.sort_values('Total Sales', ascending=False)
            
            # Calculate percentages
            total_sales_sum = category_sales['Total Sales'].sum()
            category_sales['Sales %'] = (category_sales['Total Sales'] / total_sales_sum * 100).round(2)
            
            # === SUMMARY METRICS ===
            st.markdown(f"### {get_text('product_category_summary')}")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                main_categories = category_sales[~category_sales['Category'].str.contains('อื่นๆ')]
                main_sales = main_categories['Total Sales'].sum()
                st.metric("Main Products Sales", f"฿{main_sales:,.0f}", 
                         f"{(main_sales/total_sales_sum*100):.1f}% of total")
            
            with col2:
                top_category = category_sales.iloc[0]['Category']
                top_sales = category_sales.iloc[0]['Total Sales']
                st.metric("Top Category", top_category.split()[1], 
                         f"฿{top_sales:,.0f}")
            
            with col3:
                total_quantity = category_sales['Quantity'].sum()
                st.metric("Total Quantity", f"{total_quantity:,.0f} units")
            
            with col4:
                avg_price = total_sales_sum / total_quantity if total_quantity > 0 else 0
                st.metric("💵 Avg Unit Price", f"฿{avg_price:,.2f}")
            
            st.markdown("---")
            
            # === PIE CHART & SUMMARY TABLE ===
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown(f"#### {get_text('sales_distribution')}")
                
                # Pie chart
                fig_pie = px.pie(
                    category_sales,
                    values='Total Sales',
                    names='Category',
                    title='Sales by Product Category',
                    hole=0.4,  # Donut chart
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_traces(
                    textposition='inside',
                    textinfo='percent+label',
                    hovertemplate='<b>%{label}</b><br>Sales: ฿%{value:,.0f}<br>Percentage: %{percent}<extra></extra>'
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.markdown(f"#### {get_text('category_summary_table')}")
                
                # Format the summary table
                display_summary = category_sales[['Category', 'Total Sales', 'Sales %', 'Quantity', 'Transactions']].copy()
                display_summary['Total Sales'] = display_summary['Total Sales'].apply(lambda x: f"฿{x:,.0f}")
                display_summary['Sales %'] = display_summary['Sales %'].apply(lambda x: f"{x:.1f}%")
                display_summary['Quantity'] = display_summary['Quantity'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(display_summary, use_container_width=True, hide_index=True)
                
                # Export button
                csv = category_sales.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "⬇️ Download Summary CSV",
                    csv,
                    "product_category_summary.csv",
                    "text/csv",
                    key='download-category-summary'
                )
            
            st.markdown("---")
            
            # === BAR CHART ===
            st.markdown(f"### {get_text('sales_by_category')}")
            
            fig_bar = px.bar(
                category_sales,
                x='Category',
                y='Total Sales',
                title='Total Sales by Product Category',
                color='Total Sales',
                color_continuous_scale='Viridis',
                text='Total Sales',
                hover_data=['Quantity', 'Transactions']
            )
            fig_bar.update_traces(texttemplate='฿%{text:,.0f}', textposition='outside')
            apply_chart_layout(fig_bar, showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # === DETAILED BREAKDOWN (EXPANDABLE) ===
            with st.expander("📋 Detailed Product Breakdown & Category Editor"):
                st.markdown(f"#### {get_text('all_products_by_category')}")
                st.caption("💡 Click on a product to manually change its category")
                
                # Group products by category with details
                detailed_products = df_products.groupby(['product_category', 'item']).agg({
                    'line_total': 'sum',
                    'quantity': 'sum',
                    'bill_number': 'nunique'
                }).reset_index()
                detailed_products.columns = ['Category', 'Product', 'Total Sales', 'Quantity', 'Transactions']
                detailed_products = detailed_products.sort_values(['Category', 'Total Sales'], ascending=[True, False])
                
                # Display as table with edit functionality
                st.markdown(f"##### {get_text('edit_product_categories')}")
                
                # Category options
                category_options = [
                    "🧊 ป่น (Crushed Ice)",
                    "🧊 หลอดเล็ก (Small Tube)",
                    "🧊 หลอดใหญ่ (Large Tube)",
                    "📦 อื่นๆ (Other)"
                ]
                
                # Product editor
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"**{get_text('select_product_to_edit')}**")
                    # Get unique products sorted by sales
                    product_list = detailed_products.sort_values('Total Sales', ascending=False)['Product'].unique().tolist()
                    
                    if product_list:
                        selected_product = st.selectbox(
                            "Choose a product",
                            product_list,
                            key="product_selector"
                        )
                        
                        # Get current category for this product
                        current_cat = detailed_products[detailed_products['Product'] == selected_product]['Category'].iloc[0]
                        
                        # Check if there's a manual override
                        if selected_product in st.session_state.manual_categories:
                            display_cat = st.session_state.manual_categories[selected_product]
                            st.info(f"✏️ Manual category applied: **{display_cat}**")
                        else:
                            display_cat = current_cat
                            st.caption(f"Current auto-detected category: {current_cat}")
                
                with col2:
                    st.markdown(f"**{get_text('change_category_to')}**")
                    
                    if product_list:
                        # Get current index
                        try:
                            current_idx = category_options.index(display_cat)
                        except ValueError:
                            current_idx = 0
                        
                        new_category = st.selectbox(
                            "New category",
                            category_options,
                            index=current_idx,
                            key="category_selector"
                        )
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("💾 Save Change", use_container_width=True):
                                st.session_state.manual_categories[selected_product] = new_category
                                # Save to database
                                db.save_manual_categories(st.session_state.manual_categories)
                                st.success(f"✅ Updated and saved to database!")
                                st.rerun()
                        
                        with col_b:
                            if st.button("🔄 Reset", use_container_width=True):
                                if selected_product in st.session_state.manual_categories:
                                    del st.session_state.manual_categories[selected_product]
                                    # Save updated categories to database
                                    db.save_manual_categories(st.session_state.manual_categories)
                                    st.success("✅ Reset to auto and saved to database!")
                                    st.rerun()
                
                st.markdown("---")
                
                # Show manual overrides count
                if st.session_state.manual_categories:
                    st.info(f"📝 **{len(st.session_state.manual_categories)} manual categorizations** active")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        with st.expander("👁️ View All Manual Changes"):
                            for prod, cat in st.session_state.manual_categories.items():
                                st.write(f"• **{prod}** → {cat}")
                    
                    with col2:
                        if st.button("🗑️ Clear All Manual Categories"):
                            st.session_state.manual_categories = {}
                            # Clear from database
                            db.clear_manual_categories()
                            st.success("✅ All manual categories cleared from database!")
                            st.rerun()
                
                st.markdown("---")
                st.markdown(f"##### {get_text('current_product_breakdown')}")
                
                # Format for display
                display_detailed = detailed_products.copy()
                display_detailed['Total Sales'] = display_detailed['Total Sales'].apply(lambda x: f"฿{x:,.0f}")
                display_detailed['Quantity'] = display_detailed['Quantity'].apply(lambda x: f"{x:,.0f}")
                
                st.dataframe(display_detailed, use_container_width=True, hide_index=True, height=400)
                
                # Export detailed breakdown
                csv_detailed = detailed_products.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "⬇️ Download Detailed Breakdown CSV",
                    csv_detailed,
                    "product_detailed_breakdown.csv",
                    "text/csv",
                    key='download-detailed-breakdown'
                )
                
                # Export/Import manual categorizations
                if st.session_state.manual_categories:
                    import json
                    manual_cat_json = json.dumps(st.session_state.manual_categories, ensure_ascii=False, indent=2)
                    st.download_button(
                        "⬇️ Export Manual Categories (JSON)",
                        manual_cat_json,
                        "manual_categories.json",
                        "application/json",
                        key='download-manual-categories'
                    )
                
                # Import manual categories
                st.markdown(get_heading("import_manual_categories"))
                uploaded_file = st.file_uploader(
                    "Upload JSON file with manual categories",
                    type=['json'],
                    key='import-manual-categories',
                    help="Upload a JSON file with product categories in format: {'Product Name': 'Category'}"
                )
                
                if uploaded_file is not None:
                    try:
                        import json
                        imported_categories = json.load(uploaded_file)
                        
                        if isinstance(imported_categories, dict):
                            # Merge with existing categories
                            st.session_state.manual_categories.update(imported_categories)
                            # Save to database
                            db.save_manual_categories(st.session_state.manual_categories)
                            st.success(f"✅ Imported {len(imported_categories)} manual categories!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid JSON format. Expected a dictionary.")
                    except Exception as e:
                        st.error(f"❌ Error importing file: {str(e)}")
            
            # === INSIGHTS ===
            st.info(f"""
            **💡 Key Insights:**
            - **{top_category.split()[1]}** is the top-selling category with ฿{top_sales:,.0f} ({category_sales.iloc[0]['Sales %']:.1f}% of total sales)
            - Total of **{total_quantity:,.0f} units** sold across all categories
            - Average unit price: **฿{avg_price:,.2f}**
            - Main 3 product categories account for **{(main_sales/total_sales_sum*100):.1f}%** of total revenue
            """)

        elif st.session_state.selected_tab == get_text("by_customer"):
            st.subheader(get_text("customer_analysis"))
            
            # Customer sorting options
            col1, col2 = st.columns([3, 1])
            with col1:
                sort_by = st.selectbox("Sort Customers By", 
                                     ["Total Sales", "Number of Purchases", "Items Purchased", "Average Order Value"])
            with col2:
                customer_limit = st.selectbox("Show Top", [10, 20, 30, 50, 100], index=1, key="customer_limit")
            
            # Prepare customer data
            customer_line_df = line_df[line_df["customer_id"].notna()].copy()
            customer_receipt_df = receipt_df[receipt_df["customer_id"].notna()].copy()
            
            if customer_receipt_df.empty:
                st.warning("No customer data available. Transactions may not have customer IDs.")
            else:
                # Sales and transaction metrics from receipt-level data.
                if "signed_net" in customer_receipt_df.columns:
                    customer_stats = customer_receipt_df.groupby("customer_id").agg({
                        "customer_name": "first",
                        "signed_net": "sum",
                        "bill_number": "nunique",
                        "day": "nunique"
                    }).reset_index()
                    customer_stats.columns = ["Customer ID", "Customer Name", "Total Sales", "Number of Purchases", "Days Active"]
                else:
                    customer_stats = customer_receipt_df.groupby("customer_id").agg({
                        "customer_name": "first",
                        "line_total": "sum",
                        "bill_number": "nunique",
                        "day": "nunique"
                    }).reset_index()
                    customer_stats.columns = ["Customer ID", "Customer Name", "Total Sales", "Number of Purchases", "Days Active"]

                # Quantity remains line-level.
                customer_items = (
                    customer_line_df.groupby("customer_id", as_index=False)["quantity"].sum()
                    .rename(columns={"quantity": "Items Purchased"})
                )
                customer_stats = customer_stats.merge(
                    customer_items.rename(columns={"customer_id": "Customer ID"}),
                    on="Customer ID",
                    how="left",
                )
                customer_stats["Items Purchased"] = customer_stats["Items Purchased"].fillna(0)
                customer_stats["Average Order Value"] = customer_stats["Total Sales"] / customer_stats["Number of Purchases"]
                
                # Sort based on selection
                sort_map = {
                    "Total Sales": "Total Sales",
                    "Number of Purchases": "Number of Purchases",
                    "Items Purchased": "Items Purchased",
                    "Average Order Value": "Average Order Value"
                }
                customer_stats_sorted = customer_stats.sort_values(sort_map[sort_by], ascending=False).head(customer_limit)
                
                # Visualization
                # Use customer name for display if available
                has_customer_names = (
                    "Customer Name" in customer_stats_sorted.columns
                    and customer_stats_sorted["Customer Name"].fillna("").astype(str).str.strip().ne("").any()
                )
                display_col = "Customer Name" if has_customer_names else "Customer ID"
                
                fig = px.bar(customer_stats_sorted, 
                            x=sort_map[sort_by], 
                            y=display_col,
                            orientation="h",
                            title=f"Top {customer_limit} Customers by {sort_by}",
                            color=sort_map[sort_by],
                            color_continuous_scale="Plasma",
                            hover_data=["Customer ID", "Customer Name", "Total Sales", "Number of Purchases", "Items Purchased", "Average Order Value"])
                apply_chart_layout(fig, yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                # Customer summary stats
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Customers", len(customer_stats))
                col2.metric("Avg Sales/Customer", f"{customer_stats['Total Sales'].mean():,.0f}")
                col3.metric("Avg Purchases/Customer", f"{customer_stats['Number of Purchases'].mean():.1f}")
                col4.metric("Avg Order Value", f"{customer_stats['Average Order Value'].mean():,.0f}")
                
                # Detailed customer table
                st.subheader(get_heading("customer_details"))
                st.dataframe(customer_stats_sorted.sort_values(sort_map[sort_by], ascending=False),
                           use_container_width=True, hide_index=True)
                
                # Customer segment analysis
                st.subheader(get_heading("customer_segments"))
                col1, col2 = st.columns(2)
                
                with col1:
                    # By purchase frequency
                    customer_stats["Segment"] = pd.cut(customer_stats["Number of Purchases"], 
                                                      bins=[0, 1, 3, 5, float('inf')],
                                                      labels=["One-time", "Occasional", "Regular", "Loyal"])
                    segment_sales = customer_stats.groupby("Segment")["Total Sales"].sum().reset_index()
                    fig_seg = px.pie(segment_sales, names="Segment", values="Total Sales",
                                   title="Sales by Customer Segment",
                                   color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig_seg, use_container_width=True)
                
                with col2:
                    # Customer distribution
                    fig_dist = px.histogram(customer_stats, x="Number of Purchases",
                                          title="Customer Purchase Frequency Distribution",
                                          labels={"Number of Purchases": "Purchases", "count": "Customers"},
                                          color_discrete_sequence=["#636EFA"])
                    st.plotly_chart(fig_dist, use_container_width=True)

        elif st.session_state.selected_tab == get_text("credit"):
            st.subheader(get_text("credit_management"))
            
            # Filter for credit transactions
            if 'payment_name' in receipt_df.columns:
                credit_receipt_df = receipt_df[receipt_df['payment_name'].str.contains('ค้างชำระ|เครดิต', case=False, na=False)].copy()
                credit_line_df = line_df[line_df['payment_name'].str.contains('ค้างชำระ|เครดิต', case=False, na=False)].copy()
                
                if credit_receipt_df.empty:
                    st.warning("⚠️ No credit transactions found in current data")
                    st.info("Credit transactions are those with payment type: ค้างชำระ or เครดิต")
                else:
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    total_credit = credit_receipt_df['signed_net'].sum() if "signed_net" in credit_receipt_df.columns else 0
                    credit_customers = credit_receipt_df['customer_id'].nunique()
                    credit_transactions = credit_receipt_df['bill_number'].nunique()
                    avg_credit = total_credit / credit_customers if credit_customers > 0 else 0
                    
                    col1.metric("💰 Total Credit Sales", f"{total_credit:,.2f} THB")
                    col2.metric("👥 Credit Customers", credit_customers)
                    col3.metric("🧾 Credit Transactions", credit_transactions)
                    col4.metric("📊 Avg per Customer", f"{avg_credit:,.2f} THB")
                    
                    st.markdown("---")
                    
                    # Outstanding by Customer
                    st.markdown(get_heading("outstanding_by_customer"))
                    
                    if "signed_net" in credit_receipt_df.columns:
                        customer_credit = credit_receipt_df.groupby(['customer_id', 'customer_name']).agg({
                            'signed_net': 'sum',
                            'bill_number': 'nunique',
                            'day': ['min', 'max']
                        }).reset_index()
                        customer_credit.columns = ['Customer ID', 'Customer Name', 'Outstanding Amount', 
                                                  'Transactions', 'First Credit Date', 'Last Credit Date']
                    else:
                        customer_credit = credit_receipt_df.groupby(['customer_id', 'customer_name']).agg({
                            'line_total': 'sum',
                            'bill_number': 'nunique',
                            'day': ['min', 'max']
                        }).reset_index()
                        customer_credit.columns = ['Customer ID', 'Customer Name', 'Outstanding Amount', 
                                                  'Transactions', 'First Credit Date', 'Last Credit Date']
                    customer_credit = customer_credit.sort_values('Outstanding Amount', ascending=False)
                    
                    # Calculate days outstanding
                    customer_credit['Days Outstanding'] = customer_credit['Last Credit Date'].apply(
                        lambda x: (datetime.now().date() - x).days
                    )
                    
                    # Priority status
                    def get_priority(days):
                        if days > 30:
                            return "🔴 Overdue (30+ days)"
                        elif days > 15:
                            return "🟡 Due Soon (15-30 days)"
                        else:
                            return "🟢 Current (<15 days)"
                    
                    customer_credit['Status'] = customer_credit['Days Outstanding'].apply(get_priority)
                    
                    # Show overdue first
                    overdue = customer_credit[customer_credit['Days Outstanding'] > 30]
                    due_soon = customer_credit[(customer_credit['Days Outstanding'] > 15) & 
                                              (customer_credit['Days Outstanding'] <= 30)]
                    current = customer_credit[customer_credit['Days Outstanding'] <= 15]
                    
                    # Priority alerts
                    if not overdue.empty:
                        st.error(f"🔴 {len(overdue)} customers OVERDUE (30+ days) - Total: {overdue['Outstanding Amount'].sum():,.2f} THB")
                    if not due_soon.empty:
                        st.warning(f"🟡 {len(due_soon)} customers DUE SOON (15-30 days) - Total: {due_soon['Outstanding Amount'].sum():,.2f} THB")
                    if not current.empty:
                        st.success(f"🟢 {len(current)} customers CURRENT (<15 days) - Total: {current['Outstanding Amount'].sum():,.2f} THB")
                    
                    # Display table
                    st.dataframe(
                        customer_credit[['Customer Name', 'Outstanding Amount', 'Transactions', 
                                       'First Credit Date', 'Last Credit Date', 'Days Outstanding', 'Status']],
                        use_container_width=True,
                        hide_index=True,
                        height=400
                    )
                    
                    st.markdown("---")
                    
                    # Credit by Location
                    st.markdown(get_heading("credit_sales_by_location"))
                    
                    if 'location' in credit_receipt_df.columns:
                        if "signed_net" in credit_receipt_df.columns:
                            location_credit = credit_receipt_df.groupby('location').agg({
                                'signed_net': 'sum',
                                'bill_number': 'nunique',
                                'customer_id': 'nunique'
                            }).reset_index()
                            location_credit.columns = ['Location', 'Total Credit', 'Transactions', 'Customers']
                        else:
                            location_credit = credit_receipt_df.groupby('location').agg({
                                'line_total': 'sum',
                                'bill_number': 'nunique',
                                'customer_id': 'nunique'
                            }).reset_index()
                            location_credit.columns = ['Location', 'Total Credit', 'Transactions', 'Customers']
                        location_credit = location_credit.sort_values('Total Credit', ascending=False)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            fig = px.bar(location_credit, x='Total Credit', y='Location',
                                       orientation='h',
                                       title="Credit Sales by Location",
                                       color='Total Credit',
                                       color_continuous_scale='Reds')
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            fig = px.pie(location_credit, names='Location', values='Total Credit',
                                       title="Credit Distribution by Location",
                                       hole=0.4)
                            st.plotly_chart(fig, use_container_width=True)
                        
                        st.dataframe(location_credit, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    
                    # Credit vs Cash Trends
                    st.markdown(get_heading("credit_vs_cash_trend"))
                    
                    # Get cash transactions
                    cash_receipt_df = receipt_df[receipt_df['payment_name'].str.contains('เงินสด', case=False, na=False)].copy()
                    
                    # Daily aggregation for credit
                    credit_daily = credit_receipt_df.groupby('day')['signed_net'].sum().reset_index()
                    credit_daily.columns = ['Date', 'Credit Sales']
                    
                    # Daily aggregation for cash
                    cash_daily = cash_receipt_df.groupby('day')['signed_net'].sum().reset_index()
                    cash_daily.columns = ['Date', 'Cash Sales']
                    
                    # Merge for comparison
                    daily_comparison = pd.merge(credit_daily, cash_daily, on='Date', how='outer').fillna(0)
                    
                    # Melt for plotly (long format)
                    daily_comparison_melted = daily_comparison.melt(
                        id_vars='Date',
                        value_vars=['Credit Sales', 'Cash Sales'],
                        var_name='Payment Type',
                        value_name='Amount'
                    )
                    
                    # Create comparison chart
                    fig = px.line(daily_comparison_melted, 
                                 x='Date', 
                                 y='Amount',
                                 color='Payment Type',
                                 title="Daily Sales: Credit vs Cash",
                                 markers=True,
                                 color_discrete_map={
                                     'Credit Sales': '#EF553B',  # Red for credit
                                     'Cash Sales': '#00CC96'      # Green for cash
                                 })
                    apply_chart_layout(
                        fig,
                        hovermode='x unified',
                        yaxis_title='Sales Amount (THB)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Cash vs Credit Overview
                    st.markdown(get_heading("cash_vs_credit_overview"))
                    
                    # Calculate totals
                    total_cash = cash_daily['Cash Sales'].sum() if not cash_daily.empty else 0
                    total_credit = credit_daily['Credit Sales'].sum()
                    grand_total = total_cash + total_credit
                    credit_percentage = (total_credit / grand_total * 100) if grand_total > 0 else 0
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Pie chart: Cash vs Credit
                        payment_overview = pd.DataFrame({
                            'Payment Type': ['เงินสด (Cash)', 'เครดิต/ค้างชำระ (Credit)'],
                            'Total Amount': [total_cash, total_credit]
                        })
                        
                        fig = px.pie(payment_overview, 
                                   names='Payment Type', 
                                   values='Total Amount',
                                   title="Cash vs Credit Sales Distribution",
                                   color_discrete_sequence=['#00CC96', '#EF553B'])
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        # Summary metrics
                        st.metric("💵 Total Cash Sales", f"{total_cash:,.2f} THB")
                        st.metric("Total Credit Sales", f"{total_credit:,.2f} THB")
                        st.metric("Credit Ratio", f"{credit_percentage:.1f}%")
                        st.metric("🎯 Total Sales", f"{grand_total:,.2f} THB")
                    
                    st.markdown("---")
                    
                    # Export options
                    st.markdown(get_heading("export_credit_reports"))
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Outstanding balance CSV
                        csv_outstanding = customer_credit.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ Outstanding Balances",
                            csv_outstanding,
                            "outstanding_balances.csv",
                            "text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        # Overdue customers only
                        if not overdue.empty:
                            csv_overdue = overdue.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "⬇️ Overdue Customers",
                                csv_overdue,
                                "overdue_customers.csv",
                                "text/csv",
                                use_container_width=True
                            )
                    
                    with col3:
                        # All credit transactions
                        csv_all_credit = credit_line_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "⬇️ All Credit Transactions",
                            csv_all_credit,
                            "all_credit_transactions.csv",
                            "text/csv",
                            use_container_width=True
                        )
            else:
                st.warning("⚠️ Payment type data not available. Click 'Sync All Metadata' first.")

        elif st.session_state.selected_tab == get_text("interactive_data"):
            st.subheader(get_text("interactive_data_explorer"))
            
            # Interactive filtering options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                search_product = st.text_input("🔍 Search Product", "")
            with col2:
                search_sku = st.text_input("🔍 Search SKU", "")
            with col3:
                search_customer = st.text_input("🔍 Search Customer", "")
            
            # Filter dataframe
            filtered_df = line_df.copy()
            if search_product:
                filtered_df = filtered_df[filtered_df["item"].str.contains(search_product, case=False, na=False)]
            if search_sku:
                filtered_df = filtered_df[filtered_df["sku"].astype(str).str.contains(search_sku, case=False, na=False)]
            if search_customer:
                # Search in both customer_id and customer_name
                customer_mask = (
                    filtered_df["customer_id"].astype(str).str.contains(search_customer, case=False, na=False) |
                    filtered_df["customer_name"].astype(str).str.contains(search_customer, case=False, na=False)
                )
                filtered_df = filtered_df[customer_mask]
            
            filtered_receipt_df = build_receipt_frame(filtered_df)

            # Show filtered metrics
            col1, col2, col3, col4 = st.columns(4)
            if "signed_net" in filtered_receipt_df.columns:
                col1.metric("Filtered Sales", f"{filtered_receipt_df['signed_net'].sum():,.0f}")
            else:
                col1.metric("Filtered Sales", f"{filtered_df['line_total'].sum():,.0f}")
            col2.metric("Filtered Items", f"{filtered_df['quantity'].sum():,.0f}")
            col3.metric("Transactions", filtered_receipt_df["bill_number"].nunique())
            col4.metric("Products", len(filtered_df["item"].unique()))
            
            # Sorting options
            col1, col2 = st.columns([3, 1])
            with col1:
                sort_column = st.selectbox("Sort By", 
                                         ["date", "total", "quantity", "item", "sku", "customer_name", "customer_id", "bill_number"])
            with col2:
                sort_order = st.selectbox("Order", ["Descending", "Ascending"])
            
            # Sort and display
            ascending = sort_order == "Ascending"
            filtered_df_sorted = filtered_df.sort_values(sort_column, ascending=ascending)
            
            # Display interactive table
            st.dataframe(filtered_df_sorted, 
                       use_container_width=True, 
                       hide_index=True,
                       height=400)
            
            # Scatter plot for correlation analysis
            st.subheader(get_heading("quantity_vs_total_sales"))
            scatter_data = filtered_df.groupby("item").agg({
                "quantity": "sum",
                "line_total": "sum",
                "bill_number": "nunique"
            }).reset_index()
            scatter_data.columns = ["Product", "Total Quantity", "Total Sales", "Times Sold"]
            
            fig_scatter = px.scatter(scatter_data, 
                                    x="Total Quantity", 
                                    y="Total Sales",
                                    size="Times Sold",
                                    hover_data=["Product"],
                                    title="Product Performance: Quantity vs Sales",
                                    color="Times Sold",
                                    color_continuous_scale="Rainbow")
            st.plotly_chart(fig_scatter, use_container_width=True)

        elif st.session_state.selected_tab == get_text("transaction_log"):
            st.subheader(get_text("transaction_log"))
            
            # CSV Upload for Manual Reconciliation
            st.markdown(get_heading("manual_checklist_upload_reconcile"))
            st.write("Upload your manual checklist CSV to compare against API data")
            
            # Download template
            col1, col2 = st.columns([3, 1])
            with col2:
                template_csv = "day,customer,product,quantity\n2025-10-07,Customer Name,Product Name,5\n2025-10-06,Another Customer,Another Product,3"
                st.download_button(
                    "📥 Download Template",
                    template_csv,
                    "manual_checklist_template.csv",
                    "text/csv",
                    help="Download sample CSV format"
                )
            
            uploaded_file = st.file_uploader(
                "Upload CSV (columns: day, customer, product, quantity)",
                type=["csv"],
                key="manual_checklist"
            )
            
            manual_df = None
            if uploaded_file is not None:
                try:
                    manual_df = pd.read_csv(uploaded_file)
                    
                    # Normalize column names (case insensitive)
                    manual_df.columns = [col.lower().strip() for col in manual_df.columns]
                    
                    # Check required columns
                    required = ['day', 'customer', 'product', 'quantity']
                    missing = [col for col in required if col not in manual_df.columns]
                    
                    if missing:
                        st.error(f"❌ Missing required columns: {', '.join(missing)}")
                        st.info(f"Found columns: {', '.join(manual_df.columns)}")
                        manual_df = None
                    else:
                        # Convert day to date format
                        manual_df['day'] = pd.to_datetime(manual_df['day']).dt.date
                        
                        st.success(f"✅ Uploaded {len(manual_df)} manual entries")
                        
                        # Show preview
                        with st.expander("📋 Preview Manual Checklist"):
                            st.dataframe(manual_df.head(10), use_container_width=True)
                        
                except Exception as e:
                    st.error(f"❌ Error reading CSV: {str(e)}")
                    manual_df = None
            
            st.markdown("---")
            
            # Location selector
            if "location" in line_df.columns:
                available_locations = sorted(line_df["location"].dropna().unique())
                
                if len(available_locations) == 0:
                    st.warning("⚠️ No location data available. Make sure to sync Categories and Items.")
                else:
                    selected_log_location = st.selectbox(
                        "📍 Select Location to View Transactions:",
                        available_locations,
                        key="transaction_log_location"
                    )
                    
                    # Filter by selected location
                    location_df = line_df[line_df["location"] == selected_log_location].copy()
                    location_receipt_df = receipt_df[receipt_df["location"] == selected_log_location].copy()
                    
                    if location_df.empty:
                        st.warning(f"No transactions found for {selected_log_location}")
                    else:
                        # Summary metrics for selected location
                        col1, col2, col3, col4 = st.columns(4)
                        if "signed_net" in location_receipt_df.columns:
                            col1.metric("Total Sales", f"{location_receipt_df['signed_net'].sum():,.0f}")
                        else:
                            col1.metric("Total Sales", f"{location_df['line_total'].sum():,.0f}")
                        col2.metric("Transactions", location_receipt_df['bill_number'].nunique())
                        col3.metric("Items Sold", f"{location_df['quantity'].sum():,.0f}")
                        col4.metric("Unique Customers", location_df['customer_id'].nunique())
                        
                        st.markdown("---")
                        
                        # Prepare transaction log
                        log_df = location_df[[
                            'day', 'customer_name', 'bill_number', 'sku', 'item', 'quantity'
                        ]].copy()
                        
                        # Sort by day (most recent first) then by bill number
                        log_df = log_df.sort_values(['day', 'bill_number'], ascending=[False, False])
                        
                        # Rename columns for clarity
                        log_df.columns = ['Date', 'Customer', 'Bill #', 'SKU', 'Product', 'Qty']
                        
                        # Display options
                        col1, col2 = st.columns([3, 1])
                        with col2:
                            show_limit = st.selectbox("Show Rows", [50, 100, 200, 500, "All"], index=0)
                        
                        # Apply limit
                        if show_limit != "All":
                            display_df = log_df.head(show_limit)
                            st.caption(f"Showing {len(display_df)} of {len(log_df)} total transactions")
                        else:
                            display_df = log_df
                        
                        # Display table
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                            height=600
                        )
                        
                        # Download button for this location
                        st.markdown("---")
                        col1, col2 = st.columns([3, 1])
                        with col2:
                            csv = log_df.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                f"⬇️ Download {selected_log_location}",
                                csv,
                                f"transactions_{selected_log_location}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        
                        # Reconciliation section
                        if manual_df is not None:
                            st.markdown("---")
                            st.markdown(get_heading("reconciliation_analysis"))
                            
                            # Prepare API data for comparison (for this location)
                            api_summary = location_df.groupby(['day', 'customer_name', 'item']).agg({
                                'quantity': 'sum'
                            }).reset_index()
                            api_summary.columns = ['day', 'customer', 'product', 'api_quantity']
                            
                            # Prepare manual data (normalize for comparison)
                            manual_summary = manual_df.groupby(['day', 'customer', 'product']).agg({
                                'quantity': 'sum'
                            }).reset_index()
                            manual_summary.columns = ['day', 'customer', 'product', 'manual_quantity']
                            
                            # Merge for comparison
                            comparison = pd.merge(
                                api_summary,
                                manual_summary,
                                on=['day', 'customer', 'product'],
                                how='outer',
                                indicator=True
                            )
                            
                            # Fill NaN with 0 for comparison
                            comparison['api_quantity'] = comparison['api_quantity'].fillna(0)
                            comparison['manual_quantity'] = comparison['manual_quantity'].fillna(0)
                            
                            # Calculate difference
                            comparison['difference'] = comparison['api_quantity'] - comparison['manual_quantity']
                            comparison['status'] = comparison['difference'].apply(
                                lambda x: '✅ Match' if x == 0 else ('⚠️ API More' if x > 0 else '❌ Manual More')
                            )
                            
                            # Summary metrics
                            col1, col2, col3, col4 = st.columns(4)
                            matches = len(comparison[comparison['difference'] == 0])
                            total = len(comparison)
                            col1.metric("Total Entries", total)
                            col2.metric("✅ Matches", matches)
                            col3.metric("⚠️ Discrepancies", total - matches)
                            col4.metric("Match Rate", f"{(matches/total*100):.1f}%" if total > 0 else "N/A")
                            
                            # Show discrepancies first
                            discrepancies = comparison[comparison['difference'] != 0].copy()
                            if not discrepancies.empty:
                                st.markdown(get_heading("discrepancies_found"))
                                st.dataframe(
                                    discrepancies[['day', 'customer', 'product', 'api_quantity', 'manual_quantity', 'difference', 'status']],
                                    use_container_width=True,
                                    hide_index=True
                                )
                            else:
                                st.success("🎉 Perfect Match! No discrepancies found.")
                            
                            # Show full comparison
                            with st.expander("📊 Full Comparison Table"):
                                st.dataframe(
                                    comparison[['day', 'customer', 'product', 'api_quantity', 'manual_quantity', 'difference', 'status']],
                                    use_container_width=True,
                                    hide_index=True
                                )
                            
                            # Download comparison
                            col1, col2 = st.columns([3, 1])
                            with col2:
                                comparison_csv = comparison.to_csv(index=False).encode("utf-8")
                                st.download_button(
                                    "⬇️ Download Comparison",
                                    comparison_csv,
                                    f"reconciliation_{selected_log_location}.csv",
                                    "text/csv",
                                    use_container_width=True
                                )
            else:
                st.warning("⚠️ No location data available in current dataset")
        
        elif st.session_state.selected_tab == get_text("customer_invoice"):
            st.subheader(get_text("customer_invoice_generator"))
            
            # Customer search and selection
            st.markdown(get_heading("select_customer"))
            
            # Search bar (full width)
            customer_search = st.text_input(
                "🔍 Search Customer by Name or ID:",
                "",
                key="invoice_customer_search"
            )
            
            # Get unique customers
            if 'customer_name' in receipt_df.columns:
                customer_list = receipt_df[['customer_id', 'customer_name']].drop_duplicates()
                customer_list = customer_list[customer_list['customer_name'].notna()]
                
                # Filter by search
                if customer_search:
                    mask = (
                        customer_list['customer_name'].str.contains(customer_search, case=False, na=False) |
                        customer_list['customer_id'].str.contains(customer_search, case=False, na=False)
                    )
                    filtered_customers = customer_list[mask]
                else:
                    filtered_customers = customer_list
                
                # Create display list
                customer_options = []
                customer_map_invoice = {}
                for _, row in filtered_customers.iterrows():
                    cust_id = row['customer_id']
                    cust_name = row['customer_name']
                    
                    # Skip if either is None
                    if pd.isna(cust_id) or pd.isna(cust_name) or cust_name == "Unknown Customer":
                        continue
                    
                    display = f"{cust_name} ({str(cust_id)[:8]}...)"
                    customer_options.append(display)
                    customer_map_invoice[display] = cust_id
                
                # Dropdown (full width)
                if len(customer_options) > 0:
                    selected_customer_display = st.selectbox(
                        f"Select Customer ({len(customer_options)} found):",
                        customer_options,
                        key="invoice_customer_select"
                    )
                    selected_customer_id = customer_map_invoice[selected_customer_display]
                    selected_customer_name = selected_customer_display.split(' (')[0]
                else:
                    st.warning("No customers found")
                    selected_customer_id = None
                    selected_customer_name = None
            else:
                st.warning("⚠️ Customer data not available")
                selected_customer_id = None
                selected_customer_name = None
            
            if selected_customer_id:
                st.markdown("---")
                st.markdown(get_heading("select_invoice_period"))
                
                # Get customer's transaction date range
                customer_line_df = line_df[line_df['customer_id'] == selected_customer_id]
                customer_receipt_df = receipt_df[receipt_df['customer_id'] == selected_customer_id]
                cust_min_date = customer_line_df['day'].min()
                cust_max_date = customer_line_df['day'].max()
                
                col1, col2 = st.columns([2, 2])
                
                with col1:
                    # Ensure default value is within the valid range
                    default_start = max(cust_min_date, cust_max_date - timedelta(days=7))
                    invoice_start = st.date_input(
                        "Invoice Start Date:",
                        value=default_start,
                        min_value=cust_min_date,
                        max_value=cust_max_date,
                        key="invoice_start"
                    )
                
                with col2:
                    invoice_end = st.date_input(
                        "Invoice End Date:",
                        value=cust_max_date,
                        min_value=cust_min_date,
                        max_value=cust_max_date,
                        key="invoice_end"
                    )
                
                # Quick date range buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("📅 +1 Week", help="Set end date to 1 week from start"):
                        end_date = invoice_start + timedelta(days=7)
                        if end_date > cust_max_date:
                            end_date = cust_max_date
                        st.session_state.invoice_end_override = end_date
                        st.rerun()
                
                with col2:
                    if st.button("📅 +1 Month", help="Set end date to 1 month from start"):
                        end_date = invoice_start + timedelta(days=30)
                        if end_date > cust_max_date:
                            end_date = cust_max_date
                        st.session_state.invoice_end_override = end_date
                        st.rerun()
                
                with col3:
                    generate_invoice = st.button("🧾 Generate Invoice", use_container_width=True)
                
                # Apply override if set
                if 'invoice_end_override' in st.session_state:
                    invoice_end = st.session_state.invoice_end_override
                    st.session_state.pop('invoice_end_override')  # Clear after use
                
                if generate_invoice or st.session_state.get('show_invoice'):
                    st.session_state.show_invoice = True
                    
                    # Filter customer data for invoice period
                    invoice_df = customer_line_df[
                        (customer_line_df['day'] >= invoice_start) & 
                        (customer_line_df['day'] <= invoice_end)
                    ].copy()
                    invoice_receipt_df = customer_receipt_df[
                        (customer_receipt_df['day'] >= invoice_start) &
                        (customer_receipt_df['day'] <= invoice_end)
                    ].copy()
                    
                    if invoice_df.empty:
                        st.warning(f"No transactions found for {selected_customer_name} between {invoice_start} and {invoice_end}")
                    else:
                        st.markdown("---")
                        st.markdown(get_heading("invoice_title"))
                        
                        # Invoice header
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"""
                            **Bill To:**  
                            **{selected_customer_name}**  
                            Customer ID: `{selected_customer_id[:8]}...`
                            """)
                        
                        with col2:
                            st.markdown(f"""
                            **Invoice Date:** {datetime.now().strftime('%Y-%m-%d')}  
                            **Period:** {invoice_start} to {invoice_end}  
                            **Total Transactions:** {invoice_receipt_df['bill_number'].nunique()}
                            """)
                        
                        st.markdown("---")
                        
                        # Invoice summary metrics (trusted receipt-grain money totals)
                        col1, col2, col3, col4 = st.columns(4)
                        invoice_kpis = compute_sales_kpis(invoice_receipt_df, invoice_df)
                        total_amount = invoice_kpis["total_sales"]
                        total_items = invoice_kpis["total_items"]
                        num_transactions = invoice_kpis["transactions"]
                        
                        col1.metric("💰 Total Amount", f"{total_amount:,.2f} THB")
                        col2.metric("📦 Items Purchased", f"{int(total_items)}")
                        col3.metric("🧾 Transactions", num_transactions)
                        col4.metric("📍 Locations Visited", invoice_df['location'].nunique() if 'location' in invoice_df.columns else 0)

                        invoice_monitor = build_reconciliation_monitor(invoice_receipt_df, invoice_df)
                        if invoice_monitor.get("ok"):
                            st.success("✅ Invoice totals passed receipt-vs-line reconciliation checks.")
                        else:
                            st.error(
                                "⚠️ Invoice integrity check failed. "
                                f"Sales gap: {invoice_monitor.get('sales_gap', 0):,.2f}, "
                                f"Discount gap: {invoice_monitor.get('discount_gap', 0):,.2f}, "
                                f"Txn gap: {invoice_monitor.get('txn_gap', 0)}"
                            )
                        
                        st.markdown("---")
                        
                        # Itemized list
                        st.markdown(get_heading("itemized_transactions"))
                        
                        # Prepare invoice line items with price
                        if "signed_net" in invoice_df.columns:
                            invoice_items = invoice_df[[
                                'day', 'bill_number', 'location', 'item', 'sku', 'price', 'quantity', 'signed_net'
                            ]].copy()
                            invoice_items = invoice_items.rename(columns={'signed_net': 'total'})
                        else:
                            invoice_items = invoice_df[[
                                'day', 'bill_number', 'location', 'item', 'sku', 'price', 'quantity', 'line_total'
                            ]].copy()
                            invoice_items = invoice_items.rename(columns={'line_total': 'total'})
                        
                        # Sort by date
                        invoice_items = invoice_items.sort_values('day', ascending=True)
                        
                        # Rename columns
                        invoice_items.columns = ['Date', 'Receipt #', 'Location', 'Product', 'SKU', 'Price', 'Qty', 'Amount']
                        
                        # Format price and amount columns
                        invoice_items['Price'] = invoice_items['Price'].apply(lambda x: f"{x:,.2f}")
                        invoice_items['Amount'] = invoice_items['Amount'].apply(lambda x: f"{x:,.2f}")
                        
                        # Display invoice table
                        st.dataframe(
                            invoice_items,
                            use_container_width=True,
                            hide_index=True,
                            height=400
                        )
                        
                        # Summary by product
                        st.markdown(get_heading("summary_by_product"))
                        if "signed_net" in invoice_df.columns:
                            product_summary = invoice_df.groupby('item').agg({
                                'price': 'first',  # Get unit price
                                'quantity': 'sum',
                                'signed_net': 'sum',
                                'bill_number': 'nunique'
                            }).reset_index()
                            product_summary.columns = ['Product', 'Unit Price', 'Total Qty', 'Total Amount', 'Times Purchased']
                        else:
                            product_summary = invoice_df.groupby('item').agg({
                                'price': 'first',  # Get unit price
                                'quantity': 'sum',
                                'line_total': 'sum',
                                'bill_number': 'nunique'
                            }).reset_index()
                            product_summary.columns = ['Product', 'Unit Price', 'Total Qty', 'Total Amount', 'Times Purchased']
                        product_summary = product_summary.sort_values('Total Amount', ascending=False)
                        
                        # Format currency columns
                        product_summary['Unit Price'] = product_summary['Unit Price'].apply(lambda x: f"{x:,.2f}")
                        product_summary['Total Amount'] = product_summary['Total Amount'].apply(lambda x: f"{x:,.2f}")
                        
                        st.dataframe(product_summary, use_container_width=True, hide_index=True)
                        
                        # Payment breakdown if available
                        if 'payment_name' in invoice_df.columns:
                            st.markdown(get_heading("payment_methods_used"))
                            payment_summary = invoice_receipt_df.groupby('payment_name')['signed_net'].sum().reset_index()
                            payment_summary.columns = ['Payment Method', 'Amount']
                            payment_summary = payment_summary.sort_values('Amount', ascending=False)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.dataframe(payment_summary, use_container_width=True, hide_index=True)
                            with col2:
                                fig = px.pie(payment_summary, names='Payment Method', values='Amount',
                                           title="Payment Distribution", hole=0.4)
                                st.plotly_chart(fig, use_container_width=True)
                        
                        # Download options
                        st.markdown("---")
                        st.markdown(get_heading("download_invoice"))
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Detailed CSV
                            csv_detailed = invoice_items.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "⬇️ Download Detailed Invoice",
                                csv_detailed,
                                f"invoice_{selected_customer_name}_{invoice_start}_{invoice_end}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        
                        with col2:
                            # Summary CSV
                            csv_summary = product_summary.to_csv(index=False).encode("utf-8")
                            st.download_button(
                                "⬇️ Download Summary",
                                csv_summary,
                                f"invoice_summary_{selected_customer_name}_{invoice_start}_{invoice_end}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        
                        with col3:
                            # Print-friendly view button
                            if st.button("🖨️ Print Invoice", use_container_width=True):
                                st.session_state.show_print_view = True
                                st.rerun()
                        
                        # Print View Modal
                        if st.session_state.get('show_print_view'):
                            st.markdown("---")
                            st.markdown(get_heading("print_view"))
                            
                            # Close button
                            if st.button("❌ Close Print View"):
                                st.session_state.show_print_view = False
                                st.rerun()
                            
                            # Print-optimized invoice
                            st.markdown(f"""
                            <div style="padding: 20px; background: white; color: black;">
                            
                            # INVOICE
                            
                            **Bill To:** {selected_customer_name}  
                            **Customer ID:** {selected_customer_id}  
                            **Invoice Date:** {datetime.now().strftime('%Y-%m-%d')}  
                            **Period:** {invoice_start} to {invoice_end}  
                            
                            ---
                            
                            **Total Amount:** {total_amount:,.2f} THB  
                            **Items Purchased:** {int(total_items)}  
                            **Transactions:** {num_transactions}  
                            
                            ---
                            
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Itemized transactions (print version)
                            st.markdown(get_heading("itemized_transactions"))
                            
                            # Prepare print-friendly table
                            if 'signed_net' in invoice_df.columns:
                                print_items = invoice_df[[
                                    'day', 'item', 'sku', 'price', 'quantity', 'signed_net'
                                ]].copy()
                                print_items = print_items.rename(columns={'signed_net': 'total'})
                            else:
                                print_items = invoice_df[[
                                    'day', 'item', 'sku', 'price', 'quantity', 'line_total'
                                ]].copy()
                                print_items = print_items.rename(columns={'line_total': 'total'})
                            print_items = print_items.sort_values('day', ascending=True)
                            print_items['price'] = print_items['price'].apply(lambda x: f"{x:,.2f}")
                            print_items['total'] = print_items['total'].apply(lambda x: f"{x:,.2f}")
                            print_items.columns = ['Date', 'Product', 'SKU', 'Unit Price', 'Qty', 'Amount']
                            
                            st.dataframe(print_items, use_container_width=True, hide_index=True)
                            
                            # Product summary (print version)
                            st.markdown(get_heading("summary_by_product"))
                            
                            if 'signed_net' in invoice_df.columns:
                                print_summary = invoice_df.groupby('item').agg({
                                    'price': 'first',
                                    'quantity': 'sum',
                                    'signed_net': 'sum'
                                }).reset_index()
                                print_summary = print_summary.rename(columns={'signed_net': 'total'})
                            else:
                                print_summary = invoice_df.groupby('item').agg({
                                    'price': 'first',
                                    'quantity': 'sum',
                                    'line_total': 'sum'
                                }).reset_index()
                                print_summary = print_summary.rename(columns={'line_total': 'total'})
                            print_summary.columns = ['Product', 'Unit Price', 'Total Qty', 'Total Amount']
                            print_summary = print_summary.sort_values('Total Amount', ascending=False)
                            print_summary['Unit Price'] = print_summary['Unit Price'].apply(lambda x: f"{x:,.2f}")
                            print_summary['Total Amount'] = print_summary['Total Amount'].apply(lambda x: f"{x:,.2f}")
                            
                            st.dataframe(print_summary, use_container_width=True, hide_index=True)
                            
                            # Grand Total
                            st.markdown("---")
                            st.markdown(f"""
                            <div style="text-align: right; font-size: 20px; font-weight: bold;">
                            GRAND TOTAL: {total_amount:,.2f} THB
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("---")
                            st.info("💡 Use browser Print function (Ctrl+P or Cmd+P) to print this invoice. Consider printing to PDF for digital copy.")
        
        elif st.session_state.selected_tab == get_text("ice_forecast"):
            st.subheader(get_text("ice_forecast_dashboard"))
            
            # Check if we have data
            if df.empty:
                st.warning("⚠️ No data available. Please load data first.")
            else:
                # === ICE PRODUCT CATEGORIZATION ===
                def categorize_ice_product(product_name):
                    """Categorize products into ice types"""
                    return categorize_ice_product_name(
                        product_name,
                        manual_categories=st.session_state.get("manual_categories", {}),
                    )
                
                # Apply categorization
                df_ice = line_df.copy()
                df_ice['ice_category'] = df_ice['item'].apply(categorize_ice_product)
                receipt_ice = receipt_df.copy()
                receipt_ice['day'] = pd.to_datetime(receipt_ice['day'])
                
                # === LOCATION TABLE WITH FORECASTS ===
                st.markdown(get_heading("ice_forecast_by_location"))
                
                # Get unique locations
                locations = df_ice['location'].dropna().unique()
                locations = sorted([loc for loc in locations if loc != "Uncategorized"])
                
                # Calculate 7-day moving averages for each location and ice type
                forecast_data = []
                
                for location in locations:
                    location_df = df_ice[df_ice['location'] == location].copy()
                    location_receipt_df = receipt_ice[receipt_ice['location'] == location].copy()
                    location_df['day'] = pd.to_datetime(location_df['day'])
                    location_df = location_df.sort_values('day')
                    location_receipt_df = location_receipt_df.sort_values('day')
                    
                    # Get unique ice categories for this location
                    ice_categories = location_df['ice_category'].unique()
                    
                    location_forecast = {
                        'Location': location,
                        'Total Sales (7d avg)': 0,
                        '🧊 ป่น (Crushed Ice)': 0,
                        '🧊 หลอดเล็ก (Small Tube)': 0,
                        '🧊 หลอดใหญ่ (Large Tube)': 0,
                        '📦 อื่นๆ (Other)': 0
                    }
                    
                    # Calculate 7-day moving average for each ice category
                    for ice_type in ice_categories:
                        ice_df = location_df[location_df['ice_category'] == ice_type]
                        if not ice_df.empty:
                            # Calculate daily totals for this ice type
                            ice_daily = ice_df.groupby('day')['quantity'].sum().reset_index()
                            
                            if len(ice_daily) >= 7:
                                # Calculate 7-day moving average
                                ice_daily['ma_7d'] = ice_daily['quantity'].rolling(window=7, min_periods=1).mean()
                                latest_forecast = ice_daily['ma_7d'].iloc[-1]
                                location_forecast[ice_type] = round(latest_forecast, 1)
                            else:
                                # Use average if less than 7 days of data
                                avg_quantity = ice_daily['quantity'].mean()
                                location_forecast[ice_type] = round(avg_quantity, 1)
                        else:
                            location_forecast[ice_type] = 0.0
                    
                    # Calculate total sales 7-day average
                    if len(location_receipt_df) >= 7:
                        if "signed_net" in location_receipt_df.columns:
                            daily_sales = location_receipt_df.groupby('day')['signed_net'].sum().reset_index()
                            daily_sales['ma_7d'] = daily_sales['signed_net'].rolling(window=7, min_periods=1).mean()
                        else:
                            daily_sales = location_df.groupby('day')['line_total'].sum().reset_index()
                            daily_sales['ma_7d'] = daily_sales['line_total'].rolling(window=7, min_periods=1).mean()
                        location_forecast['Total Sales (7d avg)'] = round(daily_sales['ma_7d'].iloc[-1], 0)
                    else:
                        if "signed_net" in location_receipt_df.columns:
                            location_forecast['Total Sales (7d avg)'] = round(location_receipt_df['signed_net'].mean(), 0)
                        else:
                            location_forecast['Total Sales (7d avg)'] = round(location_df['line_total'].mean(), 0)
                    
                    forecast_data.append(location_forecast)
                
                # Create forecast DataFrame
                forecast_df = pd.DataFrame(forecast_data)
                forecast_df = forecast_df.sort_values('Total Sales (7d avg)', ascending=False)
                
                # Display forecast table
                st.dataframe(
                    forecast_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Location": st.column_config.TextColumn("Location", width="medium"),
                        "Total Sales (7d avg)": st.column_config.NumberColumn("Total Sales (7d avg)", format="฿%.0f"),
                        "🧊 ป่น (Crushed Ice)": st.column_config.NumberColumn("🧊 ป่น (Crushed Ice)", format="%.1f"),
                        "🧊 หลอดเล็ก (Small Tube)": st.column_config.NumberColumn("🧊 หลอดเล็ก (Small Tube)", format="%.1f"),
                        "🧊 หลอดใหญ่ (Large Tube)": st.column_config.NumberColumn("🧊 หลอดใหญ่ (Large Tube)", format="%.1f"),
                        "📦 อื่นๆ (Other)": st.column_config.NumberColumn("📦 อื่นๆ (Other)", format="%.1f")
                    }
                )
                
                st.markdown("---")
                
                # === LOCATION SELECTOR FOR DETAILED ANALYSIS ===
                st.markdown(get_heading("detailed_analysis_by_location"))
                
                selected_location = st.selectbox(
                    "Select Location for Detailed Analysis:",
                    locations,
                    key="ice_forecast_location"
                )
                
                if selected_location:
                    st.markdown(f"#### 📊 Detailed Analysis: {selected_location}")
                    
                    # Filter data for selected location
                    location_detail_df = df_ice[df_ice['location'] == selected_location].copy()
                    location_detail_receipt_df = receipt_ice[receipt_ice['location'] == selected_location].copy()
                    location_detail_df['day'] = pd.to_datetime(location_detail_df['day'])
                    location_detail_receipt_df['day'] = pd.to_datetime(location_detail_receipt_df['day'])
                    location_detail_df = location_detail_df.sort_values('day')
                    location_detail_receipt_df = location_detail_receipt_df.sort_values('day')
                    
                    # Calculate 7-day moving averages for each ice type
                    ice_types = ["🧊 ป่น (Crushed Ice)", "🧊 หลอดเล็ก (Small Tube)", "🧊 หลอดใหญ่ (Large Tube)", "📦 อื่นๆ (Other)"]
                    
                    # Create charts for each ice type - Full width
                    
                    # Total orders trend - Full width
                    if "signed_net" in location_detail_receipt_df.columns:
                        daily_totals = location_detail_receipt_df.groupby('day')['signed_net'].sum().reset_index()
                        daily_totals['ma_7d'] = daily_totals['signed_net'].rolling(window=7, min_periods=1).mean()
                        daily_totals = daily_totals.rename(columns={'signed_net': 'total'})
                    else:
                        daily_totals = location_detail_df.groupby('day')['line_total'].sum().reset_index()
                        daily_totals['ma_7d'] = daily_totals['line_total'].rolling(window=7, min_periods=1).mean()
                        daily_totals = daily_totals.rename(columns={'line_total': 'total'})
                    
                    fig_total = px.line(daily_totals, x='day', y=['total', 'ma_7d'],
                                      title=f"Total Orders - {selected_location}",
                                      labels={'value': 'Total Sales (THB)', 'day': 'Date'})
                    apply_chart_layout(fig_total, legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ))
                    st.plotly_chart(fig_total, use_container_width=True)
                    
                    # Ice type breakdown - Full width
                    ice_breakdown = location_detail_df.groupby(['day', 'ice_category'])['quantity'].sum().reset_index()
                    ice_breakdown_pivot = ice_breakdown.pivot(index='day', columns='ice_category', values='quantity').fillna(0)
                    
                    # Calculate 7-day moving averages
                    for col in ice_breakdown_pivot.columns:
                        ice_breakdown_pivot[f'{col}_ma7d'] = ice_breakdown_pivot[col].rolling(window=7, min_periods=1).mean()
                    
                    fig_ice = px.line(ice_breakdown_pivot, 
                                    y=[col for col in ice_breakdown_pivot.columns if '_ma7d' in col],
                                    title=f"7-Day Moving Average by Ice Type - {selected_location}",
                                    labels={'value': 'Quantity (7d avg)', 'day': 'Date'})
                    apply_chart_layout(fig_ice, legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ))
                    st.plotly_chart(fig_ice, use_container_width=True)
                    
                    # Detailed metrics
                    st.markdown(get_heading("current_forecast_metrics"))
                    
                    # Get latest 7-day averages
                    latest_date = location_detail_df['day'].max()
                    week_ago = latest_date - pd.Timedelta(days=7)
                    recent_data = location_detail_df[location_detail_df['day'] >= week_ago]
                    recent_receipt_data = location_detail_receipt_df[location_detail_receipt_df['day'] >= week_ago]
                    
                    if not recent_data.empty:
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            # Calculate total ice needed per unit
                            total_ice_needed = 0
                            for ice_type in ["🧊 ป่น (Crushed Ice)", "🧊 หลอดเล็ก (Small Tube)", "🧊 หลอดใหญ่ (Large Tube)", "📦 อื่นๆ (Other)"]:
                                ice_data = recent_data[recent_data['ice_category'] == ice_type]
                                if not ice_data.empty:
                                    daily_avg = ice_data.groupby('day')['quantity'].sum().mean()
                                    total_ice_needed += daily_avg
                            st.metric("1️⃣ Est Ice Needed / Unit", f"{total_ice_needed:.1f}")
                        
                        with col2:
                            # Calculate daily average sales
                            if "signed_net" in recent_receipt_data.columns:
                                daily_sales = recent_receipt_data.groupby('day')['signed_net'].sum().mean()
                            else:
                                daily_sales = recent_data.groupby('day')['line_total'].sum().mean()
                            st.metric("2️⃣ Est Sales", f"฿{daily_sales:,.0f}")
                        
                        with col3:
                            # Calculate daily average for crushed ice
                            crushed_data = recent_data[recent_data['ice_category'] == "🧊 ป่น (Crushed Ice)"]
                            if not crushed_data.empty:
                                crushed_daily = crushed_data.groupby('day')['quantity'].sum().mean()
                                st.metric("3️⃣ ป่น (Crushed Ice)", f"{crushed_daily:.1f}")
                            else:
                                st.metric("3️⃣ ป่น (Crushed Ice)", "0.0")
                        
                        with col4:
                            # Calculate daily average for small tube
                            small_data = recent_data[recent_data['ice_category'] == "🧊 หลอดเล็ก (Small Tube)"]
                            if not small_data.empty:
                                small_daily = small_data.groupby('day')['quantity'].sum().mean()
                                st.metric("4️⃣ หลอดเล็ก (Small Tube)", f"{small_daily:.1f}")
                            else:
                                st.metric("4️⃣ หลอดเล็ก (Small Tube)", "0.0")
                    
                    # Recommendation section
                    st.markdown(get_heading("loading_recommendations"))
                    
                    if not recent_data.empty:
                        # Calculate total ice needed using daily averages
                        total_ice_needed = 0
                        ice_breakdown = {}
                        
                        for ice_type in ice_types:
                            ice_data = recent_data[recent_data['ice_category'] == ice_type]
                            if not ice_data.empty:
                                # Calculate daily average for this ice type
                                daily_avg = ice_data.groupby('day')['quantity'].sum().mean()
                                ice_breakdown[ice_type] = round(daily_avg, 1)
                                total_ice_needed += daily_avg
                            else:
                                ice_breakdown[ice_type] = 0.0
                        
                        st.markdown(f"**Estimated Total Ice Needed:** {total_ice_needed:.1f} units")
                        st.markdown("**Breakdown by Type:**")
                        for ice_type, quantity in ice_breakdown.items():
                            st.markdown(f"- {ice_type}: {quantity} units")
                        
                        # Safety buffer recommendation
                        buffer = total_ice_needed * 0.2  # 20% buffer
                        recommended_total = total_ice_needed + buffer
                        
                        st.markdown(f"**Recommended Loading (with 20% buffer):** {recommended_total:.1f} units")
                        
                        # Add explanation of calculation method
                        st.markdown("---")
                        st.markdown(get_heading("calculation_method"))
                        st.markdown("""
                        **How these forecasts are calculated:**
                        
                        1. **Data Source**: Last 7 days of sales data for the selected location
                        2. **Daily Aggregation**: For each ice type, we sum all quantities sold per day
                        3. **Average Calculation**: We calculate the average daily quantity for each ice type
                        4. **Safety Buffer**: Add 20% to account for unexpected demand spikes
                        
                        **Example**: If "🧊 ป่น (Crushed Ice)" sold 10, 12, 8, 15, 9, 11, 13 units over 7 days:
                        - Daily average = (10+12+8+15+9+11+13) ÷ 7 = 11.1 units
                        - With 20% buffer = 11.1 × 1.2 = 13.3 units
                        """)
                    else:
                        st.warning("⚠️ No recent data available for forecasting. Please ensure you have at least 7 days of data.")
        
        elif st.session_state.selected_tab == get_text("crm"):
            st.subheader(get_text("crm_dashboard"))
            
            # Check if we have data
            if line_df.empty:
                st.warning("⚠️ No data available. Please load data first.")
            else:
                # Initialize customer notes in session state
                if 'customer_notes' not in st.session_state:
                    st.session_state.customer_notes = {}
                
                # === TOP CUSTOMERS ANALYSIS ===
                st.markdown(get_heading("top_customers"))
                
                # Calculate customer metrics
                if "signed_net" in receipt_df.columns:
                    customer_metrics = receipt_df.groupby(['customer_id', 'customer_name']).agg({
                        'signed_net': 'sum',
                        'bill_number': 'nunique',
                        'day': ['min', 'max', 'nunique']
                    }).reset_index()
                    customer_metrics.columns = ['Customer ID', 'Customer Name', 'Total Spent', 'Transactions', 'First Visit', 'Last Visit', 'Active Days']
                else:
                    customer_metrics = line_df.groupby(['customer_id', 'customer_name']).agg({
                        'line_total': 'sum',
                        'bill_number': 'nunique',
                        'day': ['min', 'max', 'nunique']
                    }).reset_index()
                    customer_metrics.columns = ['Customer ID', 'Customer Name', 'Total Spent', 'Transactions', 'First Visit', 'Last Visit', 'Active Days']
                customer_items = line_df.groupby('customer_id', as_index=False)['quantity'].sum()
                customer_metrics = customer_metrics.merge(
                    customer_items.rename(columns={'customer_id': 'Customer ID', 'quantity': 'Total Items'}),
                    on='Customer ID',
                    how='left'
                )
                customer_metrics['Total Items'] = customer_metrics['Total Items'].fillna(0)
                
                # Calculate additional metrics
                customer_metrics['Avg Transaction'] = customer_metrics['Total Spent'] / customer_metrics['Transactions']
                customer_metrics['Avg Items per Transaction'] = customer_metrics['Total Items'] / customer_metrics['Transactions']
                customer_metrics['Days Since Last Visit'] = (pd.Timestamp.now() - pd.to_datetime(customer_metrics['Last Visit'])).dt.days
                
                # Sort by total spent
                customer_metrics = customer_metrics.sort_values('Total Spent', ascending=False)
                
                # Display top customers
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Customers", len(customer_metrics))
                
                with col2:
                    top_customer_spent = customer_metrics['Total Spent'].iloc[0] if len(customer_metrics) > 0 else 0
                    st.metric("Top Customer Spent", f"฿{top_customer_spent:,.0f}")
                
                with col3:
                    avg_customer_value = customer_metrics['Total Spent'].mean()
                    st.metric("Avg Customer Value", f"฿{avg_customer_value:,.0f}")
                
                st.markdown("---")
                
                # === CUSTOMER ALERTS ===
                st.markdown(get_heading("customer_alerts"))
                
                # Algorithm to detect sudden decreases in orders
                def detect_customer_decline(customer_df):
                    """Detect if a customer has had a sudden decrease in orders"""
                    if len(customer_df) < 4:  # Need at least 4 data points
                        return False, 0
                    
                    # Get last 30 days of data
                    recent_cutoff = pd.Timestamp.now() - pd.Timedelta(days=30)
                    recent_data = customer_df[customer_df['day'] >= recent_cutoff]
                    
                    if len(recent_data) < 2:
                        return False, 0
                    
                    # Calculate weekly spending
                    recent_data['week'] = recent_data['day'].dt.to_period('W')
                    if "signed_net" in recent_data.columns:
                        weekly_spending = recent_data.groupby('week')['signed_net'].sum()
                    else:
                        weekly_spending = recent_data.groupby('week')['line_total'].sum()
                    
                    if len(weekly_spending) < 2:
                        return False, 0
                    
                    # Calculate percentage change
                    latest_week = weekly_spending.iloc[-1]
                    previous_week = weekly_spending.iloc[-2]
                    
                    if previous_week == 0:
                        return False, 0
                    
                    decline_percentage = ((latest_week - previous_week) / previous_week) * 100
                    
                    # Alert if decline is more than 50%
                    return decline_percentage < -50, abs(decline_percentage)
                
                # Check for customer declines
                alerts = []
                for _, customer in customer_metrics.head(20).iterrows():  # Check top 20 customers
                    customer_id = customer['Customer ID']
                    customer_name = customer['Customer Name']
                    
                    if pd.isna(customer_id) or pd.isna(customer_name) or customer_name == "Unknown Customer":
                        continue
                    
                    customer_df = receipt_df[receipt_df['customer_id'] == customer_id].copy()
                    customer_df['day'] = pd.to_datetime(customer_df['day'])
                    customer_df = customer_df.sort_values('day')
                    
                    is_decline, decline_percentage = detect_customer_decline(customer_df)
                    
                    if is_decline:
                        alerts.append({
                            'Customer': customer_name,
                            'Decline': f"{decline_percentage:.1f}%",
                            'Total Spent': f"฿{customer['Total Spent']:,.0f}",
                            'Last Visit': customer['Last Visit'],
                            'Days Since Last Visit': customer['Days Since Last Visit']
                        })
                
                if alerts:
                    st.warning(f"🚨 {len(alerts)} customers showing significant order decline!")
                    
                    # Display alerts
                    alerts_df = pd.DataFrame(alerts)
                    st.dataframe(alerts_df, use_container_width=True, hide_index=True)
                else:
                    st.success("✅ No significant customer declines detected")
                
                st.markdown("---")
                
                # === CUSTOMER LIST WITH NOTES ===
                st.markdown(get_heading("customer_management"))
                
                # Search and filter options
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    search_term = st.text_input("🔍 Search Customer:", placeholder="Enter customer name or ID")
                
                with col2:
                    min_spent = st.number_input("Min Total Spent (THB):", min_value=0, value=0)
                
                with col3:
                    show_alerts_only = st.checkbox("Show Alerts Only", value=False)
                
                # Filter customers
                filtered_customers = customer_metrics.copy()
                
                if search_term:
                    mask = (
                        filtered_customers['Customer Name'].str.contains(search_term, case=False, na=False) |
                        filtered_customers['Customer ID'].str.contains(search_term, case=False, na=False)
                    )
                    filtered_customers = filtered_customers[mask]
                
                if min_spent > 0:
                    filtered_customers = filtered_customers[filtered_customers['Total Spent'] >= min_spent]
                
                if show_alerts_only:
                    alert_customer_ids = [alert['Customer'] for alert in alerts]
                    filtered_customers = filtered_customers[filtered_customers['Customer Name'].isin(alert_customer_ids)]
                
                # Display customer list
                st.markdown(f"**Showing {len(filtered_customers)} customers**")
                
                for idx, customer in filtered_customers.iterrows():
                    customer_id = customer['Customer ID']
                    customer_name = customer['Customer Name']
                    
                    if pd.isna(customer_id) or pd.isna(customer_name) or customer_name == "Unknown Customer":
                        continue
                    
                    # Create expandable section for each customer
                    with st.expander(f"👤 {customer_name} - ฿{customer['Total Spent']:,.0f} ({customer['Transactions']} transactions)"):
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.markdown(f"**Customer ID:** {customer_id}")
                            st.markdown(f"**Total Spent:** ฿{customer['Total Spent']:,.0f}")
                            st.markdown(f"**Transactions:** {customer['Transactions']}")
                            st.markdown(f"**Avg Transaction:** ฿{customer['Avg Transaction']:,.0f}")
                            st.markdown(f"**Last Visit:** {customer['Last Visit']}")
                            st.markdown(f"**Days Since Last Visit:** {customer['Days Since Last Visit']}")
                            
                            # Check if this customer has alerts
                            customer_alerts = [alert for alert in alerts if alert['Customer'] == customer_name]
                            if customer_alerts:
                                st.error(f"🚨 Alert: {customer_alerts[0]['Decline']} decline in recent orders")
                        
                        with col2:
                            # Customer notes section
                            st.markdown("**📝 Customer Notes:**")
                            
                            # Get existing notes
                            note_key = f"customer_{customer_id}_notes"
                            current_notes = st.session_state.customer_notes.get(note_key, "")
                            
                            # Display existing notes
                            if current_notes:
                                st.text_area("Current Notes:", value=current_notes, height=100, key=f"display_{note_key}", disabled=True)
                            else:
                                st.info("No notes yet")
                            
                            # Add new note
                            new_note = st.text_area("Add Note:", key=f"input_{note_key}", height=60, placeholder="Enter customer notes...")
                            
                            col_save, col_clear = st.columns(2)
                            with col_save:
                                if st.button("💾 Save Note", key=f"save_{note_key}"):
                                    if new_note.strip():
                                        if current_notes:
                                            updated_notes = current_notes + "\n\n" + f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] " + new_note.strip()
                                        else:
                                            updated_notes = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] " + new_note.strip()
                                        
                                        st.session_state.customer_notes[note_key] = updated_notes
                                        st.success("Note saved!")
                                        st.rerun()
                            
                            with col_clear:
                                if st.button("🗑️ Clear Notes", key=f"clear_{note_key}"):
                                    st.session_state.customer_notes[note_key] = ""
                                    st.success("Notes cleared!")
                                    st.rerun()
                        
                        # Customer transaction history
                        st.markdown(get_heading("recent_transaction_history"))
                        customer_transactions = df[df['customer_id'] == customer_id].copy()
                        customer_transactions = customer_transactions.sort_values('day', ascending=False)
                        
                        if not customer_transactions.empty:
                            # Show last 10 transactions
                            if 'signed_net' in customer_transactions.columns:
                                recent_transactions = customer_transactions.head(10)[['day', 'item', 'quantity', 'signed_net', 'location']].copy()
                                recent_transactions = recent_transactions.rename(columns={'signed_net': 'total'})
                            else:
                                recent_transactions = customer_transactions.head(10)[['day', 'item', 'quantity', 'line_total', 'location']].copy()
                                recent_transactions = recent_transactions.rename(columns={'line_total': 'total'})
                            recent_transactions.columns = ['Date', 'Item', 'Qty', 'Amount', 'Location']
                            st.dataframe(recent_transactions, use_container_width=True, hide_index=True)
                        else:
                            st.info("No transaction history available")
        
        elif st.session_state.selected_tab == DATA_IMPORT_TAB:
            st.subheader(get_heading("data_import_reconciliation"))
            st.caption("Use this tab to import receipts, reconcile against POS summary CSV, and simulate exclusion rules.")

            # Keep local state for reconciliation inputs
            if "recon_uploaded_csv" not in st.session_state:
                st.session_state.recon_uploaded_csv = None
            if "recon_csv_path" not in st.session_state:
                st.session_state.recon_csv_path = ""

            st.markdown(get_heading("import_range"))
            recon_col1, recon_col2, recon_col3 = st.columns([1, 1, 1])
            with recon_col1:
                recon_start = st.date_input(
                    "Start date (Bangkok)",
                    value=st.session_state.get("sync_start_date", datetime.today().date() - timedelta(days=9)),
                    key="recon_start_date_input",
                )
            with recon_col2:
                recon_end = st.date_input(
                    "End date (Bangkok)",
                    value=st.session_state.get("sync_end_date", datetime.today().date()),
                    key="recon_end_date_input",
                )
            with recon_col3:
                stores_map = db.get_stores_map()
                store_options = ["All Stores"] + [f"{name} ({sid[:8]})" for sid, name in stores_map.items()]
                selected_store_display = st.selectbox("Store scope", store_options, key="recon_store_scope")
                selected_store_id = None
                if selected_store_display != "All Stores":
                    selected_store_id = selected_store_display.split("(")[-1].replace(")", "")
                    # Recover full ID from prefix
                    for sid in stores_map.keys():
                        if sid.startswith(selected_store_id):
                            selected_store_id = sid
                            break

            mode = st.radio(
                "Run mode",
                ["Import + Reconcile", "Reconcile only (no new import)"],
                horizontal=True,
                key="recon_mode",
            )

            # CSV input
            st.markdown(get_heading("pos_csv_input"))
            st.session_state.recon_uploaded_csv = st.file_uploader(
                "Upload POS summary CSV (Thai export format)",
                type=["csv"],
                key="recon_csv_upload",
            )
            st.session_state.recon_csv_path = st.text_input(
                "Or local CSV path",
                value=st.session_state.recon_csv_path,
                placeholder="/Users/win/Downloads/sales-summary-2026-02-01-2026-02-10.csv",
                key="recon_csv_path_input",
            )

            def _load_csv_for_reconciliation():
                raw_csv = None
                if st.session_state.recon_uploaded_csv is not None:
                    raw_csv = pd.read_csv(st.session_state.recon_uploaded_csv)
                elif st.session_state.recon_csv_path and os.path.exists(st.session_state.recon_csv_path):
                    raw_csv = pd.read_csv(st.session_state.recon_csv_path)
                if raw_csv is None:
                    return None

                rename_map = {
                    "วันที่": "date",
                    "ยอดขายรวม": "csv_gross_sales",
                    "การคืนเงิน": "csv_refunds",
                    "ส่วนลด": "csv_discount",
                    "ยอดขายสุทธิ": "csv_net",
                }
                csv_df = raw_csv.rename(columns=rename_map)
                needed_cols = {"date", "csv_gross_sales", "csv_refunds", "csv_net"}
                if not needed_cols.issubset(set(csv_df.columns)):
                    return None
                csv_df["date"] = pd.to_datetime(csv_df["date"], dayfirst=True, errors="coerce").dt.date
                csv_df = csv_df[csv_df["date"].notna()].copy()
                return csv_df[["date", "csv_gross_sales", "csv_refunds", "csv_net"]]

            def _get_receipt_level_df():
                conn = db.get_connection()
                receipts_core = pd.read_sql_query(
                    """
                    SELECT receipt_id, receipt_number, created_at, receipt_date, store_id, receipt_type,
                           total_money, total_discount, source, dining_option
                    FROM receipts
                    """,
                    conn,
                )
                payments_map = pd.read_sql_query(
                    """
                    SELECT receipt_id,
                           MIN(COALESCE(payment_name, payment_type, 'Unknown')) AS payment_name
                    FROM payments
                    GROUP BY receipt_id
                    """,
                    conn,
                )
                conn.close()
                out = receipts_core.merge(payments_map, on="receipt_id", how="left")
                out["payment_name"] = out["payment_name"].fillna("Unknown")
                out["created_at"] = pd.to_datetime(out["created_at"], utc=True, errors="coerce")
                out["receipt_date"] = pd.to_datetime(out["receipt_date"], utc=True, errors="coerce")
                out["event_ts"] = out["receipt_date"].fillna(out["created_at"])
                out["day_bkk"] = out["event_ts"].dt.tz_convert("Asia/Bangkok").dt.date
                out = out[(out["day_bkk"] >= recon_start) & (out["day_bkk"] <= recon_end)]
                if selected_store_id:
                    out = out[out["store_id"] == selected_store_id]
                out["receipt_net"] = out["total_money"].fillna(0) - out["total_discount"].fillna(0)
                out["signed_net"] = out.apply(
                    lambda x: -x["receipt_net"] if str(x["receipt_type"]).lower() == "refund" else x["receipt_net"],
                    axis=1,
                )
                return out

            def _guardrail_import(receipts_payload):
                conn = db.get_connection()
                existing_core_query = """
                    SELECT receipt_id, receipt_number, store_id, created_at, receipt_date, total_money
                    FROM receipts
                    WHERE DATE(COALESCE(receipt_date, created_at)) >= ? AND DATE(COALESCE(receipt_date, created_at)) <= ?
                """
                params = [recon_start.isoformat(), recon_end.isoformat()]
                if selected_store_id:
                    existing_core_query += " AND store_id = ?"
                    params.append(selected_store_id)
                existing_core = pd.read_sql_query(existing_core_query, conn, params=params)
                conn.close()

                existing_receipt_ids = set(existing_core["receipt_id"].dropna().astype(str).tolist())
                existing_number_keys = set(
                    zip(
                        existing_core["store_id"].fillna("").astype(str),
                        existing_core["receipt_number"].fillna("").astype(str),
                    )
                )
                existing_time_amount_store_keys = set(
                    zip(
                        existing_core["created_at"].fillna("").astype(str),
                        existing_core["total_money"].fillna(0).astype(float).round(2),
                        existing_core["store_id"].fillna("").astype(str),
                    )
                )

                unique_receipts = []
                duplicate_by_id = 0
                duplicate_by_number = 0
                time_amount_collisions = 0
                for r in receipts_payload:
                    rid = str(r.get("id") or r.get("receipt_number") or "")
                    rnum = str(r.get("receipt_number") or "")
                    rstore = str(r.get("store_id") or "")
                    rcreated = str(r.get("created_at") or "")
                    rtotal = round(float(r.get("total_money", 0) or 0), 2)

                    if rid and rid in existing_receipt_ids:
                        duplicate_by_id += 1
                        continue
                    if rnum and (rstore, rnum) in existing_number_keys:
                        duplicate_by_number += 1
                        continue
                    if (rcreated, rtotal, rstore) in existing_time_amount_store_keys:
                        time_amount_collisions += 1

                    unique_receipts.append(r)
                    if rid:
                        existing_receipt_ids.add(rid)
                    if rnum:
                        existing_number_keys.add((rstore, rnum))
                return unique_receipts, duplicate_by_id, duplicate_by_number, time_amount_collisions

            if st.button("▶️ Run Import/Reconciliation", type="primary", key="run_recon_workflow"):
                if recon_start > recon_end:
                    st.error("Start date must be <= end date.")
                else:
                    if mode == "Import + Reconcile":
                        with st.spinner("Importing receipts with guardrails..."):
                            fetched = fetch_all_receipts(LOYVERSE_TOKEN, recon_start, recon_end, selected_store_id)
                            if fetched:
                                unique_receipts, dup_id, dup_num, weak_collisions = _guardrail_import(fetched)
                                saved = db.save_receipts(unique_receipts)
                                db.update_sync_time("receipts", f"{saved} receipts (recon tab)")
                                st.success(f"Imported {saved} receipts")
                                st.info(f"Skipped duplicates -> by ID: {dup_id}, by receipt number: {dup_num}")
                                if weak_collisions > 0:
                                    st.info(
                                        f"Same-time/same-amount collisions detected: {weak_collisions} "
                                        "(kept, not auto-removed)."
                                    )
                            else:
                                st.warning("No receipts fetched for selected range.")

                    receipt_df = _get_receipt_level_df()
                    if receipt_df.empty:
                        st.warning("No DB receipts in selected range.")
                    else:
                        # DB daily aggregates
                        sale_only = receipt_df[receipt_df["receipt_type"].str.upper() == "SALE"]
                        refund_only = receipt_df[receipt_df["receipt_type"].str.upper() == "REFUND"]
                        db_daily = pd.DataFrame({"date": sorted(receipt_df["day_bkk"].unique())})
                        db_daily = db_daily.merge(
                            sale_only.groupby("day_bkk", as_index=False).agg(db_gross_sales=("total_money", "sum")).rename(columns={"day_bkk": "date"}),
                            on="date",
                            how="left",
                        ).merge(
                            refund_only.groupby("day_bkk", as_index=False).agg(db_refunds=("total_money", "sum")).rename(columns={"day_bkk": "date"}),
                            on="date",
                            how="left",
                        ).merge(
                            receipt_df.groupby("day_bkk", as_index=False).agg(db_signed_net=("signed_net", "sum"), db_receipts=("receipt_id", "nunique")).rename(columns={"day_bkk": "date"}),
                            on="date",
                            how="left",
                        )
                        for col in ["db_gross_sales", "db_refunds", "db_signed_net", "db_receipts"]:
                            db_daily[col] = db_daily[col].fillna(0)

                        csv_daily = _load_csv_for_reconciliation()
                        if csv_daily is not None:
                            recon_daily = csv_daily.merge(db_daily, on="date", how="outer").sort_values("date")
                            recon_daily["delta_gross"] = recon_daily["db_gross_sales"] - recon_daily["csv_gross_sales"]
                            recon_daily["delta_refunds"] = recon_daily["db_refunds"] - recon_daily["csv_refunds"]
                            recon_daily["delta_net"] = recon_daily["db_signed_net"] - recon_daily["csv_net"]

                            st.markdown(get_heading("daily_reconciliation"))
                            st.dataframe(recon_daily, use_container_width=True, hide_index=True)

                            m1, m2, m3 = st.columns(3)
                            m1.metric("Total Net Delta (DB-CSV)", f"{recon_daily['delta_net'].sum():,.0f}")
                            m2.metric("Total Gross Delta (DB-CSV)", f"{recon_daily['delta_gross'].sum():,.0f}")
                            m3.metric("Total Refund Delta (DB-CSV)", f"{recon_daily['delta_refunds'].sum():,.0f}")

                            st.markdown(get_heading("delta_diagnostics"))
                            dcol1, dcol2, dcol3 = st.columns(3)
                            with dcol1:
                                st.markdown(get_heading("by_receipt_type_db"))
                                st.dataframe(
                                    receipt_df.groupby("receipt_type", as_index=False).agg(receipts=("receipt_id", "nunique"), signed_net=("signed_net", "sum")),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            with dcol2:
                                st.markdown(get_heading("by_store_db"))
                                st.dataframe(
                                    receipt_df.groupby("store_id", as_index=False).agg(receipts=("receipt_id", "nunique"), signed_net=("signed_net", "sum")),
                                    use_container_width=True,
                                    hide_index=True,
                                )
                            with dcol3:
                                st.markdown(get_heading("by_payment_db"))
                                st.dataframe(
                                    receipt_df.groupby("payment_name", as_index=False).agg(receipts=("receipt_id", "nunique"), signed_net=("signed_net", "sum")).sort_values("signed_net", ascending=False).head(20),
                                    use_container_width=True,
                                    hide_index=True,
                                )

                            st.markdown(get_heading("candidate_exclusion_set"))
                            day_options = sorted([d for d in recon_daily["date"].dropna().tolist()])
                            selected_day = st.selectbox("Target day for exclusion suggestion", day_options, key="recon_target_day")
                            day_row = recon_daily[recon_daily["date"] == selected_day]
                            if not day_row.empty:
                                day_delta = float(day_row["delta_net"].iloc[0])
                                st.write(f"Delta on {selected_day}: **{day_delta:,.0f}** (DB - CSV)")
                                if day_delta > 0:
                                    # Suggest receipts to exclude to close positive delta.
                                    day_sales = receipt_df[
                                        (receipt_df["day_bkk"] == selected_day)
                                        & (receipt_df["receipt_type"].str.upper() == "SALE")
                                    ][["receipt_id", "receipt_number", "created_at", "store_id", "payment_name", "signed_net"]].copy()
                                    day_sales = day_sales.sort_values("signed_net", ascending=False)
                                    day_sales["cum_net"] = day_sales["signed_net"].cumsum()
                                    suggestion = day_sales[day_sales["cum_net"] <= day_delta + 500].head(50)
                                    st.caption("Greedy candidate set (largest sale receipts first):")
                                    st.dataframe(suggestion, use_container_width=True, hide_index=True)
                                else:
                                    st.info("No positive delta for selected day; exclusion not needed.")

                            st.markdown(get_heading("exclusion_simulator"))
                            sim_col1, sim_col2, sim_col3 = st.columns(3)
                            with sim_col1:
                                exclude_stores = st.multiselect(
                                    "Exclude stores",
                                    sorted(receipt_df["store_id"].dropna().unique().tolist()),
                                    key="sim_exclude_stores",
                                )
                            with sim_col2:
                                exclude_types = st.multiselect(
                                    "Exclude receipt types",
                                    sorted(receipt_df["receipt_type"].dropna().unique().tolist()),
                                    key="sim_exclude_types",
                                )
                            with sim_col3:
                                exclude_payments = st.multiselect(
                                    "Exclude payments",
                                    sorted(receipt_df["payment_name"].dropna().unique().tolist()),
                                    key="sim_exclude_payments",
                                )

                            simulated = receipt_df.copy()
                            if exclude_stores:
                                simulated = simulated[~simulated["store_id"].isin(exclude_stores)]
                            if exclude_types:
                                simulated = simulated[~simulated["receipt_type"].isin(exclude_types)]
                            if exclude_payments:
                                simulated = simulated[~simulated["payment_name"].isin(exclude_payments)]

                            sim_daily = simulated.groupby("day_bkk", as_index=False).agg(sim_signed_net=("signed_net", "sum")).rename(columns={"day_bkk": "date"})
                            sim_join = recon_daily.merge(sim_daily, on="date", how="left")
                            sim_join["sim_signed_net"] = sim_join["sim_signed_net"].fillna(0)
                            sim_join["sim_delta_net"] = sim_join["sim_signed_net"] - sim_join["csv_net"]
                            st.dataframe(sim_join[["date", "csv_net", "db_signed_net", "sim_signed_net", "delta_net", "sim_delta_net"]], use_container_width=True, hide_index=True)
                            st.metric("Simulated Total Net Delta", f"{sim_join['sim_delta_net'].sum():,.0f}")
                        else:
                            st.warning("CSV not found or invalid format. Upload or provide a valid POS summary CSV path.")
                            st.markdown(get_heading("db_daily_totals_without_csv"))
                            st.dataframe(db_daily, use_container_width=True, hide_index=True)

        # --- Download ---
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col2:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Full Data", csv, "receipts_export.csv", "text/csv", use_container_width=True)
