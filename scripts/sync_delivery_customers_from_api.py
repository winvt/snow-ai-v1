#!/usr/bin/env python3
"""Sync delivery customers directly from the Loyverse customers API."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from delivery_app.config import load_settings
from delivery_app.db import create_db_engine, create_session_factory, init_db
from delivery_app.loyverse_sync import sync_delivery_customers_from_loyverse


def sync_delivery_customers_from_api(delivery_database_url: str, token: str) -> Dict[str, int]:
    """Fetch customers from Loyverse and upsert them into the delivery database."""
    engine = create_db_engine(delivery_database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)
    db_session = session_factory()
    try:
        return sync_delivery_customers_from_loyverse(db_session, token)
    finally:
        db_session.close()


def main() -> None:
    """CLI entrypoint used by Render cron."""
    settings = load_settings()
    token = os.getenv("LOYVERSE_TOKEN", "").strip()
    if not token:
        raise SystemExit("LOYVERSE_TOKEN is required for delivery customer sync")

    result = sync_delivery_customers_from_api(settings.delivery_database_url, token)
    print(
        "Synced delivery customers from Loyverse API: "
        f"{result['customers']} processed, "
        f"{result['new_customers']} new, "
        f"{result['updated_customers']} updated, "
        f"{result['unchanged_customers']} unchanged, "
        f"{result['skipped_customers']} skipped, "
        f"{result['unassigned_customers']} unassigned"
    )


if __name__ == "__main__":
    main()
