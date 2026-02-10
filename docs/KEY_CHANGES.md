# Key Changes (Current Edit Batch)

## Scope
This file summarizes the changes implemented in the latest edit batch focused on aggregation correctness, reporting accuracy, and regression coverage.

## Files updated in this edit batch
- `app.py`
- `docs/IMPORT_LOGIC_AUDIT.md`
- `test_aggregation_contract.py` (new)

---

## 1) Structural aggregation fix in `app.py`

### Canonical data frames introduced
- Added canonical frames after filtering:
  - `line_df` = line-item grain (existing detailed rows)
  - `receipt_df` = one row per receipt using `build_receipt_frame(source_df)`

### Canonical receipt columns enforced
- `day`
- `bill_number`
- `receipt_type`
- `signed_net`
- `receipt_discount`
- `customer_id`
- `customer_name`
- `store_id`
- `payment_name`
- `location`
- `date`

### Signed net fallback logic
- If `signed_net` is missing, it is derived from:
  - `receipt_total - receipt_discount`
  - refund sign handling using `receipt_type`

---

## 2) Accuracy contract applied across tabs

### Receipt-level metrics (`receipt_df`)
Used for money and receipt-level KPIs:
- sales/net/refund totals
- discounts
- credit totals and credit trends
- payment breakdown totals
- invoice total amount
- location sales totals/trends
- CRM spend trend/decline calculations

### Line-level metrics (`line_df`)
Used for item-level and quantity behavior:
- quantity totals
- product/unit charts
- itemized product tables

### Transaction counting rule
- Transaction counts standardized to `nunique(bill_number)` at receipt grain.

---

## 3) Specific high-impact fixes

- Prevented line-level double counting where `signed_net` and `receipt_discount` were being summed on repeated receipt rows.
- Reworked discount totals and daily discount charts to aggregate from receipt-level records.
- Updated interactive filtered sales KPI to compute from receipt-level filtered data.
- Updated credit and invoice payment summaries to aggregate from receipt-level payment context.
- Reworked location-level and hourly sales rollups to use receipt-level sales while keeping quantity line-level.
- Updated product summary transaction frequency to use unique bill count instead of raw row count where appropriate.

---

## 4) Documentation update

### `docs/IMPORT_LOGIC_AUDIT.md`
Added sections describing:
- the canonical `line_df`/`receipt_df` architecture,
- how this improves display accuracy in the new version,
- key areas to monitor post-change,
- aggregation contract test coverage and run command.

---

## 5) Test suite additions

### New file: `test_aggregation_contract.py`
Added regression tests for aggregation contract:
- `test_receipt_sales_not_line_double_counted`
- `test_discount_totals_use_receipt_grain`
- `test_transaction_count_uses_unique_bill_number`
- `test_quantity_stays_line_level`
- `test_source_has_canonical_frame_contract`
- `test_randomized_receipt_level_sales_matches_unique_bill_sum`
- `test_randomized_transaction_count_equals_unique_bills`

---

## 6) Validation results (latest run)

### Passed
- `python3 test_sync_match.py`
- `python3 test_app.py`
- `python3 test_aggregation_contract.py`

### Environment-dependent script status
- `python3 test_group_message.py` ran but could not send a message because `LINE_RECIPIENT_ID` is missing in environment variables.

---

## 7) Monitoring checklist

- Watch for any new code summing `signed_net` or `receipt_discount` directly from line-level frames.
- Keep all money KPIs tied to `receipt_df`.
- Keep quantity/product analyses tied to `line_df`.
- Keep transaction counts as `nunique(bill_number)`.
- Reconcile daily totals after major UI/reporting changes to catch grain regressions early.
