"""Seed and sync helpers for delivery customer metadata."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List

from sqlalchemy import func, select

from delivery_app.db import DeliveryCustomer, DeliveryLocation


SEED_METADATA_PATH = Path(__file__).resolve().parent / "seed_delivery_metadata.json"


def load_seed_metadata(path: Path = SEED_METADATA_PATH) -> Dict[str, List[Dict[str, str]]]:
    """Load the bundled customer/location snapshot used for first deploys."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def apply_delivery_metadata_payload(db_session, payload: Dict[str, List[Dict[str, str]]]) -> Dict[str, int]:
    """Upsert a customer/location payload into the delivery database."""
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
    return {
        "locations": len(payload["locations"]),
        "customers": len(payload["customers"]),
        "unassigned_customers": location_counts.get("unassigned", 0),
    }


def bootstrap_seed_metadata_if_empty(session_factory) -> bool:
    """Populate the delivery DB from the bundled snapshot when no locations exist yet."""
    db_session = session_factory()
    try:
        location_count = db_session.execute(select(func.count()).select_from(DeliveryLocation)).scalar_one()
        if int(location_count or 0) > 0:
            return False
        payload = load_seed_metadata()
        apply_delivery_metadata_payload(db_session, payload)
        return True
    finally:
        db_session.close()
