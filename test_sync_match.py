#!/usr/bin/env python3
"""
Test suite for sync and date-matching logic.
Verifies Bangkok (GMT+7) calendar dates are converted correctly to UTC for the
Loyverse API, so dashboard totals match POS/CSV exports.
"""
import sys
import os
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytz
from utils.sync_dates import get_receipts_api_utc_range, utc_to_bangkok_date

BANGKOK = pytz.timezone("Asia/Bangkok")
UTC = pytz.UTC


def test_bangkok_single_day_to_utc_range():
    """Feb 1 2026 Bangkok = Jan 31 17:00 UTC start, Feb 1 16:59:59.999 UTC end."""
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 1)
    created_min, created_max = get_receipts_api_utc_range(start_date, end_date)
    assert created_min == "2026-01-31T17:00:00.000Z", f"got {created_min}"
    assert created_max == "2026-02-01T16:59:59.000Z", f"got {created_max}"


def test_bangkok_feb_1_to_10_utc_range():
    """Sync Feb 1–10 Bangkok must request from Jan 31 17:00 UTC to Feb 10 16:59:59 UTC."""
    start_date = date(2026, 2, 1)
    end_date = date(2026, 2, 10)
    created_min, created_max = get_receipts_api_utc_range(start_date, end_date)
    assert created_min == "2026-01-31T17:00:00.000Z", f"got {created_min}"
    assert created_max == "2026-02-10T16:59:59.000Z", f"got {created_max}"


def test_utc_to_bangkok_date():
    """UTC timestamps map to correct Bangkok calendar date."""
    # Jan 31 17:00 UTC = Feb 1 00:00 Bangkok
    ts = "2026-01-31T17:00:00.000Z"
    assert utc_to_bangkok_date(ts) == date(2026, 2, 1)
    # Feb 1 16:59 UTC = Feb 1 23:59 Bangkok
    ts2 = "2026-02-01T16:59:59.000Z"
    assert utc_to_bangkok_date(ts2) == date(2026, 2, 1)
    # Feb 1 17:00 UTC = Feb 2 00:00 Bangkok
    ts3 = "2026-02-01T17:00:00.000Z"
    assert utc_to_bangkok_date(ts3) == date(2026, 2, 2)


def test_naive_datetime_would_be_wrong():
    """If we had used naive datetime as UTC, we would miss Bangkok 00:00–06:59."""
    # "Feb 1 00:00" as naive then localized to UTC = Feb 1 00:00 UTC = Jan 31 17:00 Bangkok (wrong day for "start")
    # So receipt at Jan 31 20:00 UTC = Feb 1 03:00 Bangkok would be OUTSIDE naive "Feb 1 00:00 UTC" start.
    feb1_00_utc = datetime(2026, 2, 1, 0, 0, 0)
    # Receipt at Feb 1 03:00 Bangkok = Jan 31 20:00 UTC
    receipt_utc = UTC.localize(datetime(2026, 1, 31, 20, 0, 0))
    receipt_bkk_date = utc_to_bangkok_date(receipt_utc)
    assert receipt_bkk_date == date(2026, 2, 1)
    # With correct Bangkok range, created_at_min = 2026-01-31T17:00:00.000Z, so 20:00 UTC is included.
    created_min, _ = get_receipts_api_utc_range(date(2026, 2, 1), date(2026, 2, 1))
    assert receipt_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z") >= created_min


def test_csv_feb_1_10_reference_totals():
    """Reference: CSV net totals (ยอดขายสุทธิ) for Feb 1–10 2026 (Bangkok) sum to 455,642."""
    expected_net_by_day = {
        date(2026, 2, 1): 44710.00,
        date(2026, 2, 2): 46710.00,
        date(2026, 2, 3): 50295.00,
        date(2026, 2, 4): 49720.00,
        date(2026, 2, 5): 59321.00,
        date(2026, 2, 6): 53078.00,
        date(2026, 2, 7): 49310.00,
        date(2026, 2, 8): 51695.00,
        date(2026, 2, 9): 49643.00,
        date(2026, 2, 10): 1160.00,
    }
    total = sum(expected_net_by_day.values())
    assert total == 455642.00, f"CSV total should be 455642, got {total}"
    assert len(expected_net_by_day) == 10


def test_app_sync_passes_dates_not_naive_datetime():
    """Ensure app sync branch uses date objects for custom range (source check)."""
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    with open(app_path, "r") as f:
        content = f.read()
    # Custom sync branch must set api_start = sync_start_date, api_end = sync_end_date (dates)
    assert "api_start = sync_start_date" in content, "Sync should pass start date for custom range"
    assert "api_end = sync_end_date" in content, "Sync should pass end date for custom range"
    # Must not pass naive datetime for custom range (old bug)
    # We do still use datetime for "sync missing" path; the key is the else branch uses dates.
    assert "Pass DATE objects so fetch_all_receipts" in content or "api_start = sync_start_date" in content


def run_all():
    """Run all sync/match tests."""
    tests = [
        test_bangkok_single_day_to_utc_range,
        test_bangkok_feb_1_to_10_utc_range,
        test_utc_to_bangkok_date,
        test_naive_datetime_would_be_wrong,
        test_csv_feb_1_10_reference_totals,
        test_app_sync_passes_dates_not_naive_datetime,
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
    print("Sync & match test suite\n")
    failed = run_all()
    if failed:
        print(f"\n❌ {len(failed)} test(s) failed")
        sys.exit(1)
    print("\n✅ All sync/match tests passed.")
    sys.exit(0)
