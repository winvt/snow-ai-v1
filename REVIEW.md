# Snow AI Dashboard – Code Review

**Reviewed:** Feb 2025  
**Scope:** `app.py`, `database.py`, `daily_briefing.py`, `utils/`, scripts, and config.

---

## 1. Overview

**Snow AI** is a Streamlit analytics dashboard for **Loyverse POS** data. It uses a local SQLite DB, Loyverse REST API for sync, and supports English/Thai. The app is a single ~4,400-line `app.py` with sidebar navigation, 10 main tabs, password gate, and Settings for sync/theme.

---

## 2. Features & Tabs

| Tab | Key | Purpose |
|-----|-----|--------|
| **Daily Sales** | `daily_sales` | Daily sales analysis: KPIs (avg daily sales, avg transaction, growth), day-of-week and time-period charts, daily discounts, receipt-level net/refunds. |
| **By Location** | `by_location` | Sales by location (ประเภท): breakdown by store/location, charts, filters. |
| **By Product** | `by_product` | Product analysis: category summary, sales distribution, top products, optional manual product-category overrides. |
| **By Customer** | `by_customer` | Customer analysis: spending, visits, segments; charts and metrics. |
| **Credit** | `credit` | Credit management: filter by payment name (ค้างชำระ/เครดิต), outstanding by customer, overdue/due-soon/current, credit by location. |
| **Interactive Data** | `interactive_data` | Data explorer: filters (location, store, payment), raw/aggregated view of dataset. |
| **Transaction Log** | `transaction_log` | Transaction log by location: searchable/filterable list of transactions. |
| **Customer Invoice** | `customer_invoice` | Invoice generator: pick customer, date range, view/print invoice for that period. |
| **Ice Forecast** | `ice_forecast` | Ice demand: product→ice category (ป่น, หลอดเล็ก, หลอดใหญ่, อื่นๆ), 7-day moving average by location, detailed location charts. |
| **CRM** | `crm` | Top customers, metrics, **customer decline alerts** (e.g. >50% week-over-week drop for top 20), optional notes in session state. |
| **Settings** | (sidebar expander) | Appearance (theme, font, color scheme), data management (sync receipts, sync missing, custom date sync), reference data sync (customers, payment types, stores, employees, categories, items), backup, API info. |

**Sidebar:** Load Database, EN/TH language, navigation buttons, Settings expander.  
**Auth:** Password gate before any dashboard content; logout clears `st.session_state.authenticated`.

---

## 3. Data & “Models”

### 3.1 Database (SQLite – `database.py`)

**Tables:**

- **Core:** `receipts`, `line_items`, `payments` (receipt-level and line-level).
- **Reference:** `customers`, `payment_types`, `stores`, `employees`, `categories`, `items` (Loyverse entities).
- **App:** `sync_metadata`, `manual_product_categories` (user overrides for product→category).

**Notable behavior:**

- Receipts with `total_money` ≥ 999,999 or ≤ -999,999 (and a few hardcoded receipt numbers) are filtered out on save.
- Location often comes from `dining_option` on receipts.
- Categories in DB are used as “locations” (e.g. 23 categories).

**No separate “forecast” or “alert” tables:** Ice forecast and CRM decline logic are computed in the app from the same receipt/line-item data.

### 3.2 In-App “Models” (Logic Only)

- **Ice categorization:** `categorize_ice_product()` in app and in `daily_briefing.py` – keyword rules (ป่น, หลอดเล็ก, หลอดใหญ่) → 4 buckets; manual overrides via `manual_product_categories` where used.
- **Customer decline (CRM):** `detect_customer_decline()` – last 30 days, weekly sums, flag if latest week is &lt;50% of previous week (top 20 customers only).
- **Daily briefing:** `daily_briefing.py` – same-day-of-week comparison for “decline” in daily report; uses `categorize_product()` and `compute_signed_net()`.

So today there are **no separate ML/statistical models**; everything is rule-based and aggregation-based.

---

## 4. Architecture Summary

- **Single script:** Almost all UI and tab logic lives in `app.py` (~4.4k lines). `utils/charts.py` and `utils/reference_data.py` factor out charts and reference-data loading; `database.py` is the only DB layer.
- **State:** Streamlit session state for tab, language, theme, font, color scheme, optional customer notes (CRM), and auth.
- **Data flow:** Load DB → `st.session_state.receipts_df`; date range and filters applied on that DataFrame; each tab reads from the same (possibly filtered) `df`.
- **Sync:** Loyverse API (receipts paginated by cursor); “sync missing” and “custom date range” live in Settings; `daily_briefing.py` can fetch receipts headless for a date range.

---

## 5. What Works Well

- **Feature set:** Covers sales, location, product, customer, credit, invoices, ice forecast, and CRM in one app.
- **i18n:** Full EN/TH via `TRANSLATIONS` and `get_text()`.
- **Refunds and net:** Receipt-level `signed_net` (refunds as negative) is used consistently in KPIs and charts.
- **DB resilience:** `LoyverseDB` handles missing dirs, Render persistent disk path, and fallbacks.
- **Reference data:** Centralized sync for customers, payment types, stores, employees, categories, items.
- **Charts:** Shared helpers in `utils/charts.py` (bar, pie, trend) keep styling consistent.

---

## 6. Issues & Risks

### 6.1 Security

- **Password hardcoded** in `app.py`: `PASSWORD = "snowbomb"`. Should be from env (e.g. `DASHBOARD_PASSWORD`) and never committed.
- Session-only auth: no tokens, no expiry; logout is the only way to “expire” access.

### 6.2 Maintainability

- **Monolithic `app.py`:** 10 tabs and Settings in one file make navigation and testing harder. Splitting by tab (e.g. `pages/` or `tabs/daily_sales.py`) would improve clarity and allow smaller reviews.
- **Duplicate logic:** e.g. `categorize_ice_product()` in app vs `categorize_product()` in `daily_briefing.py` – same idea, different names/signatures. One shared implementation (e.g. in `utils` or `database`-backed) would be easier to evolve.

### 6.3 Data & Correctness

- **Credit tab:** Filters by payment *name* containing "ค้างชำระ|เครดิต". If Loyverse adds new payment types or names, this may need updating. Consider payment_type_id or a tag in reference data.
- **Location:** Mix of `dining_option`, `location`, and categories; “location” can mean different things in different tabs. A short data glossary or single source of truth (e.g. “display location” from categories + overrides) would reduce confusion.

### 6.4 Performance

- **Load Database** pulls the full receipts join into memory. For very large DBs this could be slow or OOM. Pagination or lazy loading per tab would scale better.
- **CRM:** Loops over top 20 customers and builds a per-customer DataFrame each time; could be one grouped DataFrame plus vectorized checks.

---

## 7. Recommendations (Including “New Models”)

### 7.1 Quick Wins

1. **Move password to env:** e.g. `PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")` and document in README; fail closed if unset in production.
2. **Single ice-category function:** One function (e.g. in `utils/` or `reference_data`) used by both `app.py` and `daily_briefing.py`, with manual overrides from DB or session.
3. **README:** Mention all 10 tabs and Settings; document `DASHBOARD_PASSWORD` and `LOYVERSE_TOKEN`; optional one-line “data models” (tables used by the app).

### 7.2 Structure

4. **Split tabs into modules:** e.g. `tabs/daily_sales.py`, `tabs/credit.py`, `tabs/ice_forecast.py`, etc., each receiving `df`, `db`, `ref_data`, and `get_text`; `app.py` only does routing and layout.
5. **Shared “data loader”:** One place that applies date range and common filters to `receipts_df` and passes the same `df` into every tab (already almost the case; make it a small function so filters are consistent and documented).

### 7.3 New or Improved “Models”

6. **Forecast model (optional):**  
   Ice forecast currently uses 7-day moving average. You could add a simple **time-series model** (e.g. trend + seasonality by day-of-week) or use a small library (e.g. `statsmodels` or Prophet) and store last-run forecasts in a table (e.g. `ice_forecast_cache`: location, date, ice_type, predicted_qty). That would separate “historical MA” from “forecast” and allow alerts when actuals diverge.

7. **Customer alerts model (optional):**  
   Move decline logic into a small module (e.g. `utils/customer_alerts.py`). Optionally persist “alert state” in a table (e.g. `customer_alerts`: customer_id, period_end, decline_pct, notified) so you can avoid duplicate notifications and add more rules (e.g. “first time no order in 14 days”) later.

8. **Credit model (optional):**  
   If you ever need true “outstanding balance” (credits minus payments), the current receipt-based view is a proxy. A dedicated **credit ledger** (per customer: date, type=credit|payment, amount, receipt_id) would give a clear balance and aging; that would be a new model/schema and sync step.

9. **Config-driven categories:**  
   Ice categories (and maybe product→reporting category) could live in a config file or DB table (e.g. `category_rules`: pattern, category_name, order) instead of hardcoded strings in Python. Easier to add new ice types or locations without code changes.

---

## 8. Should the app be refactored?

**Short answer: Yes, but in phases.** The app works and is feature-complete; refactoring is recommended to reduce risk, improve maintainability, and make future changes safer. No need to rewrite everything at once.

### 8.1 Why refactor?

| Driver | Reason |
|--------|--------|
| **Single 4,400+ line file** | Hard to navigate, review, and test. One bug can be buried in a large `elif` chain. |
| **Duplication** | Ice categorization and similar logic exist in more than one place; changes must be repeated and can drift. |
| **Security** | Password in code is a real risk; fixing it is a small, high-value change. |
| **Onboarding** | New contributors (or future you) will find smaller, named modules easier to understand than one giant script. |
| **Testing** | Right now the app is hard to unit-test because everything is in one script. Extracted modules can be tested in isolation. |
| **Scaling** | If the DB or number of tabs grows, a monolithic script will become harder to change without regressions. |

Refactoring does **not** mean changing behaviour or adding features. It means reorganising the same logic into clearer structure.

### 8.2 What not to do

- **Don’t refactor and add features in the same step.** Do structure first, then new behaviour.
- **Don’t rewrite in a new framework.** Streamlit and the current data flow are fine; the issue is file size and organisation.
- **Don’t split without a plan.** Have a clear contract (e.g. “each tab receives `df`, `db`, `get_text`”) so tabs stay consistent.

### 8.3 Suggested refactoring (no code changes here – plan only)

**Phase 1 – Low risk, high value (do first)**  
- Move password to an environment variable and document it. No file split, minimal diff.  
- Extract a **single shared ice/product categorization** (e.g. in `utils/categories.py` or similar) and call it from `app.py` and `daily_briefing.py`. Reduces duplication and keeps behaviour in one place.

**Phase 2 – Split by tab (main structural change)**  
- Introduce a `tabs/` package (or `pages/` if you prefer Streamlit’s multipage pattern).  
- One module per tab: e.g. `daily_sales.py`, `by_location.py`, `by_product.py`, `by_customer.py`, `credit.py`, `interactive_data.py`, `transaction_log.py`, `customer_invoice.py`, `ice_forecast.py`, `crm.py`.  
- Each tab module exposes a single entry point, e.g. `render(df, db, ref_data, get_text)` (or similar), and contains only that tab’s UI and logic.  
- Move **Settings** into its own module (e.g. `sidebar_settings.py` or `tabs/settings.py`) and call it from the sidebar.  
- `app.py` becomes: auth, DB init, reference data init, sidebar (nav + Load DB + language + Settings), **date-range and filter logic**, then a single `if/elif` (or dict of tab → render function) that calls the right tab’s `render(...)`.  
- Keep all tab content out of `app.py`; no copy-paste of big blocks into `app.py`.

**Phase 3 – Shared data and helpers**  
- **Data loader:** One function (e.g. in `utils/data_loader.py` or in `app.py` as a small helper) that takes `receipts_df`, applies the selected date range and any global filters (location/store/payment), and returns the `df` that every tab uses. Document this as the single place that defines “what the user is viewing.”  
- **API/sync helpers:** The `fetch_all_*` and sync logic could move to a `sync/` or `api/` module so `app.py` and Settings only call high-level functions. Optional and can follow after Phase 2.

**Phase 4 – Optional extractions**  
- **Customer alerts:** Move `detect_customer_decline` (and any related logic) into e.g. `utils/customer_alerts.py` and call it from the CRM tab module.  
- **Translations:** If you like, move `TRANSLATIONS` and `get_text` into e.g. `utils/i18n.py` so `app.py` stays thin.  
- **Constants:** Centralise magic numbers (e.g. 7-day window for ice, 50% for decline, 30 days) in one place (config or constants module) so they’re easy to tune.

### 8.4 Suggested target layout (after refactor)

```
app.py                 # ~200–400 lines: auth, init, sidebar, date/filter, dispatch to tabs
tabs/
  __init__.py
  daily_sales.py
  by_location.py
  by_product.py
  by_customer.py
  credit.py
  interactive_data.py
  transaction_log.py
  customer_invoice.py
  ice_forecast.py
  crm.py
  settings.py          # or sidebar_settings.py – Settings expander content
utils/
  charts.py            # existing
  reference_data.py    # existing
  categories.py        # new: shared ice/product categorization
  data_loader.py       # optional: apply date range + filters → df
  customer_alerts.py   # optional: decline detection
  i18n.py              # optional: TRANSLATIONS + get_text
database.py            # unchanged
daily_briefing.py      # unchanged except use shared categories
```

### 8.5 Summary

- **Should you refactor?** Yes – in phases, starting with password and shared ice logic, then splitting tabs, then shared data loader and optional extractions.  
- **Do you have to?** No. The app will keep working as-is. Refactoring is about maintainability, safety, and making the next change easier.  
- **When to do it?** Phase 1 anytime; Phase 2 when you’re about to add or change a tab and want a clearer place to edit.

No code has been changed in this review; the above is a plan only.

---

## 9. Summary Table

| Area | Status | Suggestion |
|------|--------|------------|
| Tabs & features | ✅ Rich set | Document in README; split into modules |
| DB schema | ✅ Solid | Consider credit ledger / forecast cache if needed |
| Auth | ⚠️ Weak | Env-based password; optional token/expiry later |
| i18n | ✅ Good | Keep using `get_text` for any new copy |
| Ice “model” | Rule-based | Centralize; optional forecast table + simple model |
| CRM alerts | Rule-based | Extract to module; optional alert persistence |
| Performance | OK for medium data | Lazy load or paginate if DB grows large |
| Security | ⚠️ Password in code | Use `DASHBOARD_PASSWORD` env |

Overall, the app is feature-rich and consistent; the main improvements are security (password), structure (split tabs, shared ice logic), and optional new models (forecast cache, customer alerts, credit ledger) if you want to extend analytics or automation.
