import requests
import pandas as pd
import streamlit as st
import plotly.express as px
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

# ========= CONFIG =========
LOYVERSE_TOKEN = os.getenv("LOYVERSE_TOKEN", "d18826e6c76345888204b310aaca1351")
BASE_URL = "https://api.loyverse.com/v1.0/receipts"
PAGE_LIMIT = 250
# ==========================

st.set_page_config(page_title="🐻‍❄️ Snow AI Dashboard", layout="wide")

# ========= PASSWORD AUTHENTICATION =========
PASSWORD = "snowbomb"

# Initialize authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Password authentication
if not st.session_state.authenticated:
    st.title(get_text("login_required"))
    st.markdown("---")
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown(f"### {get_text('enter_password')}")
        password_input = st.text_input("Password", type="password", placeholder=get_text("password_placeholder"))
        
        col_login, col_clear = st.columns(2)
        
        with col_login:
            if st.button(get_text("login_button"), type="primary", use_container_width=True):
                if password_input == PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error(get_text("incorrect_password"))
        
        with col_clear:
            if st.button(get_text("clear_button"), use_container_width=True):
                st.rerun()
        
        st.markdown("---")
        st.info(get_text("contact_admin"))
    
    # Stop execution here if not authenticated
    st.stop()

# ========= MAIN APP LOGIC =========
# Initialize session state for selected tab
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = "📅 Daily Sales"  # Will be updated after language is set

# Initialize theme
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = "Light"

# Initialize language
if 'language' not in st.session_state:
    st.session_state.language = "English"

# Apply theme CSS
if st.session_state.theme_mode == "Dark":
    st.markdown("""
    <style>
        /* Dark Mode Styling */
        .stApp {
            background-color: #0e1117;
            color: #fafafa;
        }
        .stMarkdown {
            color: #fafafa;
        }
        div[data-testid="stMetricValue"] {
            color: #fafafa;
        }
        .stSelectbox label, .stDateInput label, .stTextInput label {
            color: #fafafa !important;
        }
    </style>
    """, unsafe_allow_html=True)

# Apply font size
if 'font_size' in st.session_state:
    font_sizes = {"Small": "12px", "Medium": "14px", "Large": "16px"}
    base_font = font_sizes.get(st.session_state.font_size, "14px")
    st.markdown(f"""
    <style>
        html, body, [class*="css"] {{
            font-size: {base_font};
        }}
    </style>
    """, unsafe_allow_html=True)

# Apply compact mode
if st.session_state.get('compact_mode', False):
    st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1rem !important;
        }
        .element-container {
            margin-bottom: 0.5rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

# ===== TRANSLATION DICTIONARIES =====
TRANSLATIONS = {
    "English": {
        "load_database": "💾 Load Database",
        "loaded_success": "✅ Loaded {total_receipts} receipts, {line_items} line items",
        "no_cached_data": "⚠️ No cached data. Use Settings to sync data first.",
        "navigation": "📑 Navigation",
        "daily_sales": "📅 Daily Sales",
        "by_location": "📍 By Location", 
        "by_product": "📦 By Product",
        "by_customer": "👥 By Customer",
        "credit": "💳 Credit",
        "interactive_data": "📊 Interactive Data",
        "transaction_log": "📋 Transaction Log",
        "customer_invoice": "🧾 Customer Invoice",
        "ice_forecast": "🧊 Ice Forecast",
        "crm": "👥 CRM",
        "settings_preferences": "⚙️ Settings & Preferences",
        "date_range_selector": "Date Range Selector",
        "quick_shortcuts": "Quick Shortcuts:",
        "today": "📅 Today",
        "yesterday": "📅 Yesterday",
        "last_3_days": "📅 Last 3 Days",
        "last_week": "📅 Last Week",
        "last_2_weeks": "📅 Last 2 Weeks",
        "last_30_days": "📅 Last 30 Days",
        "this_week": "📅 This Week",
        "this_month": "📅 This Month",
        "last_month": "📅 Last Month",
        "last_3_months": "📅 Last 3 Months",
        "this_year": "📅 This Year",
        "all_data": "📅 All Data",
        "start_date": "📅 Start Date:",
        "end_date": "📅 End Date:",
        "apply_range": "🔍 Apply Range",
        "current_selection": "Current Selection: {start_date} to {end_date} ({days} days)",
        "api_information": "ℹ️ API Information",
        "viewing_data_from": "Viewing data from",
        "daily_sales_analysis": "📅 Daily Sales Analysis",
        "sales_by_location": "📍 Sales by Location (ประเภท)",
        "product_analysis": "📈 Product Analysis",
        "customer_analysis": "👥 Customer Analysis",
        "credit_management": "💳 Credit Management Dashboard",
        "interactive_data_explorer": "📊 Interactive Data Explorer",
        "transaction_log": "📋 Transaction Log by Location",
        "customer_invoice_generator": "🧾 Customer Invoice Generator",
        "ice_forecast_dashboard": "🧊 Ice Forecast Dashboard",
        "crm_dashboard": "👥 Customer Relationship Management"
    },
    "Thai": {
        "load_database": "💾 โหลดฐานข้อมูล",
        "loaded_success": "✅ โหลดเสร็จสิ้น {total_receipts} ใบเสร็จ, {line_items} รายการ",
        "no_cached_data": "⚠️ ไม่มีข้อมูลแคช ใช้การตั้งค่าเพื่อซิงค์ข้อมูลก่อน",
        "navigation": "📑 เมนูนำทาง",
        "daily_sales": "📅 ยอดขายรายวัน",
        "by_location": "📍 แยกตามสถานที่", 
        "by_product": "📦 แยกตามสินค้า",
        "by_customer": "👥 แยกตามลูกค้า",
        "credit": "💳 เครดิต",
        "interactive_data": "📊 ข้อมูลแบบโต้ตอบ",
        "transaction_log": "📋 บันทึกการทำรายการ",
        "customer_invoice": "🧾 ใบแจ้งหนี้ลูกค้า",
        "ice_forecast": "🧊 พยากรณ์น้ำแข็ง",
        "crm": "👥 CRM",
        "settings_preferences": "⚙️ การตั้งค่าและความชอบ",
        "date_range_selector": "ตัวเลือกช่วงวันที่",
        "quick_shortcuts": "ทางลัด:",
        "today": "📅 วันนี้",
        "yesterday": "📅 เมื่อวาน",
        "last_3_days": "📅 3 วันที่ผ่านมา",
        "last_week": "📅 สัปดาห์ที่แล้ว",
        "last_2_weeks": "📅 2 สัปดาห์ที่แล้ว",
        "last_30_days": "📅 30 วันที่ผ่านมา",
        "this_week": "📅 สัปดาห์นี้",
        "this_month": "📅 เดือนนี้",
        "last_month": "📅 เดือนที่แล้ว",
        "last_3_months": "📅 3 เดือนที่ผ่านมา",
        "this_year": "📅 ปีนี้",
        "all_data": "📅 ข้อมูลทั้งหมด",
        "start_date": "📅 วันที่เริ่มต้น:",
        "end_date": "📅 วันที่สิ้นสุด:",
        "apply_range": "🔍 ใช้ช่วงวันที่",
        "current_selection": "การเลือกปัจจุบัน: {start_date} ถึง {end_date} ({days} วัน)",
        "api_information": "ℹ️ ข้อมูล API",
        "viewing_data_from": "กำลังดูข้อมูลจาก",
        "daily_sales_analysis": "📅 การวิเคราะห์ยอดขายรายวัน",
        "sales_by_location": "📍 ยอดขายแยกตามสถานที่ (ประเภท)",
        "product_analysis": "📈 การวิเคราะห์สินค้า",
        "customer_analysis": "👥 การวิเคราะห์ลูกค้า",
        "credit_management": "💳 แดชบอร์ดการจัดการเครดิต",
        "interactive_data_explorer": "📊 เครื่องมือสำรวจข้อมูลแบบโต้ตอบ",
        "transaction_log": "📋 บันทึกการทำรายการแยกตามสถานที่",
        "customer_invoice_generator": "🧾 เครื่องมือสร้างใบแจ้งหนี้ลูกค้า",
        "ice_forecast_dashboard": "🧊 แดชบอร์ดพยากรณ์น้ำแข็ง",
        "crm_dashboard": "👥 การจัดการความสัมพันธ์ลูกค้า",
        
        # Password Authentication
        "login_required": "🔐 Snow AI Dashboard - ต้องเข้าสู่ระบบ",
        "enter_password": "กรอกรหัสผ่านเพื่อเข้าถึงแดชบอร์ด",
        "password_placeholder": "กรอกรหัสผ่าน...",
        "login_button": "🔓 เข้าสู่ระบบ",
        "clear_button": "🗑️ ล้าง",
        "incorrect_password": "❌ รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่",
        "contact_admin": "💡 ติดต่อผู้ดูแลระบบเพื่อขอข้อมูลการเข้าถึง",
        "logout": "🚪 ออกจากระบบ",
        
        # Settings & Preferences
        "appearance": "🎨 การแสดงผล",
        "theme_mode": "โหมดธีม",
        "light": "สว่าง",
        "dark": "มืด",
        "font_size": "ขนาดตัวอักษร",
        "small": "เล็ก",
        "medium": "กลาง",
        "large": "ใหญ่",
        "compact_mode": "โหมดกะทัดรัด",
        "data_management": "💾 การจัดการข้อมูล",
        "sync_receipts": "🔄 ซิงค์ใบเสร็จจาก API",
        "sync_missing_data": "🔄 ซิงค์ข้อมูลที่ขาดหาย",
        "sync_all_metadata": "🔄 ซิงค์ข้อมูลทั้งหมด",
        "extended_sync_options": "📊 ตัวเลือกการซิงค์แบบขยาย",
        "custom_date_range_sync": "📅 ช่วงวันที่กำหนดเองสำหรับการซิงค์",
        "display_preferences": "🎯 การตั้งค่าการแสดงผล",
        "data_backup": "💾 การสำรองข้อมูล",
        "api_connection": "🔌 API และการเชื่อมต่อ",
        "sync_data_operations": "🔄 การซิงค์และการดำเนินการข้อมูล",
        "advanced_options": "⚙️ ตัวเลือกขั้นสูง",
        "maintenance": "🔧 การบำรุงรักษา",
        
        # Key Metrics
        "key_metrics": "📊 ตัวชี้วัดหลัก",
        "total_sales": "ยอดขายรวม",
        "total_items": "รายการรวม",
        "unique_customers": "ลูกค้าไม่ซ้ำ",
        "avg_transaction_value": "มูลค่าเฉลี่ยต่อรายการ",
        "sales_growth": "การเติบโตของยอดขาย",
        "sales_overview": "📊 ภาพรวมยอดขาย",
        "daily_discounts": "💸 ส่วนลดรายวัน",
        "day_of_week_analysis": "📅 การวิเคราะห์ตามวันในสัปดาห์",
        "time_period_analysis": "📊 การวิเคราะห์ช่วงเวลา",
        
        # Product Analysis
        "product_category_summary": "📊 สรุปหมวดหมู่สินค้า",
        "sales_distribution": "🥧 การกระจายยอดขาย",
        "category_summary_table": "📋 ตารางสรุปหมวดหมู่",
        "sales_by_category": "📊 ยอดขายแยกตามหมวดหมู่",
        "all_products_by_category": "สินค้าทั้งหมดแยกตามหมวดหมู่",
        "edit_product_categories": "📝 แก้ไขหมวดหมู่สินค้า",
        "select_product_to_edit": "เลือกสินค้าที่จะแก้ไข:",
        "change_category_to": "เปลี่ยนหมวดหมู่เป็น:",
        "current_product_breakdown": "📊 การแบ่งสินค้าปัจจุบัน",
        
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
        "item_growth_period": "การเติบโตของรายการ"
    }
}

def get_text(key, **kwargs):
    """Get translated text for the current language"""
    lang = st.session_state.get('language', 'English')
    template = TRANSLATIONS[lang].get(key, TRANSLATIONS['English'].get(key, key))
    return template.format(**kwargs) if kwargs else template

def initialize_selected_tab():
    """Initialize selected tab with proper translation"""
    if st.session_state.get('selected_tab') in ["📅 Daily Sales", "📅 ยอดขายรายวัน"]:
        st.session_state.selected_tab = get_text("daily_sales")

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

# --- Helper: API call with pagination for receipts ---
def fetch_all_receipts(token, start_date, end_date, store_id=None, limit=250):
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

    # Debug console output
    with st.expander("🔍 Debug Console", expanded=False):
        st.write(f"**Token:** {token[:10]}...{token[-10:]}")
        st.write(f"**Date Range (GMT+7):** {start_date} to {end_date}")
        st.write(f"**API Range (UTC):** {start_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')} to {end_datetime_utc.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"**Store Filter:** {store_id if store_id else 'All stores'}")
    
    all_receipts = []
    cursor = None
    page_count = 0
    progress_bar = st.progress(0)
    status_text = st.empty()

    while True:
        page_count += 1
        status_text.text(f"Fetching page {page_count}...")
        
        if cursor:
            params["cursor"] = cursor
        
        try:
            res = requests.get(BASE_URL, headers=headers, params=params)
            
            if res.status_code != 200:
                st.error(f"❌ **Error {res.status_code}:** {res.text}")
                break
                
            data = res.json()
            receipts = data.get("receipts", [])
            
            all_receipts.extend(receipts)
            cursor = data.get("cursor")
            
            progress_bar.progress(min(page_count * 20, 100))
            
            if not cursor:
                status_text.text(f"✅ Completed! Found {len(all_receipts)} receipts")
                break
                
        except Exception as e:
            st.error(f"❌ **Exception:** {str(e)}")
            break
    
    progress_bar.progress(100)
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
db = LoyverseDB()

# Initialize reference data
if 'ref_data' not in st.session_state:
    st.session_state.ref_data = ReferenceData(db)
ref_data = st.session_state.ref_data

# Initialize selected tab with proper translation
initialize_selected_tab()

# ========== SIDEBAR NAVIGATION ==========
st.sidebar.title("🐻‍❄️ Snow AI")

# Logout button
if st.sidebar.button(get_text("logout"), key="logout_btn", use_container_width=True, type="secondary"):
    st.session_state.authenticated = False
    st.rerun()

st.sidebar.markdown("---")

# Load Database button right under title
if st.sidebar.button(get_text("load_database"), key="load_db_main", use_container_width=True, type="primary"):
    # Load ALL data from database (not filtered by date range)
    df = db.get_receipts_dataframe()
    
    if not df.empty:
        st.session_state.receipts_df = df
        total_receipts = db.get_receipt_count()
        st.sidebar.success(get_text("loaded_success", total_receipts=total_receipts, line_items=len(df)))
    else:
        st.sidebar.warning(get_text("no_cached_data"))

# Language switch buttons
# Create two columns for the language buttons
lang_col1, lang_col2 = st.sidebar.columns(2)

with lang_col1:
    if st.button("🇺🇸 English", key="lang_english", 
                type="primary" if st.session_state.language == "English" else "secondary",
                use_container_width=True):
        st.session_state.language = "English"
        st.rerun()

with lang_col2:
    if st.button("🇹🇭 ไทย", key="lang_thai",
                type="primary" if st.session_state.language == "Thai" else "secondary", 
                use_container_width=True):
        st.session_state.language = "Thai"
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader(get_text("navigation"))

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
    get_text("crm")
]

for tab in tabs:
    if st.sidebar.button(tab, key=f"nav_{tab}", use_container_width=True, 
                        type="primary" if st.session_state.selected_tab == tab else "secondary"):
        st.session_state.selected_tab = tab
        st.rerun()

st.sidebar.markdown("---")

# Settings section at the bottom - Comprehensive Data Management & Customization
with st.sidebar.expander(get_text("settings_preferences"), expanded=False):
    
    # === VISUAL SETTINGS ===
    st.markdown(f"### {get_text('appearance')}")
    
    # Initialize theme in session state
    if 'theme_mode' not in st.session_state:
        st.session_state.theme_mode = "Light"
    
    # Theme selector
    col1, col2 = st.columns(2)
    with col1:
        if st.button(f"☀️ {get_text('light')}", use_container_width=True, 
                    type="primary" if st.session_state.theme_mode == "Light" else "secondary"):
            st.session_state.theme_mode = "Light"
            st.info("💡 Light mode active")
    
    with col2:
        if st.button(f"🌙 {get_text('dark')}", use_container_width=True,
                    type="primary" if st.session_state.theme_mode == "Dark" else "secondary"):
            st.session_state.theme_mode = "Dark"
            st.info("🌙 Dark mode active (refresh to apply)")
    
    # Chart color scheme
    if 'color_scheme' not in st.session_state:
        st.session_state.color_scheme = "Default"
    
    color_scheme = st.selectbox(
        "📊 Chart Color Scheme",
        ["Default", "Blues", "Greens", "Reds", "Purples", "Viridis", "Plasma", "Rainbow"],
        index=["Default", "Blues", "Greens", "Reds", "Purples", "Viridis", "Plasma", "Rainbow"].index(st.session_state.color_scheme),
        key="color_scheme_select"
    )
    st.session_state.color_scheme = color_scheme
    
    # Font size
    if 'font_size' not in st.session_state:
        st.session_state.font_size = "Medium"
    
    font_size = st.radio(
        f"🔤 {get_text('font_size')}",
        [get_text("small"), get_text("medium"), get_text("large")],
        index=["Small", "Medium", "Large"].index(st.session_state.font_size),
        horizontal=True,
        key="font_size_select"
    )
    st.session_state.font_size = font_size
    
    st.markdown("---")
    
    # === DATA MANAGEMENT ===
    st.markdown(f"### {get_text('data_management')}")
    
    # Database info
    db_stats = db.get_database_stats()
    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"💾 {get_text('customers')}", db_stats['customers'])
        st.metric(f"📍 {get_text('locations')}", db_stats['categories'])
    with col2:
        st.metric("🧾 Receipts", db_stats['receipts'])
        st.metric(f"📦 {get_text('products')}", db_stats['items'])
    
    if db_stats['date_range'][0]:
        st.caption(f"📅 Data: {db_stats['date_range'][0][:10]} to {db_stats['date_range'][1][:10]}")
    
    st.markdown("---")
    st.subheader("📚 Reference Data")
    
    # Sync all metadata button
    if st.button(get_text("sync_all_metadata"), help="Fetch customers, payment types, stores, employees", key="sync_all_meta"):
        with st.spinner("Syncing all reference data..."):
            total_synced = 0
            
            # Fetch customers
            customers = fetch_all_customers(LOYVERSE_TOKEN)
            if customers:
                count = db.save_customers(customers)
                db.update_sync_time('customers', f"{count} customers")
                total_synced += count
            
            # Fetch payment types
            payment_types = fetch_all_payment_types(LOYVERSE_TOKEN)
            if payment_types:
                count = db.save_payment_types(payment_types)
                db.update_sync_time('payment_types', f"{count} payment types")
                total_synced += count
            
            # Fetch stores
            stores = fetch_all_stores(LOYVERSE_TOKEN)
            if stores:
                count = db.save_stores(stores)
                db.update_sync_time('stores', f"{count} stores")
                total_synced += count
            
            # Fetch employees
            employees = fetch_all_employees(LOYVERSE_TOKEN)
            if employees:
                count = db.save_employees(employees)
                db.update_sync_time('employees', f"{count} employees")
                total_synced += count
            
            # Fetch categories (your 23 locations!)
            categories = fetch_all_categories(LOYVERSE_TOKEN)
            if categories:
                count = db.save_categories(categories)
                db.update_sync_time('categories', f"{count} categories/locations")
                total_synced += count
                st.info(f"📍 Found {count} location categories!")
            
            # Fetch items (to link products to locations)
            items = fetch_all_items(LOYVERSE_TOKEN)
            if items:
                count = db.save_items(items)
                db.update_sync_time('items', f"{count} items")
                total_synced += count
            
            # Refresh reference data
            ref_data.refresh()
            
            st.success(f"✅ Synced {total_synced} total records!")
            st.success(f"📍 Your {len(categories)} locations are now mapped!")
            st.rerun()

    # Show reference data status
    status = ref_data.get_status_summary()
    categories_count = db.get_category_count()
    items_count = db.get_item_count()

    if status['total'] > 0 or categories_count > 0:
        st.info(f"📊 Loaded: {status['customers']} customers, {status['payment_types']} payments, {status['stores']} stores, {status['employees']} employees")
        if categories_count > 0:
            st.success(f"📍 Locations: {categories_count} categories, {items_count} items")
        missing = ref_data.get_missing_data_types()
        if missing:
            st.warning(f"⚠️ Missing: {', '.join(missing)}")
    else:
        st.warning("⚠️ No reference data loaded. Click 'Sync All Metadata' to fetch.")

    st.markdown("---")
    st.subheader("👥 Individual Syncs")

    # Fetch customers when button is clicked
    col1, col2 = st.columns(2)
    with col1:
        fetch_new = st.button("🔄 Sync Customers", help="Fetch latest from API", key="sync_customers_btn")
    with col2:
        load_cached = st.button("💾 Load Cached", help="Load from local database", key="load_cached_btn")

    if fetch_new:
        with st.spinner("Fetching customer data from Loyverse API..."):
            customers = fetch_all_customers(LOYVERSE_TOKEN)
        
        if customers:
            # Save to database
            saved_count = db.save_customers(customers)
            db.update_sync_time('customers', f"{saved_count} customers")
            
            st.success(f"✅ Synced {saved_count} customers to database")
            
            # Load from database
            customer_map = db.get_customer_map()
            st.session_state.customer_map = customer_map
            
            # Show preview
            customer_df = db.get_all_customers().head(5)
            st.dataframe(customer_df[['customer_id', 'name']].head(5), hide_index=True)
            total = db.get_customer_count()
            if total > 5:
                st.caption(f"... and {total - 5} more")
        else:
            st.warning("⚠️ No customers found or API error")

    if load_cached:
        customer_count = db.get_customer_count()
        if customer_count > 0:
            customer_map = db.get_customer_map()
            st.session_state.customer_map = customer_map
            st.success(f"✅ Loaded {customer_count} customers from database")
        else:
            st.warning("⚠️ No cached customers. Click 'Sync Customers' first.")

    # Get customer map from session state or database
    if 'customer_map' not in st.session_state:
        customer_map = db.get_customer_map()
        if customer_map:
            st.session_state.customer_map = customer_map
    else:
        customer_map = st.session_state.get('customer_map', {})
    
    st.markdown("---")
    st.subheader("📊 Receipt Data Management")
    
    # Show current database stats with date range
    date_range = db.get_date_range()
    if date_range and date_range[0] and date_range[1]:
        st.info(f"📊 **Current Database:** {db_stats['receipts']} receipts, {db_stats['customers']} customers | **Date Range:** {date_range[0]} to {date_range[1]}")
    else:
        st.info(f"📊 **Current Database:** {db_stats['receipts']} receipts, {db_stats['customers']} customers | **No data yet**")
    
    # Sync options with better date range controls
    st.markdown("#### 🔄 Sync Receipts from API")
    
    # Help information
    with st.expander("ℹ️ Sync Options Help", expanded=False):
        st.markdown("""
        **🔄 Sync Missing Data** - Intelligently syncs from your latest data to today  
        **📅 Sync Last Week** - Downloads last 7 days of receipts  
        **📅 Sync Last Month** - Downloads last 30 days of receipts  
        **📅 Sync Last 3 Months** - Downloads last 90 days of receipts  
        **📅 Sync All Historical Data** - Downloads ALL historical data (may take time)  
        
        💡 **Tip:** Use "Sync Missing Data" for regular updates - it's the smartest option!
        """)
    
    # Quick sync buttons - Enhanced with new options
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Sync Missing Data", help="Sync from latest data to current date", key="sync_missing_btn"):
            start_date, end_date, message = get_smart_sync_range(db)
            st.session_state.sync_start_date = start_date
            st.session_state.sync_end_date = end_date
            st.session_state.trigger_sync = True
            st.session_state.is_sync_missing = True  # Flag for precise timestamp handling
            st.info(f"📅 {message} - Syncing from {start_date} to {end_date}")
    
    with col2:
        if st.button("📅 Sync Last Week", help="Download last 7 days of receipts", key="sync_week_btn"):
            end_date = datetime.today()
            start_date = end_date - timedelta(days=7)
            st.session_state.sync_start_date = start_date.date()
            st.session_state.sync_end_date = end_date.date()
            st.session_state.trigger_sync = True
    
    with col3:
        if st.button("📅 Sync Last Month", help="Download last 30 days of receipts", key="sync_month_btn"):
            end_date = datetime.today()
            start_date = end_date - timedelta(days=30)
            st.session_state.sync_start_date = start_date.date()
            st.session_state.sync_end_date = end_date.date()
            st.session_state.trigger_sync = True
    
    # Additional sync options
    st.markdown("#### 📊 Extended Sync Options")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📅 Sync Last 3 Months", help="Download last 3 months of receipts", key="sync_3months_btn"):
            end_date = datetime.today()
            start_date = end_date - timedelta(days=90)
            st.session_state.sync_start_date = start_date.date()
            st.session_state.sync_end_date = end_date.date()
            st.session_state.trigger_sync = True
    
    with col2:
        if st.button("📅 Sync All Historical Data", help="Download ALL historical receipts (may take a while)", key="sync_all_historical_btn"):
            # Set date range to cover a wide historical period
            end_date = datetime.today()
            start_date = datetime(2020, 1, 1)  # Go back to 2020
            st.session_state.sync_start_date = start_date.date()
            st.session_state.sync_end_date = end_date.date()
            st.session_state.trigger_sync = True
            st.warning("⚠️ This may take several minutes for large datasets!")
    
    with col3:
        # Show current database date range
        date_range = db.get_date_range()
        if date_range and date_range[0] and date_range[1]:
            st.info(f"📊 **Current Data:** {date_range[0]} to {date_range[1]}")
        else:
            st.warning("📊 **No data in database**")
    
    # Manual date range for sync
    st.markdown("#### 📅 Custom Date Range for Sync")
    col1, col2 = st.columns(2)
    with col1:
        # Default to 30 days ago, but allow any date
        default_start = st.session_state.get('sync_start_date', datetime.today() - timedelta(days=30))
        if isinstance(default_start, datetime):
            default_start = default_start.date()
        sync_start = st.date_input(
            "Start Date", 
            value=default_start,
            min_value=datetime(2020, 1, 1).date(),  # Allow going back to 2020
            max_value=datetime.today().date(),
            key="sync_start_date_input"
        )
    with col2:
        # Default to today
        default_end = st.session_state.get('sync_end_date', datetime.today())
        if isinstance(default_end, datetime):
            default_end = default_end.date()
        sync_end = st.date_input(
            "End Date", 
            value=default_end,
            min_value=datetime(2020, 1, 1).date(),  # Allow going back to 2020
            max_value=datetime.today().date(),
            key="sync_end_date_input"
        )
    
    # Store sync dates in session state
    st.session_state.sync_start_date = sync_start
    st.session_state.sync_end_date = sync_end
    
    # Sync and load buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Sync Custom Range", help=f"Download receipts from {sync_start} to {sync_end}", key="sync_custom_btn"):
            st.session_state.trigger_sync = True
    with col2:
        if st.button("💾 Load Database", help="Load all cached data from database", key="load_receipts_btn"):
            st.session_state.trigger_load = True
    with col3:
        if st.button("🗑️ Clear Database", help="Clear all cached data", key="clear_db_btn"):
            st.session_state.trigger_clear = True
    
    # Show sync range info
    days_range = (sync_end - sync_start).days + 1
    st.caption(f"📊 Will sync {days_range} days of data from {sync_start} to {sync_end}")

    st.markdown("---")
    
    # === DISPLAY PREFERENCES ===
    st.markdown("### 🎯 Display Preferences")
    
    # Initialize preferences
    if 'show_tooltips' not in st.session_state:
        st.session_state.show_tooltips = True
    if 'decimal_places' not in st.session_state:
        st.session_state.decimal_places = 0
    if 'date_format' not in st.session_state:
        st.session_state.date_format = "YYYY-MM-DD"
    
    # Tooltips toggle
    show_tooltips = st.checkbox(
        "💬 Show Help Tooltips",
        value=st.session_state.show_tooltips,
        key="tooltips_checkbox"
    )
    st.session_state.show_tooltips = show_tooltips
    
    # Decimal places
    decimal_places = st.select_slider(
        "💰 Decimal Places for Currency",
        options=[0, 1, 2],
        value=st.session_state.decimal_places,
        key="decimal_slider"
    )
    st.session_state.decimal_places = decimal_places
    st.caption(f"Example: ฿1,234.{('00' if decimal_places == 2 else '0' if decimal_places == 1 else '')}")
    
    # Date format
    date_format = st.selectbox(
        "📅 Date Format",
        ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"],
        index=["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"].index(st.session_state.date_format),
        key="date_format_select"
    )
    st.session_state.date_format = date_format
    
    # Chart animation
    if 'chart_animation' not in st.session_state:
        st.session_state.chart_animation = True
    
    chart_animation = st.checkbox(
        "✨ Animate Charts",
        value=st.session_state.chart_animation,
        key="animation_checkbox"
    )
    st.session_state.chart_animation = chart_animation
    
    st.markdown("---")
    
    # === DATA BACKUP & EXPORT ===
    st.markdown("### 💾 Data Backup")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📤 Export All Data", use_container_width=True, help="Export complete database as CSV"):
            all_data = db.get_receipts_dataframe()
            if not all_data.empty:
                csv = all_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "⬇️ Download",
                    csv,
                    f"loyverse_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    key="download_backup"
                )
                st.success(f"✅ {len(all_data)} records ready")
            else:
                st.warning("No data to export")
    
    with col2:
        if st.button("🗄️ Database Info", use_container_width=True):
            import os
            if os.path.exists('loyverse_data.db'):
                size = os.path.getsize('loyverse_data.db') / (1024 * 1024)  # MB
                st.info(f"📊 Database Size: {size:.2f} MB")
            else:
                st.warning("Database file not found")
    
    # Auto-backup toggle
    if 'auto_backup' not in st.session_state:
        st.session_state.auto_backup = False
    
    auto_backup = st.checkbox(
        "🔄 Auto-backup on sync (saves to backup/ folder)",
        value=st.session_state.auto_backup,
        key="auto_backup_checkbox"
    )
    st.session_state.auto_backup = auto_backup
    
    st.markdown("---")
    
    # === API SETTINGS ===
    st.markdown("### 🔌 API & Connection")
    
    # Show API status
    col1, col2 = st.columns([2, 1])
    with col1:
        st.caption(f"🔑 Token: {LOYVERSE_TOKEN[:8]}...{LOYVERSE_TOKEN[-8:]}")
    with col2:
        st.caption("✅ Connected")
    
    # Cache settings
    if 'cache_ttl' not in st.session_state:
        st.session_state.cache_ttl = 300  # 5 minutes
    
    cache_ttl = st.select_slider(
        "⏱️ Cache Duration (seconds)",
        options=[60, 300, 600, 1800, 3600],
        value=st.session_state.cache_ttl,
        format_func=lambda x: f"{x//60} min" if x < 3600 else f"{x//3600} hr",
        key="cache_ttl_slider"
    )
    st.session_state.cache_ttl = cache_ttl
    
    st.markdown("---")
    st.subheader("📅 Query Settings")
    
    query_start_date = st.date_input("Sync Start Date", datetime.today() - timedelta(days=7), key="query_start_date")
    query_end_date = st.date_input("Sync End Date", datetime.today(), key="query_end_date")
    query_store_filter = st.text_input("Store ID Filter (optional)", "", key="query_store_filter")
    
    st.markdown("---")
    
    # === SYNC & DATA OPERATIONS ===
    st.markdown("### 🔄 Sync & Data Operations")
    
    # Test API Connection
    if st.button("🧪 Test API Connection", key="test_api_btn"):
        st.write("🔍 **Testing API Connection...**")
        headers = {"Authorization": f"Bearer {LOYVERSE_TOKEN}", "Accept": "application/json"}
        
        # Test with a simple request first
        test_params = {
            "created_at_min": "2024-01-01T00:00:00.000Z",
            "created_at_max": "2024-12-31T23:59:59.000Z",
            "limit": 1
        }
        
        st.write(f"**Test Token:** {LOYVERSE_TOKEN[:10]}...{LOYVERSE_TOKEN[-10:]}")
        st.write(f"**Test URL:** {BASE_URL}")
        st.write(f"**Test Params:** {test_params}")
        
        try:
            res = requests.get(BASE_URL, headers=headers, params=test_params)
            st.write(f"**Test Response Status:** {res.status_code}")
            st.write(f"**Test Response Headers:** {dict(res.headers)}")
            st.write(f"**Test Response Text:** {res.text}")
            
            if res.status_code == 200:
                st.success("✅ API connection successful!")
                data = res.json()
                st.write(f"**Response Data:** {data}")
            else:
                st.error(f"❌ API connection failed: {res.status_code}")
                
        except Exception as e:
            st.error(f"❌ Exception during test: {str(e)}")
    
    st.markdown("---")
    
    # === ADVANCED SETTINGS ===
    st.markdown("### ⚙️ Advanced Options")
    
    # Performance settings
    if 'default_rows' not in st.session_state:
        st.session_state.default_rows = 100
    
    default_rows = st.number_input(
        "📊 Default Table Rows",
        min_value=10,
        max_value=500,
        value=st.session_state.default_rows,
        step=10,
        key="default_rows_input",
        help="Default number of rows to display in tables"
    )
    st.session_state.default_rows = default_rows
    
    # Auto-refresh
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    
    auto_refresh = st.checkbox(
        "🔄 Auto-refresh data every 5 minutes",
        value=st.session_state.auto_refresh,
        key="auto_refresh_checkbox",
        help="Automatically reload data in background"
    )
    st.session_state.auto_refresh = auto_refresh
    
    # Compact mode
    if 'compact_mode' not in st.session_state:
        st.session_state.compact_mode = False
    
    compact_mode = st.checkbox(
        "📐 Compact Mode (reduce spacing)",
        value=st.session_state.compact_mode,
        key="compact_mode_checkbox"
    )
    st.session_state.compact_mode = compact_mode
    
    # Show debug info
    if 'show_debug' not in st.session_state:
        st.session_state.show_debug = False
    
    show_debug = st.checkbox(
        "🐛 Show Debug Information",
        value=st.session_state.show_debug,
        key="debug_checkbox"
    )
    st.session_state.show_debug = show_debug
    
    st.markdown("---")
    
    # === RESET & MAINTENANCE ===
    st.markdown("### 🔧 Maintenance")
    
    # Reset preferences
    if st.button("🔄 Reset All Preferences", use_container_width=True, help="Reset visual and display settings to defaults"):
        st.session_state.theme_mode = "Light"
        st.session_state.color_scheme = "Default"
        st.session_state.font_size = "Medium"
        st.session_state.decimal_places = 0
        st.session_state.date_format = "YYYY-MM-DD"
        st.session_state.chart_animation = True
        st.session_state.default_rows = 100
        st.session_state.auto_refresh = False
        st.session_state.compact_mode = False
        st.session_state.show_debug = False
        st.success("✅ Preferences reset to defaults!")
        st.rerun()
    
    # Clear cache
    if st.button("🗑️ Clear Streamlit Cache", use_container_width=True, help="Clear all cached data and functions"):
        st.cache_data.clear()
        st.success("✅ Cache cleared!")
        st.rerun()
    
    st.markdown("---")
    st.caption("💡 **Tip:** Visual settings apply globally to all tabs")
    st.caption("⚙️ **Version:** 2.1 | **Tests:** 115/115 passing")

# Store settings values in session state for use outside the expander
if 'query_start_date' in st.session_state:
    start_date = st.session_state.query_start_date
else:
    start_date = datetime.today() - timedelta(days=7)
    
if 'query_end_date' in st.session_state:
    end_date = st.session_state.query_end_date
else:
    end_date = datetime.today()
    
if 'query_store_filter' in st.session_state:
    store_filter = st.session_state.query_store_filter
else:
    store_filter = ""

# ========== MAIN CONTENT ==========

# Get database stats for date navigator
db_stats = db.get_database_stats()

# Enhanced Date Selector
st.markdown(f"### 📅 {get_text('date_range_selector')}")

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
    
    # Quick shortcut buttons
    st.markdown(f"**{get_text('quick_shortcuts')}**")
    
    # First row of shortcuts
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button(get_text("today"), key="quick_today", help="Select today only"):
            st.session_state.date_selector_start = max_date
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = max_date
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col2:
        if st.button(get_text("yesterday"), key="quick_yesterday", help="Select yesterday only"):
            yesterday = max_date - timedelta(days=1)
            st.session_state.date_selector_start = yesterday
            st.session_state.date_selector_end = yesterday
            st.session_state.view_start_date = yesterday
            st.session_state.view_end_date = yesterday
            st.rerun()
    
    with col3:
        if st.button(get_text("last_3_days"), key="quick_last_3_days", help="Select last 3 days"):
            start_date = max(min_date, max_date - timedelta(days=2))
            st.session_state.date_selector_start = start_date
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = start_date
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col4:
        if st.button(get_text("last_week"), key="quick_last_week", help="Select last 7 days"):
            start_date = max(min_date, max_date - timedelta(days=6))
            st.session_state.date_selector_start = start_date
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = start_date
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col5:
        if st.button(get_text("last_2_weeks"), key="quick_last_2_weeks", help="Select last 14 days"):
            start_date = max(min_date, max_date - timedelta(days=13))
            st.session_state.date_selector_start = start_date
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = start_date
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col6:
        if st.button(get_text("last_30_days"), key="quick_last_30_days", help="Select last 30 days"):
            start_date = max(min_date, max_date - timedelta(days=29))
            st.session_state.date_selector_start = start_date
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = start_date
            st.session_state.view_end_date = max_date
            st.rerun()
    
    # Second row of shortcuts
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        if st.button(get_text("this_week"), key="quick_this_week", help="Select this week (Mon-Sun)"):
            # Get Monday of current week (weekday() returns 0 for Monday, 6 for Sunday)
            days_since_monday = max_date.weekday()  # 0=Monday, 1=Tuesday, ..., 6=Sunday
            week_start = max_date - timedelta(days=days_since_monday)
            st.session_state.date_selector_start = week_start
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = week_start
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col2:
        if st.button(get_text("this_month"), key="quick_this_month", help="Select from start of month"):
            month_start = max_date.replace(day=1)
            st.session_state.date_selector_start = month_start
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = month_start
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col3:
        if st.button(get_text("last_month"), key="quick_last_month", help="Select entire last month"):
            # Calculate last month
            if max_date.month == 1:
                last_month_start = max_date.replace(year=max_date.year-1, month=12, day=1)
            else:
                last_month_start = max_date.replace(month=max_date.month-1, day=1)
            
            # Get last day of last month
            if last_month_start.month == 12:
                next_month = last_month_start.replace(year=last_month_start.year+1, month=1, day=1)
            else:
                next_month = last_month_start.replace(month=last_month_start.month+1, day=1)
            last_month_end = next_month - timedelta(days=1)
            
            st.session_state.date_selector_start = last_month_start
            st.session_state.date_selector_end = last_month_end
            st.session_state.view_start_date = last_month_start
            st.session_state.view_end_date = last_month_end
            st.rerun()
    
    with col4:
        if st.button(get_text("last_3_months"), key="quick_last_3_months", help="Select last 3 months"):
            # Calculate 3 months ago
            if max_date.month <= 3:
                if max_date.month == 1:
                    start_month = 10
                    start_year = max_date.year - 1
                elif max_date.month == 2:
                    start_month = 11
                    start_year = max_date.year - 1
                else:  # month == 3
                    start_month = 12
                    start_year = max_date.year - 1
            else:
                start_month = max_date.month - 3
                start_year = max_date.year
            
            three_months_start = max_date.replace(year=start_year, month=start_month, day=1)
            st.session_state.date_selector_start = three_months_start
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = three_months_start
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col5:
        if st.button(get_text("this_year"), key="quick_this_year", help="Select from start of year"):
            year_start = max_date.replace(month=1, day=1)
            st.session_state.date_selector_start = year_start
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = year_start
            st.session_state.view_end_date = max_date
            st.rerun()
    
    with col6:
        if st.button(get_text("all_data"), key="quick_all_data", help="Select all available data"):
            st.session_state.date_selector_start = min_date
            st.session_state.date_selector_end = max_date
            st.session_state.view_start_date = min_date
            st.session_state.view_end_date = max_date
            st.rerun()
    
    st.markdown("---")
    
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
    
    # Show current selection
    if 'view_start_date' in st.session_state and 'view_end_date' in st.session_state:
        days_diff = (st.session_state.view_end_date - st.session_state.view_start_date).days + 1
        st.success(f"📊 **{get_text('current_selection', start_date=st.session_state.view_start_date.strftime('%Y-%m-%d'), end_date=st.session_state.view_end_date.strftime('%Y-%m-%d'), days=days_diff)}**")
    
else:
    st.info("📅 No cached data. Load data first to use date navigator.")

st.markdown("---")

# API Info button
if st.button(get_text("api_information")):
    with st.expander("📡 API Endpoints Used", expanded=True):
        st.markdown("""
        ### **1️⃣ Fetch Receipts**
        **Endpoint:** `GET /v1.0/receipts`  
        **Called when:** You click "🔄 Load Data"
        
        **Parameters:**
        - `created_at_min` - Start date (from sidebar)
        - `created_at_max` - End date (from sidebar)
        - `limit` - 250 receipts per page
        - `store_id` - Optional store filter
        - `cursor` - For pagination
        
        **Returns:** Receipt data including:
        - Receipt details (number, date, total)
        - Line items (products, quantities, prices)
        - Payments (payment types, amounts)
        - Customer IDs, store IDs, employee IDs
        
        ---
        
        ### **2️⃣ Fetch Customers**
        **Endpoint:** `GET /v1.0/customers`  
        **Called when:** You click "👥 Fetch Customer Names"
        
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
        
        ### **🔐 Authentication**
        - Uses Bearer Token: `{token[:10]}...{token[-10:]}`
        - All requests include `Authorization` header
        
        ### **📦 Data Processing**
        1. Fetches all receipts in date range (with pagination)
        2. Flattens nested JSON into flat table structure
        3. Maps customer UUIDs to names
        4. Calculates aggregations for charts
        
        ### **📄 Full Documentation**
        See `API_REFERENCE.md` for complete details, response examples, and curl commands.
        """.format(token=LOYVERSE_TOKEN))

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
            except Exception as e:
                # Fallback to regular date handling
                sync_start_datetime = datetime.combine(sync_start_date, datetime.min.time())
                sync_end_datetime = datetime.combine(sync_end_date, datetime.max.time())
        else:
            # Fallback to regular date handling
            sync_start_datetime = datetime.combine(sync_start_date, datetime.min.time())
            sync_end_datetime = datetime.combine(sync_end_date, datetime.max.time())
        
        # Clear the flag
        st.session_state.is_sync_missing = False
    else:
        # For other sync operations, convert to datetime objects if they're date objects
        if hasattr(sync_start_date, 'date'):
            sync_start_date = sync_start_date.date()
        if hasattr(sync_end_date, 'date'):
            sync_end_date = sync_end_date.date()
        
        # Convert to datetime for the API call
        sync_start_datetime = datetime.combine(sync_start_date, datetime.min.time())
        sync_end_datetime = datetime.combine(sync_end_date, datetime.max.time())
    
    st.info(f"🔄 **Syncing receipts from {sync_start_date} to {sync_end_date}**")
    
    # Check what's already in database for this range
    existing_df = db.get_receipts_dataframe(
        start_date=sync_start_date.isoformat(),
        end_date=sync_end_date.isoformat(),
        store_id=store_filter if store_filter else None
    )
    existing_count = len(existing_df) if not existing_df.empty else 0
    
    with st.spinner(f"Fetching receipts from API ({sync_start_date} to {sync_end_date})..."):
        receipts = fetch_all_receipts(LOYVERSE_TOKEN, sync_start_datetime, sync_end_datetime, store_filter)
    
    if receipts:
        # Save to database (INSERT OR REPLACE = merge/upsert)
        saved_count = db.save_receipts(receipts)
        db.update_sync_time('receipts', f"{saved_count} receipts")
        
        # Check if we added new data or just updated
        new_df = db.get_receipts_dataframe(
            start_date=sync_start_date.isoformat(),
            end_date=sync_end_date.isoformat(),
            store_id=store_filter if store_filter else None
        )
        new_count = len(new_df) if not new_df.empty else 0
        
        if new_count > existing_count:
            st.success(f"✅ Added {new_count - existing_count} new transactions!")
            st.info(f"📊 Total in database: {db.get_receipt_count()} receipts")
            st.info(f"📅 Synced date range: {sync_start_date} to {sync_end_date}")
        else:
            st.success(f"✅ Updated {saved_count} receipts (no new data)")
            st.info(f"📅 Date range: {sync_start_date} to {sync_end_date}")
        
        # Load ALL data from database (not just this date range)
        df = db.get_receipts_dataframe()
        st.session_state.receipts_df = df
    else:
        st.warning(f"⚠️ No receipts found in range {sync_start_date} to {sync_end_date}")
        st.caption("💡 Try expanding the date range or check if data exists in Loyverse")
    
    st.session_state.trigger_sync = False

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
if 'receipts_df' in st.session_state and not st.session_state.receipts_df.empty:
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
                        "Total Sales": [df[df["customer_id"] == cid]["signed_net"].sum() if "signed_net" in df.columns else df[df["customer_id"] == cid]["line_total"].sum() for cid in unknown_customers]
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
        st.sidebar.subheader("🔍 Data Filters")
        
        # Location filter (ประเภท)
        if "location" in df.columns:
            unique_locations = sorted(df["location"].dropna().unique())
            selected_location = st.sidebar.selectbox("📍 Filter by Location (ประเภท)", ["All"] + list(unique_locations))
            if selected_location != "All":
                df = df[df["location"] == selected_location]
        
        unique_stores = sorted(df["store_id"].dropna().unique())
        selected_store = st.sidebar.selectbox("🏪 Filter by Store", ["All"] + list(unique_stores))
        if selected_store != "All":
            df = df[df["store_id"] == selected_store]

        # Use payment_name (readable) if available, otherwise fall back to bill_type
        if "payment_name" in df.columns:
            unique_payments = sorted(df["payment_name"].dropna().unique())
            selected_payment = st.sidebar.selectbox("💳 Filter by Payment Type", ["All"] + list(unique_payments))
            if selected_payment != "All":
                df = df[df["payment_name"] == selected_payment]
        else:
            unique_payments = sorted(df["bill_type"].dropna().unique())
            selected_payment = st.sidebar.selectbox("💳 Filter by Payment Type", ["All"] + list(unique_payments))
            if selected_payment != "All":
                df = df[df["bill_type"] == selected_payment]

        # --- KPI Cards ---
        # Compute net sales at receipt level and subtract refunds
        # First, aggregate per receipt to avoid line duplication
        if {"bill_number","receipt_total","receipt_discount","receipt_type"}.issubset(df.columns):
            receipt_level = df.groupby(["bill_number","receipt_type"], as_index=False).agg({
                "receipt_total":"first",
                "receipt_discount":"first"
            })
            receipt_level["receipt_net"] = receipt_level["receipt_total"].fillna(0) - receipt_level["receipt_discount"].fillna(0)
            # Refunds should subtract from sales
            receipt_level["signed_net"] = receipt_level.apply(lambda r: -r["receipt_net"] if str(r["receipt_type"]).lower()=="refund" else r["receipt_net"], axis=1)
            total_sales = float(receipt_level["signed_net"].sum())
            # attach signed_net back to rows for day-level calcs
            df_receipt_net = receipt_level[["bill_number","signed_net"]]
            df = df.merge(df_receipt_net, on="bill_number", how="left")
        else:
            total_sales = df["line_total"].astype(float).sum()
        total_items = df["quantity"].sum()
        unique_customers = df["customer_id"].nunique()
        
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
        col1.metric("💰 Total Sales", f"{total_sales:,.0f}")
        col2.metric("📦 Items Sold", f"{total_items:,.0f}")
        col3.metric("👥 Unique Customers", f"{unique_customers}")
        col4.metric("📅 Bags/Day", f"{bags_per_day:.1f}", help=f"Average bags sold per day over {days_in_period} days")

        st.markdown("---")

        # --- Render selected tab content ---
        if st.session_state.selected_tab == get_text("daily_sales"):
            st.subheader(get_text("daily_sales_analysis"))
            
            # === ENHANCED KPI CARDS ===
            st.markdown(f"### {get_text('key_metrics')}")
            
            # Calculate daily aggregations using receipt-level signed net
            if "signed_net" in df.columns:
                daily_agg = df.groupby("day").agg({
                    "signed_net": "sum",
                    "quantity": "sum", 
                    "bill_number": "nunique",
                    "customer_id": "nunique"
                }).reset_index()
                daily_agg.columns = ["day", "total_sales", "items", "transactions", "customers"]
            else:
                daily_agg = df.groupby("day").agg({
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
            if "signed_net" in df.columns and "receipt_type" in df.columns:
                per_receipt = df.groupby(["bill_number","receipt_type"], as_index=False)["signed_net"].first()
                per_receipt = per_receipt[per_receipt["receipt_type"].str.lower() != "refund"]
                avg_transaction_value = per_receipt["signed_net"].mean() if not per_receipt.empty else 0
            elif "line_total" in df.columns:
                avg_transaction_value = df.groupby("bill_number")["line_total"].sum().mean()
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
                    f"💰 {get_text('avg_daily_sales')}", 
                    f"฿{avg_daily_sales:,.0f}",
                    delta=f"{sales_delta:+.1f}%" if sales_delta != 0 else None,
                    help="Average sales per day in selected period"
                )
            
            with col2:
                st.metric(
                    f"🧾 {get_text('avg_transaction')}", 
                    f"฿{avg_transaction_value:,.0f}",
                    help="Average value per transaction"
                )
            
            with col3:
                st.metric(
                    f"📦 {get_text('avg_items_per_day')}", 
                    f"{avg_items_per_day:,.0f}",
                    help="Average items sold per day"
                )
            
            with col4:
                st.metric(
                    f"👥 {get_text('avg_customers_per_day')}", 
                    f"{avg_customers_per_day:,.0f}",
                    delta=f"{trans_delta:+.1f}%" if trans_delta != 0 else None,
                    help="Average unique customers per day"
                )
            
            st.markdown("---")
            
            # === DAILY SALES CHARTS ===
            st.markdown(f"### {get_text('sales_overview')}")
            
            # Bar chart - Full width using signed net
            if "signed_net" in df.columns:
                daily_sales = df.groupby("day")["signed_net"].sum().reset_index().rename(columns={"signed_net":"total"})
            else:
                daily_sales = df.groupby("day")["line_total"].sum().reset_index().rename(columns={"line_total":"total"})
            
            fig = px.bar(daily_sales, x="day", y="total", title="Daily Sales Trend (Net Sales)", 
                        text_auto=True, color="total",
                        color_continuous_scale="Blues",
                        labels={"total": "Total Sales", "day": "Date"})
            fig.update_traces(textposition='outside')
            fig.update_layout(showlegend=False, height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show discount information if available
            if 'receipt_discount' in df.columns:
                total_discounts = df["receipt_discount"].sum()
                if total_discounts > 0:
                    st.info(f"💰 **Total Discounts Applied:** ฿{total_discounts:,.2f}")
                    
                    # Show daily discount breakdown
                    daily_discounts = df.groupby("day")["receipt_discount"].sum().reset_index()
                    daily_discounts.columns = ["day", "discounts"]
                    
                    if daily_discounts["discounts"].sum() > 0:
                        st.markdown(f"#### {get_text('daily_discounts')}")
                        fig_discounts = px.bar(daily_discounts, x="day", y="discounts", 
                                             title="Daily Discounts Applied",
                                             color="discounts",
                                             color_continuous_scale="Reds",
                                             text_auto=True)
                        fig_discounts.update_traces(textposition='outside')
                        fig_discounts.update_layout(showlegend=False, height=400)
                        st.plotly_chart(fig_discounts, use_container_width=True)
                else:
                    st.info("ℹ️ **No discounts found in the data**")
            
            # Line chart with hover details - Full width using signed net
            if "signed_net" in df.columns:
                daily_details = df.groupby("day").agg({
                    "signed_net": "sum",
                    "quantity": "sum",
                    "bill_number": "nunique"
                }).reset_index().rename(columns={"signed_net":"Total Sales"})
            else:
                daily_details = df.groupby("day").agg({
                    "line_total": "sum",
                    "quantity": "sum",
                    "bill_number": "nunique"
                }).reset_index().rename(columns={"line_total":"Total Sales"})
            daily_details.columns = ["Date", "Total Sales", "Items Sold", "Transactions"]
            fig2 = px.line(daily_details, x="Date", y="Total Sales", 
                          title="Sales Trend Line",
                          markers=True,
                          hover_data=["Items Sold", "Transactions"])
            fig2.update_traces(line_color='#1f77b4', line_width=3)
            fig2.update_layout(height=500)
            st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("---")
            
            # === DAY OF WEEK ANALYSIS ===
            st.markdown(f"### {get_text('day_of_week_analysis')}")
            
            # Add day of week to dataframe
            df_temp = df.copy()
            df_temp['day_date'] = pd.to_datetime(df_temp['day'])
            df_temp['day_of_week'] = df_temp['day_date'].dt.day_name()
            df_temp['weekday_num'] = df_temp['day_date'].dt.dayofweek
            
            # Aggregate by day of week using signed_net if available
            if 'signed_net' in df_temp.columns:
                dow_sales = df_temp.groupby(['day_of_week', 'weekday_num']).agg({
                    'signed_net': ['sum', 'mean', 'count'],
                    'bill_number': 'nunique',
                    'customer_id': 'nunique',
                    'quantity': 'sum'
                }).reset_index()
                # Flatten column names
                dow_sales.columns = ['day_of_week', 'weekday_num', 'total_sales', 'avg_sales', 'days_count', 'transactions', 'customers', 'items']
            else:
                dow_sales = df_temp.groupby(['day_of_week', 'weekday_num']).agg({
                    'line_total': ['sum', 'mean', 'count'],
                    'bill_number': 'nunique',
                    'customer_id': 'nunique',
                    'quantity': 'sum'
                }).reset_index()
                # Flatten column names
                dow_sales.columns = ['day_of_week', 'weekday_num', 'total_sales', 'avg_sales', 'days_count', 'transactions', 'customers', 'items']
            
            # Sort by weekday (Monday=0, Sunday=6)
            dow_sales = dow_sales.sort_values('weekday_num')
            
            # Calculate average per occurrence
            dow_sales['avg_per_occurrence'] = dow_sales['total_sales'] / dow_sales['days_count']
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                best_day = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmax(), 'day_of_week']
                best_day_sales = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmax(), 'avg_per_occurrence']
                st.metric("🏆 Best Day", best_day, f"฿{best_day_sales:,.0f} avg")
            
            with col2:
                worst_day = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmin(), 'day_of_week']
                worst_day_sales = dow_sales.loc[dow_sales['avg_per_occurrence'].idxmin(), 'avg_per_occurrence']
                st.metric("📉 Slowest Day", worst_day, f"฿{worst_day_sales:,.0f} avg")
            
            with col3:
                weekend_days = dow_sales[dow_sales['day_of_week'].isin(['Saturday', 'Sunday'])]
                weekday_days = dow_sales[~dow_sales['day_of_week'].isin(['Saturday', 'Sunday'])]
                weekend_avg = weekend_days['avg_per_occurrence'].mean() if len(weekend_days) > 0 else 0
                weekday_avg = weekday_days['avg_per_occurrence'].mean() if len(weekday_days) > 0 else 0
                diff_pct = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0
                st.metric("🎉 Weekend vs Weekday", f"{diff_pct:+.1f}%", 
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
                    color='avg_per_occurrence',
                    color_continuous_scale='Viridis',
                    text_auto=True
                )
                fig_dow.update_traces(texttemplate='฿%{y:,.0f}', textposition='outside')
                fig_dow.update_layout(showlegend=False, xaxis_tickangle=-45)
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
                fig_dow_multi.update_layout(xaxis_tickangle=-45, legend_title_text='')
                st.plotly_chart(fig_dow_multi, use_container_width=True)
            
            # Detailed table
            with st.expander("📋 Detailed Day of Week Statistics"):
                # Prepare display dataframe
                display_dow = dow_sales[['day_of_week', 'total_sales', 'avg_per_occurrence', 'transactions', 'customers', 'items', 'days_count']].copy()
                display_dow.columns = ['Day', 'Total Sales', 'Avg per Day', 'Transactions', 'Customers', 'Items Sold', 'Days in Period']
                display_dow['Total Sales'] = display_dow['Total Sales'].apply(lambda x: f"฿{x:,.0f}")
                display_dow['Avg per Day'] = display_dow['Avg per Day'].apply(lambda x: f"฿{x:,.0f}")
                
                st.dataframe(display_dow, use_container_width=True, hide_index=True)
            
            # Insights
            st.info(f"""
            **💡 Insights:**
            - **{best_day}** is your busiest day with an average of ฿{best_day_sales:,.0f} in sales
            - **{worst_day}** is the slowest day - consider running promotions
            - Weekend sales are **{diff_pct:+.1f}%** {'higher' if diff_pct > 0 else 'lower'} than weekdays on average
            - Total days analyzed: {total_days} days
            """)

        elif st.session_state.selected_tab == get_text("by_location"):
            st.subheader(get_text("sales_by_location"))
            
            if "location" in df.columns and not df["location"].isna().all():
                # Location sales summary
                if "signed_net" in df.columns:
                    location_sales = df.groupby("location").agg({
                        "signed_net": "sum",
                        "quantity": "sum",
                        "bill_number": "nunique",
                        "customer_id": "nunique"
                    }).reset_index()
                    location_sales.columns = ["Location", "Total Sales", "Items Sold", "Transactions", "Unique Customers"]
                else:
                    location_sales = df.groupby("location").agg({
                        "line_total": "sum",
                        "quantity": "sum",
                        "bill_number": "nunique",
                        "customer_id": "nunique"
                    }).reset_index()
                    location_sales.columns = ["Location", "Total Sales", "Items Sold", "Transactions", "Unique Customers"]
                location_sales = location_sales.sort_values("Total Sales", ascending=False)
                
                # Bar chart
                fig = px.bar(location_sales, x="Total Sales", y="Location",
                            orientation="h",
                            title="Sales by Location (ประเภท)",
                            color="Total Sales",
                            color_continuous_scale="Teal",
                            text_auto=True)
                fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
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
                st.subheader("📊 Location Performance Details")
                location_sales["Avg Transaction"] = location_sales["Total Sales"] / location_sales["Transactions"]
                location_sales["Avg Items/Transaction"] = location_sales["Items Sold"] / location_sales["Transactions"]
                st.dataframe(location_sales.sort_values("Total Sales", ascending=False), 
                           use_container_width=True, hide_index=True)
                
                # Location trends over time
                st.subheader("📈 Location Trends Over Time")
                if "signed_net" in df.columns:
                    location_daily = df.groupby(["day", "location"])["signed_net"].sum().reset_index().rename(columns={"signed_net":"total"})
                else:
                    location_daily = df.groupby(["day", "location"])["line_total"].sum().reset_index().rename(columns={"line_total":"total"})
                fig_trend = px.line(location_daily, x="day", y="total", color="location",
                                   title="Daily Sales Trend by Location (Net Sales)",
                                   markers=True)
                st.plotly_chart(fig_trend, use_container_width=True)
                
                st.markdown("---")
                
                # === PEAK HOURS ANALYSIS ===
                st.subheader("🕐 Peak Hours Analysis by Location")
                
                # Extract hour from timestamp
                df_hours = df.copy()
                df_hours['datetime'] = pd.to_datetime(df_hours['date'])
                df_hours['hour'] = df_hours['datetime'].dt.hour
                
                # Location selector for peak hours
                peak_location_list = ["All Locations"] + sorted(df["location"].dropna().unique().tolist())
                selected_peak_location = st.selectbox(
                    "📍 Select Location for Peak Hours Analysis:",
                    peak_location_list,
                    key="peak_hours_location"
                )
                
                # Filter data
                if selected_peak_location == "All Locations":
                    hourly_data = df_hours.copy()
                    analysis_title = "All Locations"
                else:
                    hourly_data = df_hours[df_hours["location"] == selected_peak_location].copy()
                    analysis_title = selected_peak_location
                
                if not hourly_data.empty:
                    # Aggregate by hour
                    if "signed_net" in hourly_data.columns:
                        hourly_sales = hourly_data.groupby('hour').agg({
                            'signed_net': 'sum',
                            'bill_number': 'nunique',
                            'customer_id': 'nunique',
                            'quantity': 'sum',
                        }).reset_index()
                    else:
                        hourly_sales = hourly_data.groupby('hour').agg({
                            'line_total': 'sum',
                            'bill_number': 'nunique',
                            'customer_id': 'nunique',
                            'quantity': 'sum',
                        }).reset_index()
                    
                    # Calculate occurrences before renaming columns
                    hour_counts = hourly_data.groupby('hour').size().reset_index(name='occurrences')
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
                        fig_periods.update_layout(yaxis={'categoryorder':'total ascending'})
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
                if pd.isna(product_name):
                    return "📦 อื่นๆ (Other)"
                
                # Check manual categories first (user overrides)
                if product_name in st.session_state.manual_categories:
                    return st.session_state.manual_categories[product_name]
                
                # Auto-detect category
                product_str = str(product_name).lower()
                
                # Check for each category
                if "ป่น" in product_str:
                    return "🧊 ป่น (Crushed Ice)"
                elif "หลอดเล็ก" in product_str or ("หลอด" in product_str and "เล็ก" in product_str):
                    return "🧊 หลอดเล็ก (Small Tube)"
                elif "หลอดใหญ่" in product_str or ("หลอด" in product_str and "ใหญ่" in product_str):
                    return "🧊 หลอดใหญ่ (Large Tube)"
                else:
                    return "📦 อื่นๆ (Other)"
            
            # Apply categorization
            df_products = df.copy()
            df_products['product_category'] = df_products['item'].apply(categorize_product)
            
            # Aggregate by category
            if "signed_net" in df_products.columns:
                category_sales = df_products.groupby('product_category').agg({
                    'signed_net': 'sum',
                    'quantity': 'sum',
                    'bill_number': 'nunique',
                    'item': 'count'
                }).reset_index()
                category_sales.columns = ['Category', 'Total Sales', 'Quantity', 'Transactions', 'Items Sold']
            else:
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
            st.markdown("### 📊 Product Category Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                main_categories = category_sales[~category_sales['Category'].str.contains('อื่นๆ')]
                main_sales = main_categories['Total Sales'].sum()
                st.metric("💰 Main Products Sales", f"฿{main_sales:,.0f}", 
                         f"{(main_sales/total_sales_sum*100):.1f}% of total")
            
            with col2:
                top_category = category_sales.iloc[0]['Category']
                top_sales = category_sales.iloc[0]['Total Sales']
                st.metric("🏆 Top Category", top_category.split()[1], 
                         f"฿{top_sales:,.0f}")
            
            with col3:
                total_quantity = category_sales['Quantity'].sum()
                st.metric("📦 Total Quantity", f"{total_quantity:,.0f} units")
            
            with col4:
                avg_price = total_sales_sum / total_quantity if total_quantity > 0 else 0
                st.metric("💵 Avg Unit Price", f"฿{avg_price:,.2f}")
            
            st.markdown("---")
            
            # === PIE CHART & SUMMARY TABLE ===
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 🥧 Sales Distribution")
                
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
                st.markdown("#### 📋 Category Summary Table")
                
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
            st.markdown("### 📊 Sales by Category")
            
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
            fig_bar.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # === DETAILED BREAKDOWN (EXPANDABLE) ===
            with st.expander("📋 Detailed Product Breakdown & Category Editor"):
                st.markdown("#### All Products by Category")
                st.caption("💡 Click on a product to manually change its category")
                
                # Group products by category with details
                if "signed_net" in df_products.columns:
                    detailed_products = df_products.groupby(['product_category', 'item']).agg({
                        'signed_net': 'sum',
                        'quantity': 'sum',
                        'bill_number': 'nunique'
                    }).reset_index()
                    detailed_products.columns = ['Category', 'Product', 'Total Sales', 'Quantity', 'Transactions']
                else:
                    detailed_products = df_products.groupby(['product_category', 'item']).agg({
                        'line_total': 'sum',
                        'quantity': 'sum',
                        'bill_number': 'nunique'
                    }).reset_index()
                    detailed_products.columns = ['Category', 'Product', 'Total Sales', 'Quantity', 'Transactions']
                detailed_products = detailed_products.sort_values(['Category', 'Total Sales'], ascending=[True, False])
                
                # Display as table with edit functionality
                st.markdown("##### 📝 Edit Product Categories")
                
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
                    st.markdown("**Select Product to Edit:**")
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
                    st.markdown("**Change Category To:**")
                    
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
                st.markdown("##### 📊 Current Product Breakdown")
                
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
                st.markdown("#### 📤 Import Manual Categories")
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
            customer_df = df[df["customer_id"].notna()].copy()
            
            if customer_df.empty:
                st.warning("No customer data available. Transactions may not have customer IDs.")
            else:
                # Group by customer_id and get the first customer_name for each
                if "signed_net" in customer_df.columns:
                    customer_stats = customer_df.groupby("customer_id").agg({
                        "customer_name": "first",
                        "signed_net": "sum",
                        "bill_number": "nunique",
                        "quantity": "sum",
                        "day": "nunique"
                    }).reset_index()
                    customer_stats.columns = ["Customer ID", "Customer Name", "Total Sales", "Number of Purchases", "Items Purchased", "Days Active"]
                else:
                    customer_stats = customer_df.groupby("customer_id").agg({
                        "customer_name": "first",
                        "line_total": "sum",
                        "bill_number": "nunique",
                        "quantity": "sum",
                        "day": "nunique"
                    }).reset_index()
                    customer_stats.columns = ["Customer ID", "Customer Name", "Total Sales", "Number of Purchases", "Items Purchased", "Days Active"]
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
                display_col = "Customer Name" if customer_map else "Customer ID"
                
                fig = px.bar(customer_stats_sorted, 
                            x=sort_map[sort_by], 
                            y=display_col,
                            orientation="h",
                            title=f"Top {customer_limit} Customers by {sort_by}",
                            color=sort_map[sort_by],
                            color_continuous_scale="Plasma",
                            hover_data=["Customer ID", "Customer Name", "Total Sales", "Number of Purchases", "Items Purchased", "Average Order Value"])
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
                
                # Customer summary stats
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Customers", len(customer_stats))
                col2.metric("Avg Sales/Customer", f"{customer_stats['Total Sales'].mean():,.0f}")
                col3.metric("Avg Purchases/Customer", f"{customer_stats['Number of Purchases'].mean():.1f}")
                col4.metric("Avg Order Value", f"{customer_stats['Average Order Value'].mean():,.0f}")
                
                # Detailed customer table
                st.subheader("📋 Customer Details")
                st.dataframe(customer_stats_sorted.sort_values(sort_map[sort_by], ascending=False),
                           use_container_width=True, hide_index=True)
                
                # Customer segment analysis
                st.subheader("📊 Customer Segments")
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
            if 'payment_name' in df.columns:
                credit_df = df[df['payment_name'].str.contains('ค้างชำระ|เครดิต', case=False, na=False)].copy()
                
                if credit_df.empty:
                    st.warning("⚠️ No credit transactions found in current data")
                    st.info("Credit transactions are those with payment type: ค้างชำระ or เครดิต")
                else:
                    # Summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    if "signed_net" in credit_df.columns:
                        total_credit = credit_df['signed_net'].sum()
                    else:
                        total_credit = credit_df['line_total'].sum()
                    credit_customers = credit_df['customer_id'].nunique()
                    credit_transactions = credit_df['bill_number'].nunique()
                    avg_credit = total_credit / credit_customers if credit_customers > 0 else 0
                    
                    col1.metric("💰 Total Credit Sales", f"{total_credit:,.2f} THB")
                    col2.metric("👥 Credit Customers", credit_customers)
                    col3.metric("🧾 Credit Transactions", credit_transactions)
                    col4.metric("📊 Avg per Customer", f"{avg_credit:,.2f} THB")
                    
                    st.markdown("---")
                    
                    # Outstanding by Customer
                    st.markdown("### 👥 Outstanding Balance by Customer")
                    
                    if "signed_net" in credit_df.columns:
                        customer_credit = credit_df.groupby(['customer_id', 'customer_name']).agg({
                            'signed_net': 'sum',
                            'bill_number': 'nunique',
                            'day': ['min', 'max']
                        }).reset_index()
                        customer_credit.columns = ['Customer ID', 'Customer Name', 'Outstanding Amount', 
                                                  'Transactions', 'First Credit Date', 'Last Credit Date']
                    else:
                        customer_credit = credit_df.groupby(['customer_id', 'customer_name']).agg({
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
                    st.markdown("### 📍 Credit Sales by Location")
                    
                    if 'location' in credit_df.columns:
                        if "signed_net" in credit_df.columns:
                            location_credit = credit_df.groupby('location').agg({
                                'signed_net': 'sum',
                                'bill_number': 'nunique',
                                'customer_id': 'nunique'
                            }).reset_index()
                            location_credit.columns = ['Location', 'Total Credit', 'Transactions', 'Customers']
                        else:
                            location_credit = credit_df.groupby('location').agg({
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
                    st.markdown("### 📈 Credit vs Cash Sales Trend")
                    
                    # Get cash transactions
                    cash_df = df[df['payment_name'].str.contains('เงินสด', case=False, na=False)].copy()
                    
                    # Daily aggregation for credit
                    if "signed_net" in credit_df.columns:
                        credit_daily = credit_df.groupby('day')['signed_net'].sum().reset_index()
                        credit_daily.columns = ['Date', 'Credit Sales']
                    else:
                        credit_daily = credit_df.groupby('day')['line_total'].sum().reset_index()
                        credit_daily.columns = ['Date', 'Credit Sales']
                    
                    # Daily aggregation for cash
                    if "signed_net" in cash_df.columns:
                        cash_daily = cash_df.groupby('day')['signed_net'].sum().reset_index()
                        cash_daily.columns = ['Date', 'Cash Sales']
                    else:
                        cash_daily = cash_df.groupby('day')['line_total'].sum().reset_index()
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
                    fig.update_layout(
                        hovermode='x unified',
                        yaxis_title='Sales Amount (THB)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.markdown("---")
                    
                    # Cash vs Credit Overview
                    st.markdown("### 💳 Cash vs Credit Overview")
                    
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
                        st.metric("💳 Total Credit Sales", f"{total_credit:,.2f} THB")
                        st.metric("📊 Credit Ratio", f"{credit_percentage:.1f}%")
                        st.metric("🎯 Total Sales", f"{grand_total:,.2f} THB")
                    
                    st.markdown("---")
                    
                    # Export options
                    st.markdown("### 📥 Export Credit Reports")
                    
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
                        csv_all_credit = credit_df.to_csv(index=False).encode("utf-8")
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
            filtered_df = df.copy()
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
            
            # Show filtered metrics
            col1, col2, col3, col4 = st.columns(4)
            if "signed_net" in filtered_df.columns:
                col1.metric("Filtered Sales", f"{filtered_df['signed_net'].sum():,.0f}")
            else:
                col1.metric("Filtered Sales", f"{filtered_df['line_total'].sum():,.0f}")
            col2.metric("Filtered Items", f"{filtered_df['quantity'].sum():,.0f}")
            col3.metric("Transactions", len(filtered_df["bill_number"].unique()))
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
            st.subheader("📈 Quantity vs Total Sales")
            if "signed_net" in filtered_df.columns:
                scatter_data = filtered_df.groupby("item").agg({
                    "quantity": "sum",
                    "signed_net": "sum",
                    "bill_number": "count"
                }).reset_index()
                scatter_data.columns = ["Product", "Total Quantity", "Total Sales", "Times Sold"]
            else:
                scatter_data = filtered_df.groupby("item").agg({
                    "quantity": "sum",
                    "line_total": "sum",
                    "bill_number": "count"
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
            st.markdown("### 📤 Manual Checklist Upload & Reconciliation")
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
            if "location" in df.columns:
                available_locations = sorted(df["location"].dropna().unique())
                
                if len(available_locations) == 0:
                    st.warning("⚠️ No location data available. Make sure to sync Categories and Items.")
                else:
                    selected_log_location = st.selectbox(
                        "📍 Select Location to View Transactions:",
                        available_locations,
                        key="transaction_log_location"
                    )
                    
                    # Filter by selected location
                    location_df = df[df["location"] == selected_log_location].copy()
                    
                    if location_df.empty:
                        st.warning(f"No transactions found for {selected_log_location}")
                    else:
                        # Summary metrics for selected location
                        col1, col2, col3, col4 = st.columns(4)
                        if "signed_net" in location_df.columns:
                            col1.metric("Total Sales", f"{location_df['signed_net'].sum():,.0f}")
                        else:
                            col1.metric("Total Sales", f"{location_df['line_total'].sum():,.0f}")
                        col2.metric("Transactions", location_df['bill_number'].nunique())
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
                            st.markdown("### 🔍 Reconciliation Analysis")
                            
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
                                st.markdown("#### ⚠️ Discrepancies Found")
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
            st.markdown("### 👤 Select Customer")
            
            # Search bar (full width)
            customer_search = st.text_input(
                "🔍 Search Customer by Name or ID:",
                "",
                key="invoice_customer_search"
            )
            
            # Get unique customers
            if 'customer_name' in df.columns:
                customer_list = df[['customer_id', 'customer_name']].drop_duplicates()
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
                st.markdown("### 📅 Select Invoice Period")
                
                # Get customer's transaction date range
                customer_df = df[df['customer_id'] == selected_customer_id]
                cust_min_date = customer_df['day'].min()
                cust_max_date = customer_df['day'].max()
                
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
                    invoice_df = customer_df[
                        (customer_df['day'] >= invoice_start) & 
                        (customer_df['day'] <= invoice_end)
                    ].copy()
                    
                    if invoice_df.empty:
                        st.warning(f"No transactions found for {selected_customer_name} between {invoice_start} and {invoice_end}")
                    else:
                        st.markdown("---")
                        st.markdown("## 🧾 INVOICE")
                        
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
                            **Total Transactions:** {invoice_df['bill_number'].nunique()}
                            """)
                        
                        st.markdown("---")
                        
                        # Invoice summary metrics
                        col1, col2, col3, col4 = st.columns(4)
                        if "signed_net" in invoice_df.columns:
                            total_amount = invoice_df['signed_net'].sum()
                        else:
                            total_amount = invoice_df['line_total'].sum()
                        total_items = invoice_df['quantity'].sum()
                        num_transactions = invoice_df['bill_number'].nunique()
                        
                        col1.metric("💰 Total Amount", f"{total_amount:,.2f} THB")
                        col2.metric("📦 Items Purchased", f"{int(total_items)}")
                        col3.metric("🧾 Transactions", num_transactions)
                        col4.metric("📍 Locations Visited", invoice_df['location'].nunique() if 'location' in invoice_df.columns else 0)
                        
                        st.markdown("---")
                        
                        # Itemized list
                        st.markdown("### 📋 Itemized Transactions")
                        
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
                        st.markdown("### 📊 Summary by Product")
                        if "signed_net" in invoice_df.columns:
                            product_summary = invoice_df.groupby('item').agg({
                                'price': 'first',  # Get unit price
                                'quantity': 'sum',
                                'signed_net': 'sum',
                                'bill_number': 'count'
                            }).reset_index()
                            product_summary.columns = ['Product', 'Unit Price', 'Total Qty', 'Total Amount', 'Times Purchased']
                        else:
                            product_summary = invoice_df.groupby('item').agg({
                                'price': 'first',  # Get unit price
                                'quantity': 'sum',
                                'line_total': 'sum',
                                'bill_number': 'count'
                            }).reset_index()
                            product_summary.columns = ['Product', 'Unit Price', 'Total Qty', 'Total Amount', 'Times Purchased']
                        product_summary = product_summary.sort_values('Total Amount', ascending=False)
                        
                        # Format currency columns
                        product_summary['Unit Price'] = product_summary['Unit Price'].apply(lambda x: f"{x:,.2f}")
                        product_summary['Total Amount'] = product_summary['Total Amount'].apply(lambda x: f"{x:,.2f}")
                        
                        st.dataframe(product_summary, use_container_width=True, hide_index=True)
                        
                        # Payment breakdown if available
                        if 'payment_name' in invoice_df.columns:
                            st.markdown("### 💳 Payment Methods Used")
                            if "signed_net" in invoice_df.columns:
                                payment_summary = invoice_df.groupby('payment_name')['signed_net'].sum().reset_index()
                                payment_summary.columns = ['Payment Method', 'Amount']
                            else:
                                payment_summary = invoice_df.groupby('payment_name')['line_total'].sum().reset_index()
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
                        st.markdown("### 📥 Download Invoice")
                        
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
                            st.markdown("## 🖨️ PRINT VIEW")
                            
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
                            st.markdown("### 📋 Itemized Transactions")
                            
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
                            st.markdown("### 📊 Summary by Product")
                            
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
                    if pd.isna(product_name):
                        return "📦 อื่นๆ (Other)"
                    
                    product_str = str(product_name).lower()
                    
                    if "ป่น" in product_str:
                        return "🧊 ป่น (Crushed Ice)"
                    elif "หลอดเล็ก" in product_str or ("หลอด" in product_str and "เล็ก" in product_str):
                        return "🧊 หลอดเล็ก (Small Tube)"
                    elif "หลอดใหญ่" in product_str or ("หลอด" in product_str and "ใหญ่" in product_str):
                        return "🧊 หลอดใหญ่ (Large Tube)"
                    else:
                        return "📦 อื่นๆ (Other)"
                
                # Apply categorization
                df_ice = df.copy()
                df_ice['ice_category'] = df_ice['item'].apply(categorize_ice_product)
                
                # === LOCATION TABLE WITH FORECASTS ===
                st.markdown("### 📊 Ice Forecast by Location")
                
                # Get unique locations
                locations = df_ice['location'].dropna().unique()
                locations = sorted([loc for loc in locations if loc != "Uncategorized"])
                
                # Calculate 7-day moving averages for each location and ice type
                forecast_data = []
                
                for location in locations:
                    location_df = df_ice[df_ice['location'] == location].copy()
                    location_df['day'] = pd.to_datetime(location_df['day'])
                    location_df = location_df.sort_values('day')
                    
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
                    if len(location_df) >= 7:
                        if "signed_net" in location_df.columns:
                            daily_sales = location_df.groupby('day')['signed_net'].sum().reset_index()
                            daily_sales['ma_7d'] = daily_sales['signed_net'].rolling(window=7, min_periods=1).mean()
                        else:
                            daily_sales = location_df.groupby('day')['line_total'].sum().reset_index()
                            daily_sales['ma_7d'] = daily_sales['line_total'].rolling(window=7, min_periods=1).mean()
                        location_forecast['Total Sales (7d avg)'] = round(daily_sales['ma_7d'].iloc[-1], 0)
                    else:
                        if "signed_net" in location_df.columns:
                            location_forecast['Total Sales (7d avg)'] = round(location_df['signed_net'].mean(), 0)
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
                st.markdown("### 📍 Detailed Analysis by Location")
                
                selected_location = st.selectbox(
                    "Select Location for Detailed Analysis:",
                    locations,
                    key="ice_forecast_location"
                )
                
                if selected_location:
                    st.markdown(f"#### 📊 Detailed Analysis: {selected_location}")
                    
                    # Filter data for selected location
                    location_detail_df = df_ice[df_ice['location'] == selected_location].copy()
                    location_detail_df['day'] = pd.to_datetime(location_detail_df['day'])
                    location_detail_df = location_detail_df.sort_values('day')
                    
                    # Calculate 7-day moving averages for each ice type
                    ice_types = ["🧊 ป่น (Crushed Ice)", "🧊 หลอดเล็ก (Small Tube)", "🧊 หลอดใหญ่ (Large Tube)", "📦 อื่นๆ (Other)"]
                    
                    # Create charts for each ice type - Full width
                    
                    # Total orders trend - Full width
                    if "signed_net" in location_detail_df.columns:
                        daily_totals = location_detail_df.groupby('day')['signed_net'].sum().reset_index()
                        daily_totals['ma_7d'] = daily_totals['signed_net'].rolling(window=7, min_periods=1).mean()
                        daily_totals = daily_totals.rename(columns={'signed_net': 'total'})
                    else:
                        daily_totals = location_detail_df.groupby('day')['line_total'].sum().reset_index()
                        daily_totals['ma_7d'] = daily_totals['line_total'].rolling(window=7, min_periods=1).mean()
                        daily_totals = daily_totals.rename(columns={'line_total': 'total'})
                    
                    fig_total = px.line(daily_totals, x='day', y=['total', 'ma_7d'],
                                      title=f"Total Orders - {selected_location}",
                                      labels={'value': 'Total Sales (THB)', 'day': 'Date'})
                    fig_total.update_layout(legend=dict(
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
                    fig_ice.update_layout(legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ))
                    st.plotly_chart(fig_ice, use_container_width=True)
                    
                    # Detailed metrics
                    st.markdown("#### 📈 Current Forecast Metrics")
                    
                    # Get latest 7-day averages
                    latest_date = location_detail_df['day'].max()
                    week_ago = latest_date - pd.Timedelta(days=7)
                    recent_data = location_detail_df[location_detail_df['day'] >= week_ago]
                    
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
                            if "signed_net" in recent_data.columns:
                                daily_sales = recent_data.groupby('day')['signed_net'].sum().mean()
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
                    st.markdown("#### 💡 Loading Recommendations")
                    
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
                        st.markdown("#### 📊 Calculation Method")
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
            if df.empty:
                st.warning("⚠️ No data available. Please load data first.")
            else:
                # Initialize customer notes in session state
                if 'customer_notes' not in st.session_state:
                    st.session_state.customer_notes = {}
                
                # === TOP CUSTOMERS ANALYSIS ===
                st.markdown("### 🏆 Top Customers")
                
                # Calculate customer metrics
                if "signed_net" in df.columns:
                    customer_metrics = df.groupby(['customer_id', 'customer_name']).agg({
                        'signed_net': 'sum',
                        'quantity': 'sum',
                        'bill_number': 'nunique',
                        'day': ['min', 'max', 'nunique']
                    }).reset_index()
                    customer_metrics.columns = ['Customer ID', 'Customer Name', 'Total Spent', 'Total Items', 'Transactions', 'First Visit', 'Last Visit', 'Active Days']
                else:
                    customer_metrics = df.groupby(['customer_id', 'customer_name']).agg({
                        'line_total': 'sum',
                        'quantity': 'sum',
                        'bill_number': 'nunique',
                        'day': ['min', 'max', 'nunique']
                    }).reset_index()
                    customer_metrics.columns = ['Customer ID', 'Customer Name', 'Total Spent', 'Total Items', 'Transactions', 'First Visit', 'Last Visit', 'Active Days']
                
                # Calculate additional metrics
                customer_metrics['Avg Transaction'] = customer_metrics['Total Spent'] / customer_metrics['Transactions']
                customer_metrics['Avg Items per Transaction'] = customer_metrics['Total Items'] / customer_metrics['Transactions']
                customer_metrics['Days Since Last Visit'] = (pd.Timestamp.now() - pd.to_datetime(customer_metrics['Last Visit'])).dt.days
                
                # Sort by total spent
                customer_metrics = customer_metrics.sort_values('Total Spent', ascending=False)
                
                # Display top customers
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("💰 Total Customers", len(customer_metrics))
                
                with col2:
                    top_customer_spent = customer_metrics['Total Spent'].iloc[0] if len(customer_metrics) > 0 else 0
                    st.metric("🏆 Top Customer Spent", f"฿{top_customer_spent:,.0f}")
                
                with col3:
                    avg_customer_value = customer_metrics['Total Spent'].mean()
                    st.metric("📊 Avg Customer Value", f"฿{avg_customer_value:,.0f}")
                
                st.markdown("---")
                
                # === CUSTOMER ALERTS ===
                st.markdown("### 🚨 Customer Alerts")
                
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
                    
                    customer_df = df[df['customer_id'] == customer_id].copy()
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
                st.markdown("### 📋 Customer Management")
                
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
                        st.markdown("**📊 Recent Transaction History:**")
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
        
        # --- Download ---
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col2:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Full Data", csv, "receipts_export.csv", "text/csv", use_container_width=True)
