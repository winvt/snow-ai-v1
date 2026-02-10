import os
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple, Optional

import pandas as pd
import pytz
import requests
from dotenv import load_dotenv

from database import LoyverseDB


def get_bangkok_yesterday() -> Tuple[date, date]:
    """Get yesterday's date in Bangkok timezone."""
    tz = pytz.timezone("Asia/Bangkok")
    now_bkk = datetime.now(tz)
    yesterday_bkk = now_bkk.date() - timedelta(days=1)
    return yesterday_bkk, yesterday_bkk


def fetch_receipts_headless(
    token: str,
    start_date: date,
    end_date: date,
    store_id: Optional[str] = None,
    limit: int = 250,
) -> List[Dict]:
    """Fetch receipts from Loyverse API for a date range (Bangkok -> UTC) without Streamlit UI."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    base_url = "https://api.loyverse.com/v1.0/receipts"

    # Convert Bangkok local date range to UTC timestamps expected by API
    tz = pytz.timezone("Asia/Bangkok")
    start_dt_utc = tz.localize(datetime.combine(start_date, datetime.min.time())).astimezone(pytz.UTC)
    end_dt_utc = tz.localize(datetime.combine(end_date, datetime.max.time())).astimezone(pytz.UTC)

    params: Dict[str, str] = {
        "created_at_min": start_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "created_at_max": end_dt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": limit,
    }
    if store_id:
        params["store_id"] = store_id

    all_receipts: List[Dict] = []
    cursor: Optional[str] = None

    while True:
        if cursor:
            params["cursor"] = cursor
        res = requests.get(base_url, headers=headers, params=params, timeout=60)
        if res.status_code != 200:
            raise RuntimeError(f"Loyverse API error {res.status_code}: {res.text}")
        data = res.json() if res.text else {}
        batch = data.get("receipts", [])
        all_receipts.extend(batch)
        cursor = data.get("cursor")
        if not cursor:
            break

    return all_receipts


def compute_signed_net(df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
    """Compute receipt-level signed net and attach to rows; returns (df_with_signed, total_sales)."""
    if {"bill_number", "receipt_total", "receipt_discount", "receipt_type"}.issubset(df.columns):
        receipt_level = df.groupby(["bill_number", "receipt_type"], as_index=False).agg(
            {"receipt_total": "first", "receipt_discount": "first"}
        )
        receipt_level["receipt_net"] = (
            receipt_level["receipt_total"].fillna(0) - receipt_level["receipt_discount"].fillna(0)
        )
        receipt_level["signed_net"] = receipt_level.apply(
            lambda r: -r["receipt_net"] if str(r["receipt_type"]).lower() == "refund" else r["receipt_net"],
            axis=1,
        )
        total_sales = float(receipt_level["signed_net"].sum())
        df_with = df.merge(receipt_level[["bill_number", "signed_net"]], on="bill_number", how="left")
        return df_with, total_sales
    # Fallback: sum line totals
    total_sales = float(df["line_total"].astype(float).sum()) if "line_total" in df.columns else 0.0
    return df, total_sales


def categorize_product(product_name: str, manual_categories: Dict[str, str] = None) -> str:
    """Map item name to ice categories, using manual overrides first."""
    if pd.isna(product_name):
        return "📦 อื่นๆ (Other)"
    
    product_str = str(product_name)
    
    # Check manual categories first (exact match)
    if manual_categories and product_str in manual_categories:
        return manual_categories[product_str]
    
    # Auto-detect category
    text = product_str.lower()
    if "ป่น" in text:
        return "🧊 ป่น (Crushed Ice)"
    if "หลอดเล็ก" in text or ("หลอด" in text and "เล็ก" in text):
        return "🧊 หลอดเล็ก (Small Tube)"
    if "หลอดใหญ่" in text or ("หลอด" in text and "ใหญ่" in text):
        return "🧊 หลอดใหญ่ (Large Tube)"
    return "📦 อื่นๆ (Other)"


def detect_customer_decline_daily(customer_df: pd.DataFrame, compare_through_date: date) -> Tuple[bool, float]:
    """
    For daily reports: Compare same day of week (e.g., Tuesday vs last Tuesday)
    """
    if len(customer_df) < 2:
        return False, 0.0

    # Get day of week (0=Monday, 6=Sunday)
    target_dow = compare_through_date.weekday()
    
    # Find same day of week in previous weeks
    recent_data = customer_df.copy()
    recent_data["day_of_week"] = recent_data["day"].dt.dayofweek
    recent_data["week"] = recent_data["day"].dt.to_period("W-SUN")
    
    # Filter to same day of week
    same_dow_data = recent_data[recent_data["day_of_week"] == target_dow]
    if len(same_dow_data) < 2:
        return False, 0.0
    
    # Get last 2 occurrences of this day of week
    metric_col = "signed_net" if "signed_net" in same_dow_data.columns else "line_total"
    daily_totals = same_dow_data.groupby("day")[metric_col].sum().sort_index()
    
    if len(daily_totals) < 2:
        return False, 0.0
    
    latest = daily_totals.iloc[-1]
    previous = daily_totals.iloc[-2]
    
    if previous == 0:
        return False, 0.0
    
    decline_pct = ((latest - previous) / previous) * 100
    return decline_pct < -50, abs(float(decline_pct))


def build_message(
    report_date: date,
    sales_baht: float,
    items_sold: float,
    transactions: int,
    avg_order: float,
    unique_customers: int,
    ice_counts: Dict[str, float],
    customer_alerts: List[Dict[str, str]],
) -> str:
    date_str = report_date.strftime("%A, %d %B %Y")
    crushed = ice_counts.get("🧊 ป่น (Crushed Ice)", 0)
    small = ice_counts.get("🧊 หลอดเล็ก (Small Tube)", 0)
    large = ice_counts.get("🧊 หลอดใหญ่ (Large Tube)", 0)

    lines = []
    lines.append("--- ❄️ Snowbomb Daily Briefing ---")
    lines.append(f"Summary for: {date_str}")
    lines.append("")
    lines.append("**Top-Line KPIs:**")
    lines.append(f"Sales: ฿{sales_baht:,.0f}")
    lines.append(f"Units Sold: {items_sold:,.0f}")
    lines.append(f"Transactions: {transactions:,}")
    lines.append(f"Unique Customers: {unique_customers:,}")
    lines.append(f"Avg. Order: ฿{avg_order:,.0f}")
    lines.append("")
    lines.append("**Ice Sold (Units):**")
    lines.append(f"🧊 ป่น (Crushed): {crushed:,.0f}")
    lines.append(f"🧊 หลอดเล็ก (Small): {small:,.0f}")
    lines.append(f"🧊 หลอดใหญ่ (Large): {large:,.0f}")
    other_units = ice_counts.get("📦 อื่นๆ (Other)", 0)
    lines.append(f"📦 อื่นๆ (Other): {other_units:,.0f}")
    lines.append("")
    lines.append("**Customer Alerts:**")
    if customer_alerts:
        for a in customer_alerts:
            lines.append(
                f"- {a['Customer']}: decline {a['Decline']}, last visit {a['Last Visit']}, spent {a['Total Spent']}"
            )
    else:
        lines.append("- No significant customer declines detected")

    return "\n".join(lines)


def send_line_message(message: str, channel_access_token: str, recipient_id: str) -> None:
    """Send message using LINE Messaging API to a user or group."""
    headers = {
        "Authorization": f"Bearer {channel_access_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "to": recipient_id,  # Can be userId or groupId
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    
    res = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=data,
        timeout=30,
    )
    if res.status_code != 200:
        raise RuntimeError(f"LINE Messaging API error {res.status_code}: {res.text}")


def main() -> None:
    load_dotenv()

    loyverse_token = os.getenv("LOYVERSE_TOKEN")
    if not loyverse_token:
        print("⚠️ Missing LOYVERSE_TOKEN; will use existing database without fetching new receipts.")

    line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    if not line_channel_access_token:
        raise RuntimeError("Missing LINE_CHANNEL_ACCESS_TOKEN environment variable")

    # Recipient can be provided as LINE_RECIPIENT_ID or LINE_RECIPIENT_ID_GROUP
    line_recipient_id = os.getenv("LINE_RECIPIENT_ID") or os.getenv("LINE_RECIPIENT_ID_GROUP")
    if not line_recipient_id:
        raise RuntimeError("Missing LINE_RECIPIENT_ID or LINE_RECIPIENT_ID_GROUP environment variable")

    # Initialize database
    db = LoyverseDB(os.getenv("DATABASE_PATH"))
    db.init_database()

    # Always use yesterday's date (Bangkok timezone)
    start_date, end_date = get_bangkok_yesterday()
    report_date = start_date

    # Fetch and sync yesterday's receipts
    if loyverse_token:
        receipts = fetch_receipts_headless(loyverse_token, start_date, end_date)
        if receipts:
            db.save_receipts(receipts)
            db.update_sync_time("receipts", f"{len(receipts)} receipts")
            print(f"✅ Fetched {len(receipts)} receipts for {report_date}")
    else:
        print("⚠️ No LOYVERSE_TOKEN, using existing database data")

    # Load yesterday's data from DB for KPIs
    df = db.get_receipts_dataframe(start_date=start_date.isoformat(), end_date=end_date.isoformat())
    
    # Get customer mapping for proper names
    customer_map = db.get_customer_map()
    
    # Load manual categories (optional)
    manual_categories = {}
    manual_cat_path = os.getenv("MANUAL_CATEGORIES_PATH")
    if manual_cat_path:
        try:
            with open(manual_cat_path, "r", encoding="utf-8") as f:
                manual_categories = json.load(f)
        except FileNotFoundError:
            print("⚠️ Manual categories file not found, using auto-detection only")
    
    if df.empty:
        message = build_message(
            report_date, 0, 0, 0, 0, 0,
            {"🧊 ป่น (Crushed Ice)": 0, "🧊 หลอดเล็ก (Small Tube)": 0, "🧊 หลอดใหญ่ (Large Tube)": 0, "📦 อื่นๆ (Other)": 0},
            []
        )
        send_line_message(message, line_channel_access_token, line_recipient_id)
        print(f"✅ Sent empty briefing for {report_date}")
        return

    # Compute signed net and totals
    # Convert dates from UTC to Bangkok timezone (handles both aware and naive datetimes)
    df_dates = pd.to_datetime(df["date"])
    if df_dates.dt.tz is None:
        # If naive, assume UTC (Loyverse stores in UTC)
        df_dates = df_dates.dt.tz_localize("UTC")
    df["day"] = df_dates.dt.tz_convert("Asia/Bangkok").dt.date
    df["day"] = pd.to_datetime(df["day"])  # for grouping in decline logic
    df, total_sales = compute_signed_net(df)
    total_items = float(df["quantity"].sum()) if "quantity" in df.columns else 0.0
    transactions = int(df["bill_number"].nunique()) if "bill_number" in df.columns else 0
    unique_customers = int(df["customer_id"].nunique()) if "customer_id" in df.columns else 0
    if "signed_net" in df.columns and "receipt_type" in df.columns:
        per_receipt = df.groupby(["bill_number", "receipt_type"], as_index=False)["signed_net"].first()
        per_receipt = per_receipt[per_receipt["receipt_type"].str.lower() != "refund"]
        avg_order = float(per_receipt["signed_net"].mean()) if not per_receipt.empty else 0.0
    elif "line_total" in df.columns:
        avg_order = float(df.groupby("bill_number")["line_total"].sum().mean())
    else:
        avg_order = 0.0

    # Ice units by category
    df_cat = df.copy()
    df_cat["ice_category"] = df_cat["item"].apply(lambda x: categorize_product(x, manual_categories)) if "item" in df_cat.columns else "📦 อื่นๆ (Other)"
    ice_counts = {
        "🧊 ป่น (Crushed Ice)": float(df_cat[df_cat["ice_category"] == "🧊 ป่น (Crushed Ice)"]["quantity"].sum() if "quantity" in df_cat.columns else 0),
        "🧊 หลอดเล็ก (Small Tube)": float(df_cat[df_cat["ice_category"] == "🧊 หลอดเล็ก (Small Tube)"]["quantity"].sum() if "quantity" in df_cat.columns else 0),
        "🧊 หลอดใหญ่ (Large Tube)": float(df_cat[df_cat["ice_category"] == "🧊 หลอดใหญ่ (Large Tube)"]["quantity"].sum() if "quantity" in df_cat.columns else 0),
        "📦 อื่นๆ (Other)": float(df_cat[df_cat["ice_category"] == "📦 อื่นๆ (Other)"]["quantity"].sum() if "quantity" in df_cat.columns else 0),
    }

    # Customer decline alerts (top 20 by spend)
    alerts: List[Dict[str, str]] = []
    
    # Build per-customer metrics from all available data (load wider window for alerts)
    df_alert = db.get_receipts_dataframe()
    if not df_alert.empty:
        # Convert dates from UTC to Bangkok timezone (handles both aware and naive datetimes)
        df_alert_dates = pd.to_datetime(df_alert["date"])
        if df_alert_dates.dt.tz is None:
            # If naive, assume UTC (Loyverse stores in UTC)
            df_alert_dates = df_alert_dates.dt.tz_localize("UTC")
        df_alert["day"] = df_alert_dates.dt.tz_convert("Asia/Bangkok")  # convert to Bangkok time
        df_alert, _ = compute_signed_net(df_alert)
        
        # Get top customers by total spend
        top_spend = (
            df_alert.groupby("customer_id").agg(total_spent=("signed_net" if "signed_net" in df_alert.columns else "line_total", "sum"))
        )
        top_ids = list(top_spend.sort_values("total_spent", ascending=False).head(20).index)
        
        for cid in top_ids:
            cust_df = df_alert[df_alert["customer_id"] == cid].copy()
            cust_df = cust_df.sort_values("day")
            
            # Daily report: compare same day of week
            is_decline, decline_pct = detect_customer_decline_daily(cust_df, report_date)
            if is_decline:
                # Get proper customer name from mapping
                cust_name = customer_map.get(str(cid), f"Customer {str(cid)[:8]}...")
                last_visit = pd.to_datetime(cust_df["day"].iloc[-1]).date().isoformat() if not cust_df.empty else "-"
                total_spent_val = float(top_spend.loc[cid, "total_spent"]) if cid in top_spend.index else 0.0
                alerts.append(
                    {
                        "Customer": cust_name,
                        "Decline": f"{decline_pct:.1f}%",
                        "Total Spent": f"฿{total_spent_val:,.0f}",
                        "Last Visit": last_visit,
                    }
                )

    message = build_message(report_date, total_sales, total_items, transactions, avg_order, unique_customers, ice_counts, alerts)
    send_line_message(message, line_channel_access_token, line_recipient_id)
    print(f"✅ Daily briefing sent for {report_date}")


if __name__ == "__main__":
    main()
