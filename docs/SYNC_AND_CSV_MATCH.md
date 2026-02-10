# Sync logic and matching POS/CSV totals

## Your CSV (Feb 1–10, 2026) – reference totals

From `sales-summary-2026-02-01-2026-02-10.csv` (Bangkok calendar days):

| วันที่ (Date) | ยอดขายรวม (Gross) | การคืนเงิน (Refunds) | ส่วนลด (Discount) | ยอดขายสุทธิ (Net) |
|--------------|-------------------|----------------------|--------------------|--------------------|
| 1/2/26       | 45,250.00         | 540.00               | 0.00               | 44,710.00         |
| 2/2/26       | 47,100.00         | 390.00               | 0.00               | 46,710.00         |
| 3/2/26       | 51,150.00         | 855.00               | 0.00               | 50,295.00         |
| 4/2/26       | 51,645.00         | 1,925.00             | 0.00               | 49,720.00         |
| 5/2/26       | 60,046.00         | 725.00               | 0.00               | 59,321.00         |
| 6/2/26       | 53,848.00         | 770.00               | 0.00               | 53,078.00         |
| 7/2/26       | 54,045.00         | 4,735.00             | 0.00               | 49,310.00         |
| 8/2/26       | 52,405.00         | 710.00               | 0.00               | 51,695.00         |
| 9/2/26       | 50,253.00         | 610.00               | 0.00               | 49,643.00         |
| 10/2/26      | 1,370.00          | 210.00               | 0.00               | 1,160.00          |

- **Net (ยอดขายสุทธิ)** = Gross − Refunds − Discount.  
- **Total net (period)** = 455,642.00 (sum of net column).

The POS export uses **Bangkok (GMT+7) calendar day** for “วันที่”.

---

## Why the dashboard didn’t match (and what was fixed)

### 1. Sync date range was wrong (fixed)

- When you picked “Feb 1 – Feb 10” you meant **Bangkok** calendar days.
- The app was sending **naive** datetimes to the Loyverse API and treating them as **UTC**.
  - So it requested: Feb 1 00:00 **UTC** → Feb 10 23:59 **UTC**.
  - That corresponds to **Bangkok** Feb 1 07:00 – Feb 11 06:59, not Feb 1 00:00 – Feb 10 23:59 Bangkok.

Effects:

- **Missing:** Receipts from **Feb 1 00:00–06:59 Bangkok** (they are Jan 31 17:00–23:59 UTC and were outside the requested range).
- **Wrong day:** Some late-evening Bangkok receipts could be counted on the next UTC day in the DB.

**Fix (in code):** For “Sync Custom Range” (and similar range syncs), the app now passes **date** objects to `fetch_all_receipts()`. That function converts **Bangkok** start-of-day and end-of-day to UTC, so the API receives the correct UTC window for the chosen Bangkok dates. Sync for “Feb 1–10” now pulls all receipts whose **Bangkok** time falls on Feb 1–10.

### 2. How the dashboard shows totals

- **Data:** Receipts are stored with `created_at` in UTC. When loading, the app converts each receipt to **Bangkok** date and stores it in the `day` column.
- **Filter:** The quick date navigator (e.g. “Feb 1 – Feb 10”) filters on this **Bangkok** `day`.
- **Net sales:** The app uses **signed net** at receipt level:  
  `receipt_total - receipt_discount`, and **refunds** are negated. So “net” in the dashboard is comparable to **ยอดขายสุทธิ** in your CSV.

So:

- **Before the fix:** Sync asked for the wrong UTC range → some Bangkok-day receipts were missing or attributed to the wrong day → totals and per-day numbers didn’t match the CSV.
- **After the fix:** Sync asks for the Bangkok calendar range → all receipts for Feb 1–10 Bangkok are fetched → daily and period totals should align with the POS/CSV (aside from rounding or minor definition differences).

---

## How to check that transactions match

1. **Re-sync the range (Bangkok):**  
   Settings → Custom Date Range → set **Feb 1, 2026** to **Feb 10, 2026** → “Sync Custom Range”.  
   (With the fix, this requests the correct Bangkok→UTC range.)

2. **Load database** and set the quick date range to **Feb 1 – Feb 10**.

3. **Compare:**
   - **Daily net:** In “Daily Sales”, compare each day’s net to the “ยอดขายสุทธิ” column in the CSV. They should be very close (same definition: gross − refunds − discount, with refunds as negative).
   - **Period total:** Sum of daily nets in the dashboard should be close to **455,642** (or whatever your CSV total is for that period).
   - **Transaction count:** Optionally compare number of receipts per day with the POS if you have that.

4. **If a day still differs:**  
   - Confirm the CSV is for the same store(s) and same “net” definition.  
   - Check for any store filter in the dashboard (e.g. “Filter by Store”) so you’re comparing same scope as the export.

---

## Summary

| Item | Detail |
|------|--------|
| **CSV** | Bangkok calendar day; net = gross − refunds − discount. |
| **Dashboard** | Uses Bangkok `day` (from UTC `created_at`) and signed net (refunds negative). |
| **Bug** | Sync used naive datetime → interpreted as UTC → wrong API range vs Bangkok. |
| **Fix** | Custom/range sync now passes **dates** so the API range is Bangkok start/end of day in UTC. |
| **After fix** | Re-sync Feb 1–10, then compare daily and period totals to the CSV; they should match. |
