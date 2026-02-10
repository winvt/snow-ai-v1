# Import Logic Change Log + Detailed Audit

## Scope
This document summarizes all changes made from the original import/sync logic, includes the actual code-level updates (snippets), and provides a detailed logic audit with potential pitfalls.

## Files touched for import/reconciliation behavior
- `app.py`
- `database.py`
- `utils/sync_dates.py`
- `test_sync_match.py`
- `docs/SYNC_AND_CSV_MATCH.md`

---

## 1) Original behavior vs updated behavior

### A. Sync date-range timezone handling

**Original:**
- Custom sync converted date inputs into naive datetimes (`datetime.combine(...)`) and passed them into API fetch.
- In fetch path, naive datetimes were interpreted as UTC.
- Result: Bangkok day windows were shifted and could miss/include wrong transactions.

**Updated:**
- Custom range sync passes date objects (`api_start = sync_start_date`, `api_end = sync_end_date`) so API window is derived from Bangkok day boundaries.
- Added `utils/sync_dates.py` to formalize Bangkok<->UTC conversion utilities.

**Impact:**
- Eliminated day-boundary drift for sync windows.

---

### B. Dedup strategy during import

**Original:**
- Skip duplicates using weak signature `(created_at, total_money)`.
- This can falsely classify legitimate receipts as duplicates in high-throughput windows.

**Updated:**
- Strong guardrails:
  - Skip only if `receipt_id` already exists, or
  - Skip if `(store_id, receipt_number)` already exists.
- Keep `(created_at, total_money, store)` only as an informational collision signal (not a skip condition).

**Impact:**
- Greatly reduced false-positive dedup drops.

---

### C. Canonical transaction day for analytics/reconciliation

**Original:**
- Grouping/filtering frequently used `created_at` date semantics.
- This caused major day-level mismatches vs POS summary when `created_at` lagged transaction event time.

**Updated:**
- `database.py:get_receipts_dataframe()` now uses:
  - `COALESCE(receipt_date, created_at) AS date`
  - date filters on `DATE(COALESCE(receipt_date, created_at))`
- Reconciliation tab computes `event_ts = receipt_date if present else created_at` for day aggregation.

**Impact:**
- Large discrepancy (notably Feb 8) resolved at day-level alignment.

---

### D. Post-sync integrity checks

**Added:**
- Post-sync guardrail query to detect duplicate `(store_id, receipt_number)` groups in synced range and surface alert in UI.

**Impact:**
- Immediate visibility for actual duplicate bill-number anomalies.

---

### E. Dedicated Data Import & Reconciliation tab

**Added:**
- New tab: `🧪 Data Import & Reconciliation`
- Features:
  - Import + reconcile mode
  - Reconcile-only mode
  - CSV upload/path input
  - Daily delta table (gross/refund/net)
  - Diagnostics by receipt type/store/payment
  - Candidate exclusion suggestion
  - Exclusion simulator (store/type/payment)

**Impact:**
- Operational reconciliation moved from ad-hoc scripts into app workflow.

---

## 2) Actual code changes (key snippets)

### 2.1 `app.py` — timezone-safe sync input passing

```python
# Custom/range sync: use Bangkok calendar dates
if hasattr(sync_start_date, 'date'):
    sync_start_date = sync_start_date.date()
if hasattr(sync_end_date, 'date'):
    sync_end_date = sync_end_date.date()
api_start = sync_start_date
api_end = sync_end_date

receipts = fetch_all_receipts(LOYVERSE_TOKEN, api_start, api_end, store_filter)
```

### 2.2 `app.py` — dedup guardrails

```python
existing_core_query = """
    SELECT receipt_id, receipt_number, store_id, created_at, receipt_date, total_money
    FROM receipts
    WHERE DATE(COALESCE(receipt_date, created_at)) >= ?
      AND DATE(COALESCE(receipt_date, created_at)) <= ?
"""

# Skip only by strong keys
if receipt_id and receipt_id in existing_receipt_ids:
    duplicate_by_id_count += 1
    continue

if receipt_number and (receipt_store, receipt_number) in existing_number_keys:
    duplicate_by_number_count += 1
    continue

# weak collision -> signal only
if (receipt_created, receipt_total, receipt_store) in existing_time_amount_store_keys:
    suspicious_time_amount_collisions += 1
```

### 2.3 `app.py` — post-sync duplicate receipt number check

```python
dup_num_query = """
    SELECT store_id, receipt_number, COUNT(*) AS c
    FROM receipts
    WHERE DATE(COALESCE(receipt_date, created_at)) >= ?
      AND DATE(COALESCE(receipt_date, created_at)) <= ?
      AND receipt_number IS NOT NULL
    GROUP BY store_id, receipt_number
    HAVING c > 1
    ORDER BY c DESC
    LIMIT 20
"""
```

### 2.4 `database.py` — canonical date model

```python
SELECT
    COALESCE(r.receipt_date, r.created_at) as date,
    ...

if start_date:
    query += " AND DATE(COALESCE(r.receipt_date, r.created_at)) >= ?"
if end_date:
    query += " AND DATE(COALESCE(r.receipt_date, r.created_at)) <= ?"
```

### 2.5 `app.py` reconciliation tab event timestamp

```python
out["created_at"] = pd.to_datetime(out["created_at"], utc=True, errors="coerce")
out["receipt_date"] = pd.to_datetime(out["receipt_date"], utc=True, errors="coerce")
out["event_ts"] = out["receipt_date"].fillna(out["created_at"])
out["day_bkk"] = out["event_ts"].dt.tz_convert("Asia/Bangkok").dt.date
```

### 2.6 `utils/sync_dates.py`

```python
def get_receipts_api_utc_range(start_date, end_date):
    start_bkk = BANGKOK.localize(datetime.combine(start_date, datetime.min.time()))
    end_bkk = BANGKOK.localize(datetime.combine(end_date, datetime.max.time()))
    return (
        start_bkk.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        end_bkk.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    )
```

---

## 3) Validation performed

### Automated tests
- `python3 test_sync_match.py` passed
- `python3 test_app.py` passed

### Fresh import + overwrite + reconcile test
- Existing DB backed up
- DB overwritten with fresh schema
- Fresh API pull for Feb 1-10 (Bangkok)
- Reconciled against CSV (`sales-summary-2026-02-01-2026-02-10.csv`)

### Key finding from validation
- Using `created_at` day: large mismatch remained.
- Using `receipt_date` (or `event_ts=coalesce(receipt_date,created_at)`): day-level mismatch collapsed to small residual.
- Feb 8 specifically matched exactly under `receipt_date` model.

---

## 4) Detailed logic audit

## 4.1 End-to-end flow (current)
1. User chooses sync range in Bangkok dates.
2. API fetch runs with Bangkok->UTC boundary conversion.
3. Incoming receipts are deduped by strong keys (id / store+receipt_number).
4. Upsert persists receipts, line items, payments.
5. Post-sync duplicate-number integrity check runs.
6. Analytics/reconciliation use transaction day from `receipt_date` fallback `created_at`.

## 4.2 Why this is now safer
- Avoids weak-key dedup false positives.
- Aligns business day with POS report semantics.
- Exposes duplicates and collisions explicitly instead of silently dropping data.

---

## 5) Potential pitfalls / remaining risks

### P1. Residual delta can still exist (~small)
Even after timestamp-model fix, small differences may remain due to:
- report cutoff timing,
- report scope filters in POS export,
- report business rules not represented in raw API receipts.

**Recommendation:** add a residual-delta explainer panel listing exact receipts for days with |delta| > threshold.

### P2. Reconciliation payment mapping is simplified
Current reconciliation maps one payment per receipt with:

```sql
MIN(COALESCE(payment_name, payment_type, 'Unknown'))
```

For split tenders this can misrepresent payment diagnostics.

**Recommendation:** aggregate payment diagnostics from full payments rows, not one MIN value.

### P3. Duplicate logic duplicated in two places
Guardrail dedup logic exists in main sync path and recon-tab helper.

**Risk:** logic drift over time.

**Recommendation:** extract a shared helper function/module for dedup guardrails.

### P4. Range integrity checks still depend on DB date expression
Integrity queries use `DATE(COALESCE(receipt_date, created_at))`, which is correct semantically now, but if future data has malformed timestamps, checks may undercount.

**Recommendation:** add a data-quality check for null/invalid timestamps before aggregation.

### P5. Collision signal is informational only
Same-time/same-amount collisions are surfaced but not triaged.

**Recommendation:** add an optional review table with counts by second/amount/store and export button for manual audit.

### P6. Performance at larger scale
Reconciliation tab reads full receipts and payments into pandas.

**Risk:** memory/time overhead as DB grows.

**Recommendation:** add SQL-side filters for date/store before dataframe merge, and pagination for detail tables.

---

## 6) Recommended next hardening steps
1. **Extract shared dedup guardrail helper** (single source of truth).
2. **Add residual-delta explainer** (top contributing receipts for each mismatch day).
3. **Use full payment-table diagnostics** (support split tenders correctly).
4. **Add strict timestamp QA checks** (null/invalid receipt_date and created_at).
5. **Add reconciliation snapshots** (persist run metadata + deltas for audit trail).

---

## 7) Operational checklist (current best practice)
- Run sync using Bangkok date range.
- Reconcile with the new tab using CSV from same store/scope.
- Prefer `event_ts` (`receipt_date` fallback `created_at`) for business-day reporting.
- Treat weak collisions as review signals, not automatic duplicates.
- Investigate residual deltas with day-level drilldown before approving totals.

---

## 8) Structural aggregation fix (new version accuracy update)

### 8.1 What changed in the data model used by the UI

To eliminate line-item double counting in sales displays, the app now builds two canonical in-memory frames after filtering:

- `line_df`: line-item grain (1 row per sold/refunded item line).
- `receipt_df`: receipt grain (1 row per `bill_number`, with canonical receipt-level fields).

`receipt_df` is generated from `line_df` and normalized to include:
- `day`, `bill_number`, `receipt_type`, `signed_net`, `receipt_discount`,
- `customer_id`, `customer_name`, `store_id`, `payment_name`, `location`, `date`.

If `signed_net` is missing, it is derived from receipt totals with refund sign handling.

### 8.2 Accuracy rules enforced in the UI

The app now follows a strict grain contract:

1. **Sales/net/refund/discount/credit/payment KPIs** -> from `receipt_df`
2. **Quantity/product/unit charts** -> from `line_df`
3. **Transaction counts** -> `nunique(bill_number)` at receipt grain

### 8.3 Areas updated for receipt-level accuracy

The following displays were migrated to the receipt grain for value metrics:

- Top KPI cards (`Total Sales`, unique customer logic for KPI context).
- Daily Sales tab:
  - Sales overview totals
  - daily trend lines
  - discount totals and daily discount charts
  - day-of-week sales metrics
- By Location tab:
  - location sales totals
  - location sales trend over time
  - hourly sales value rollups
- Credit tab:
  - total credit value
  - customer outstanding balances
  - credit vs cash daily comparison
  - cash/credit payment mix totals
- Customer Invoice tab:
  - invoice total amount
  - payment method totals
  - transaction counts at receipt grain
- Interactive Data tab:
  - filtered sales KPI moved to receipt-level rollup
  - transaction count aligned to receipt-level uniqueness
- CRM and Ice Forecast value rollups:
  - customer spend and decline detection now use receipt-level spend
  - location-level sales trend rollups use receipt-level spend

### 8.4 Why data display is more accurate now

Previously, some cards/charts summed receipt-level money fields (`signed_net`, `receipt_discount`) on a line-level frame where each receipt can repeat across multiple lines. That overstates totals for multi-line receipts.

Using `receipt_df` for money metrics guarantees each receipt contributes once to sales/discount/payment/credit value calculations, which aligns with POS receipt semantics.

---

## 9) Key areas to monitor (post-deployment)

1. **Receipt uniqueness health**
   - Monitor duplicate `(store_id, receipt_number)` counts after sync.
   - Investigate any sustained increase.

2. **Grain regression risk**
   - Watch for new code that sums `signed_net` or `receipt_discount` directly from line-level filtered frames.
   - Keep sales/discount/payment metrics tied to `receipt_df`.

3. **Split tender behavior**
   - Payment diagnostics in receipt-level summaries may still simplify split tenders.
   - Reconcile payment distribution vs full payments table periodically.

4. **Null timestamp quality**
   - Validate share of rows where `receipt_date` is null and fallback to `created_at` is used.
   - Alert on sudden increases.

5. **Reconciliation residuals**
   - Track daily `|delta|` thresholds (e.g., > 1% or fixed THB threshold).
   - Keep drilldown exports for anomalous days.

---

## 10) Test suite for aggregation contract

A dedicated suite was added to verify the new structural rules and prevent regression:

- File: `test_aggregation_contract.py`
- Focus:
  - receipt-level money totals are not double-counted
  - line-level quantity remains unchanged
  - transaction counting uses `nunique(bill_number)`
  - source checks confirm canonical frame construction and usage contract in `app.py`

Run:

```bash
python3 test_aggregation_contract.py
```

Expected:
- All checks pass with explicit test names.
