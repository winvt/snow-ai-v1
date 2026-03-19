#!/usr/bin/env python3
"""Trigger delivery customer sync through the live delivery service."""

from __future__ import annotations

import os
from pathlib import Path
import sys

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    base_url = os.getenv("APP_BASE_URL", "").rstrip("/")
    sync_secret = os.getenv("DELIVERY_SYNC_SECRET", "").strip()

    if not base_url:
        raise SystemExit("APP_BASE_URL is required for delivery customer sync trigger")
    if not sync_secret:
        raise SystemExit("DELIVERY_SYNC_SECRET is required for delivery customer sync trigger")

    response = requests.post(
        f"{base_url}/internal/sync/customers",
        headers={"X-Delivery-Sync-Secret": sync_secret},
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result", {})
    print(
        "Triggered delivery customer sync: "
        f"{result.get('customers', 0)} processed, "
        f"{result.get('new_customers', 0)} new, "
        f"{result.get('updated_customers', 0)} updated, "
        f"{result.get('unchanged_customers', 0)} unchanged"
    )


if __name__ == "__main__":
    main()
