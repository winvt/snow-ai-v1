#!/usr/bin/env python3
"""
Aggregation contract tests for canonical line/receipt data frames.

These tests ensure the app-level data display contract remains:
- Money KPIs from receipt grain
- Quantity/product analytics from line grain
- Transactions from unique bill numbers
"""

import os
import sys
import random
import pandas as pd


def _build_receipt_frame(source_df: pd.DataFrame) -> pd.DataFrame:
    """Mirror the canonical receipt-level aggregation contract."""
    if source_df.empty or "bill_number" not in source_df.columns:
        return pd.DataFrame(
            columns=[
                "day",
                "bill_number",
                "receipt_type",
                "signed_net",
                "receipt_discount",
                "customer_id",
                "store_id",
                "payment_name",
                "location",
            ]
        )

    group_cols = ["day", "bill_number"] if "day" in source_df.columns else ["bill_number"]

    agg_map = {}
    for col in [
        "receipt_type",
        "signed_net",
        "receipt_discount",
        "customer_id",
        "store_id",
        "payment_name",
        "location",
        "receipt_total",
    ]:
        if col in source_df.columns:
            agg_map[col] = "first"

    if agg_map:
        out = source_df.groupby(group_cols, as_index=False).agg(agg_map)
    else:
        out = source_df[group_cols].drop_duplicates().reset_index(drop=True)

    if "receipt_discount" in out.columns:
        out["receipt_discount"] = out["receipt_discount"].fillna(0)

    if (
        "signed_net" not in out.columns
        and {"receipt_total", "receipt_discount", "receipt_type"}.issubset(out.columns)
    ):
        receipt_net = out["receipt_total"].fillna(0) - out["receipt_discount"].fillna(0)
        is_refund = out["receipt_type"].astype(str).str.lower().eq("refund")
        out["signed_net"] = receipt_net.where(~is_refund, -receipt_net)

    return out


def test_receipt_sales_not_line_double_counted():
    # Two lines belong to the same bill, so line-level signed_net sum is wrong.
    line_df = pd.DataFrame(
        [
            {
                "day": "2026-02-05",
                "bill_number": "R-001",
                "receipt_type": "SALE",
                "signed_net": 100.0,
                "receipt_discount": 5.0,
                "quantity": 2,
            },
            {
                "day": "2026-02-05",
                "bill_number": "R-001",
                "receipt_type": "SALE",
                "signed_net": 100.0,
                "receipt_discount": 5.0,
                "quantity": 3,
            },
            {
                "day": "2026-02-05",
                "bill_number": "R-002",
                "receipt_type": "SALE",
                "signed_net": 50.0,
                "receipt_discount": 0.0,
                "quantity": 1,
            },
        ]
    )

    receipt_df = _build_receipt_frame(line_df)

    line_total_wrong = line_df["signed_net"].sum()
    receipt_total_correct = receipt_df["signed_net"].sum()

    assert line_total_wrong == 250.0
    assert receipt_total_correct == 150.0
    assert receipt_total_correct != line_total_wrong


def test_discount_totals_use_receipt_grain():
    line_df = pd.DataFrame(
        [
            {"day": "2026-02-05", "bill_number": "R-001", "receipt_discount": 10.0},
            {"day": "2026-02-05", "bill_number": "R-001", "receipt_discount": 10.0},
            {"day": "2026-02-05", "bill_number": "R-002", "receipt_discount": 0.0},
        ]
    )
    receipt_df = _build_receipt_frame(line_df)

    assert line_df["receipt_discount"].sum() == 20.0
    assert receipt_df["receipt_discount"].sum() == 10.0


def test_transaction_count_uses_unique_bill_number():
    line_df = pd.DataFrame(
        [
            {"bill_number": "R-001"},
            {"bill_number": "R-001"},
            {"bill_number": "R-002"},
            {"bill_number": "R-003"},
        ]
    )
    receipt_df = _build_receipt_frame(line_df)

    assert len(line_df) == 4
    assert receipt_df["bill_number"].nunique() == 3


def test_quantity_stays_line_level():
    line_df = pd.DataFrame(
        [
            {"day": "2026-02-05", "bill_number": "R-001", "quantity": 2},
            {"day": "2026-02-05", "bill_number": "R-001", "quantity": 3},
            {"day": "2026-02-05", "bill_number": "R-002", "quantity": 1},
        ]
    )
    receipt_df = _build_receipt_frame(line_df)

    assert line_df["quantity"].sum() == 6
    assert receipt_df["bill_number"].nunique() == 2


def test_source_has_canonical_frame_contract():
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    required_markers = [
        "line_df = df.copy()",
        "def build_receipt_frame(source_df):",
        "def compute_sales_kpis(receipt_frame, line_frame):",
        "def build_reconciliation_monitor(receipt_frame, line_frame, tolerance=0.01):",
        "receipt_df = build_receipt_frame(line_df)",
        "filtered_receipt_df = build_receipt_frame(filtered_df)",
        "invoice_monitor = build_reconciliation_monitor(invoice_receipt_df, invoice_df)",
    ]
    for marker in required_markers:
        assert marker in content, f"Missing marker in app.py: {marker}"


def test_randomized_receipt_level_sales_matches_unique_bill_sum():
    rng = random.Random(42)
    rows = []
    expected = {}
    for i in range(1, 121):
        bill = f"R-{i:04d}"
        signed_net = round(rng.uniform(-300, 2500), 2)
        expected[bill] = signed_net
        line_count = rng.randint(1, 6)
        for _ in range(line_count):
            rows.append(
                {
                    "day": "2026-02-10",
                    "bill_number": bill,
                    "receipt_type": "refund" if signed_net < 0 else "sale",
                    "signed_net": signed_net,
                    "receipt_discount": round(rng.uniform(0, 100), 2),
                    "quantity": rng.randint(1, 12),
                }
            )

    line_df = pd.DataFrame(rows)
    receipt_df = _build_receipt_frame(line_df)
    expected_total = round(sum(expected.values()), 2)
    actual_total = round(float(receipt_df["signed_net"].sum()), 2)

    assert receipt_df["bill_number"].nunique() == len(expected)
    assert actual_total == expected_total


def test_randomized_transaction_count_equals_unique_bills():
    rng = random.Random(7)
    rows = []
    unique_bills = set()
    for i in range(500):
        bill = f"T-{rng.randint(1, 150):03d}"
        unique_bills.add(bill)
        rows.append(
            {
                "day": "2026-02-11",
                "bill_number": bill,
                "quantity": rng.randint(1, 10),
            }
        )

    line_df = pd.DataFrame(rows)
    receipt_df = _build_receipt_frame(line_df)

    assert receipt_df["bill_number"].nunique() == len(unique_bills)
    assert receipt_df.shape[0] == len(unique_bills)


def test_randomized_signed_net_fallback_from_receipt_total():
    rng = random.Random(99)
    rows = []
    expected_total = 0.0
    for i in range(1, 81):
        bill = f"F-{i:04d}"
        receipt_type = "refund" if rng.random() < 0.25 else "sale"
        receipt_total = round(rng.uniform(50, 3000), 2)
        receipt_discount = round(rng.uniform(0, 200), 2)
        receipt_net = receipt_total - receipt_discount
        signed = -receipt_net if receipt_type == "refund" else receipt_net
        expected_total += signed
        for _ in range(rng.randint(1, 4)):
            rows.append(
                {
                    "day": "2026-02-12",
                    "bill_number": bill,
                    "receipt_type": receipt_type,
                    "receipt_total": receipt_total,
                    "receipt_discount": receipt_discount,
                    "quantity": rng.randint(1, 5),
                }
            )

    line_df = pd.DataFrame(rows)
    receipt_df = _build_receipt_frame(line_df)

    assert "signed_net" in receipt_df.columns
    assert round(float(receipt_df["signed_net"].sum()), 2) == round(expected_total, 2)


def test_randomized_order_invariance_for_receipt_totals():
    rng = random.Random(123)
    rows = []
    for i in range(1, 101):
        bill = f"O-{i:04d}"
        signed_net = round(rng.uniform(-150, 2200), 2)
        for _ in range(rng.randint(1, 5)):
            rows.append(
                {
                    "day": "2026-02-13",
                    "bill_number": bill,
                    "receipt_type": "refund" if signed_net < 0 else "sale",
                    "signed_net": signed_net,
                    "receipt_discount": round(rng.uniform(0, 90), 2),
                }
            )

    df_a = pd.DataFrame(rows)
    df_b = pd.DataFrame(list(reversed(rows)))  # deterministic shuffled order
    a = _build_receipt_frame(df_a).sort_values(["day", "bill_number"]).reset_index(drop=True)
    b = _build_receipt_frame(df_b).sort_values(["day", "bill_number"]).reset_index(drop=True)

    assert round(float(a["signed_net"].sum()), 2) == round(float(b["signed_net"].sum()), 2)
    assert int(a["bill_number"].nunique()) == int(b["bill_number"].nunique())


def test_randomized_daily_rollup_matches_expected_receipt_map():
    rng = random.Random(314)
    days = ["2026-02-14", "2026-02-15", "2026-02-16"]
    rows = []
    expected_by_day = {d: 0.0 for d in days}
    for i in range(1, 151):
        day = rng.choice(days)
        bill = f"D-{i:04d}"
        signed_net = round(rng.uniform(-400, 2600), 2)
        expected_by_day[day] += signed_net
        for _ in range(rng.randint(1, 3)):
            rows.append(
                {
                    "day": day,
                    "bill_number": bill,
                    "receipt_type": "refund" if signed_net < 0 else "sale",
                    "signed_net": signed_net,
                    "quantity": rng.randint(1, 8),
                }
            )

    line_df = pd.DataFrame(rows)
    receipt_df = _build_receipt_frame(line_df)
    got = receipt_df.groupby("day", as_index=False)["signed_net"].sum()
    got_map = {r["day"]: round(float(r["signed_net"]), 2) for _, r in got.iterrows()}
    exp_map = {k: round(v, 2) for k, v in expected_by_day.items()}

    assert got_map == exp_map


def test_weird_empty_aggregation_does_not_error():
    """Weird case: frame missing all optional aggregate columns should still build."""
    line_df = pd.DataFrame(
        [
            {"bill_number": "X-001", "day": "2026-02-20"},
            {"bill_number": "X-001", "day": "2026-02-20"},
            {"bill_number": "X-002", "day": "2026-02-20"},
        ]
    )
    receipt_df = _build_receipt_frame(line_df)
    assert receipt_df.shape[0] == 2
    assert set(receipt_df.columns) == {"day", "bill_number"}


def test_weird_missing_bill_number_returns_empty_contract_frame():
    """Weird case: if bill_number is missing entirely, return empty contract frame."""
    line_df = pd.DataFrame([{"day": "2026-02-20", "signed_net": 10.0}])
    receipt_df = _build_receipt_frame(line_df)
    assert receipt_df.empty
    assert "bill_number" in receipt_df.columns


def run_all():
    tests = [
        test_receipt_sales_not_line_double_counted,
        test_discount_totals_use_receipt_grain,
        test_transaction_count_uses_unique_bill_number,
        test_quantity_stays_line_level,
        test_source_has_canonical_frame_contract,
        test_randomized_receipt_level_sales_matches_unique_bill_sum,
        test_randomized_transaction_count_equals_unique_bills,
        test_randomized_signed_net_fallback_from_receipt_total,
        test_randomized_order_invariance_for_receipt_totals,
        test_randomized_daily_rollup_matches_expected_receipt_map,
        test_weird_empty_aggregation_does_not_error,
        test_weird_missing_bill_number_returns_empty_contract_frame,
    ]
    failed = []
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed.append((t.__name__, e))
    return failed


if __name__ == "__main__":
    print("Aggregation contract test suite\n")
    failures = run_all()
    if failures:
        print(f"\n❌ {len(failures)} test(s) failed")
        sys.exit(1)
    print("\n✅ All aggregation contract tests passed.")
    sys.exit(0)
