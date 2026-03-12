#!/usr/bin/env python3
"""Sync delivery customer/location metadata from the local SQLite POS DB to the delivery app database."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import os
import sqlite3
from typing import Dict, List

import pandas as pd
from sqlalchemy import select

from delivery_app.config import load_settings
from delivery_app.db import DeliveryCustomer, DeliveryLocation, create_db_engine, create_session_factory, init_db
from delivery_app.repository import UNASSIGNED_LOCATION_ID, UNASSIGNED_LOCATION_NAME


def compute_primary_locations(source_sqlite_path: str) -> Dict[str, Dict[str, str]]:
    """Compute primary location per customer from receipt history."""
    conn = sqlite3.connect(source_sqlite_path)
    customer_df = pd.read_sql_query(
        """
        WITH customer_location AS (
            SELECT
                r.customer_id AS customer_id,
                c.category_id AS category_id,
                c.name AS location_name,
                COUNT(DISTINCT r.receipt_id) AS receipt_count,
                MAX(COALESCE(r.receipt_date, r.created_at)) AS latest_receipt_at
            FROM receipts r
            JOIN line_items li ON r.receipt_id = li.receipt_id
            LEFT JOIN items i ON li.item_id = i.item_id
            LEFT JOIN categories c ON i.category_id = c.category_id
            WHERE r.customer_id IS NOT NULL
              AND c.name IS NOT NULL
            GROUP BY r.customer_id, c.category_id, c.name
        ),
        ranked AS (
            SELECT
                customer_id,
                category_id,
                location_name,
                receipt_count,
                latest_receipt_at,
                ROW_NUMBER() OVER (
                    PARTITION BY customer_id
                    ORDER BY receipt_count DESC, latest_receipt_at DESC, location_name ASC
                ) AS rank_index
            FROM customer_location
        )
        SELECT customer_id, category_id, location_name
        FROM ranked
        WHERE rank_index = 1
        """,
        conn,
    )
    customers = pd.read_sql_query(
        "SELECT customer_id, COALESCE(name, customer_code, 'Unknown') AS name, customer_code, phone FROM customers",
        conn,
    )
    categories = pd.read_sql_query(
        "SELECT category_id, name FROM categories WHERE name IS NOT NULL ORDER BY name",
        conn,
    )
    conn.close()

    location_rows = [
        {
            "id": row["category_id"],
            "name": row["name"],
            "source_category_id": row["category_id"],
        }
        for _, row in categories.iterrows()
    ]
    location_rows.append(
        {
            "id": UNASSIGNED_LOCATION_ID,
            "name": UNASSIGNED_LOCATION_NAME,
            "source_category_id": None,
        }
    )

    primary_map = {
        row["customer_id"]: {
            "location_id": row["category_id"],
            "location_name": row["location_name"],
        }
        for _, row in customer_df.iterrows()
    }

    customer_rows = []
    for _, row in customers.iterrows():
        match = primary_map.get(row["customer_id"])
        customer_rows.append(
            {
                "customer_id": row["customer_id"],
                "name": row["name"],
                "customer_code": row["customer_code"],
                "phone": row["phone"],
                "primary_location_id": match["location_id"] if match else UNASSIGNED_LOCATION_ID,
            }
        )

    return {
        "locations": location_rows,
        "customers": customer_rows,
    }


def sync_delivery_metadata(source_sqlite_path: str, delivery_database_url: str) -> Dict[str, int]:
    """Upsert derived locations and customers into the delivery database."""
    payload = compute_primary_locations(source_sqlite_path)
    engine = create_db_engine(delivery_database_url)
    init_db(engine)
    session_factory = create_session_factory(engine)
    db_session = session_factory()
    now = datetime.utcnow()

    location_counts = Counter(row["primary_location_id"] for row in payload["customers"])
    for location in payload["locations"]:
        model = db_session.execute(
            select(DeliveryLocation).where(DeliveryLocation.id == location["id"])
        ).scalar_one_or_none()
        if model is None:
            model = DeliveryLocation(
                id=location["id"],
                name=location["name"],
                source_category_id=location["source_category_id"],
                customer_count=location_counts.get(location["id"], 0),
                last_synced_at=now,
            )
            db_session.add(model)
        else:
            model.name = location["name"]
            model.source_category_id = location["source_category_id"]
            model.customer_count = location_counts.get(location["id"], 0)
            model.last_synced_at = now

    for customer in payload["customers"]:
        model = db_session.execute(
            select(DeliveryCustomer).where(DeliveryCustomer.customer_id == customer["customer_id"])
        ).scalar_one_or_none()
        if model is None:
            model = DeliveryCustomer(
                customer_id=customer["customer_id"],
                name=customer["name"],
                customer_code=customer["customer_code"],
                phone=customer["phone"],
                primary_location_id=customer["primary_location_id"],
                last_synced_at=now,
            )
            db_session.add(model)
        else:
            model.name = customer["name"]
            model.customer_code = customer["customer_code"]
            model.phone = customer["phone"]
            model.primary_location_id = customer["primary_location_id"]
            model.last_synced_at = now

    db_session.commit()
    db_session.close()
    return {
        "locations": len(payload["locations"]),
        "customers": len(payload["customers"]),
        "unassigned_customers": location_counts.get(UNASSIGNED_LOCATION_ID, 0),
    }


def main() -> None:
    """CLI entrypoint."""
    settings = load_settings()
    result = sync_delivery_metadata(settings.source_sqlite_path, settings.delivery_database_url)
    print(
        "Synced delivery metadata: "
        f"{result['locations']} locations, "
        f"{result['customers']} customers, "
        f"{result['unassigned_customers']} unassigned"
    )


if __name__ == "__main__":
    main()

