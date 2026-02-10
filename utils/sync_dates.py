"""
Timezone-safe date range conversion for Loyverse API sync.
Bangkok (Asia/Bangkok, GMT+7) calendar dates → UTC created_at_min / created_at_max.
Used so dashboard sync matches POS/CSV exports that use Bangkok day.
"""
from datetime import datetime, date
from typing import Tuple, Union

import pytz

BANGKOK = pytz.timezone("Asia/Bangkok")
UTC = pytz.UTC


def get_receipts_api_utc_range(
    start_date: date, end_date: date
) -> Tuple[str, str]:
    """
    Return (created_at_min, created_at_max) in UTC ISO format for the Loyverse API,
    so that all receipts whose Bangkok local time falls on start_date..end_date are included.

    - start_date: first Bangkok calendar day (inclusive) → 00:00:00 Bangkok in UTC.
    - end_date: last Bangkok calendar day (inclusive) → 23:59:59.999 Bangkok in UTC.
    """
    start_bkk = BANGKOK.localize(datetime.combine(start_date, datetime.min.time()))
    end_bkk = BANGKOK.localize(datetime.combine(end_date, datetime.max.time()))
    start_utc = start_bkk.astimezone(UTC)
    end_utc = end_bkk.astimezone(UTC)
    return (
        start_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        end_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    )


def utc_to_bangkok_date(utc_timestamp: Union[str, datetime]) -> date:
    """Convert a UTC timestamp to Bangkok calendar date (for display / grouping)."""
    if utc_timestamp is None:
        return None
    if isinstance(utc_timestamp, str):
        s = utc_timestamp.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    else:
        dt = utc_timestamp
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    elif dt.tzinfo != UTC:
        dt = dt.astimezone(UTC)
    return dt.astimezone(BANGKOK).date()
