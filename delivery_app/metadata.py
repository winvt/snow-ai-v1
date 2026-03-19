"""Seed and sync helpers for delivery customer metadata."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from typing import Dict, List

from sqlalchemy import func, select

from delivery_app.db import DeliveryCustomer, DeliveryLocation
from delivery_app.repository import UNASSIGNED_LOCATION_ID, UNASSIGNED_LOCATION_NAME


SEED_METADATA_PATH = Path(__file__).resolve().parent / "seed_delivery_metadata.json"


def load_seed_metadata(path: Path = SEED_METADATA_PATH) -> Dict[str, List[Dict[str, str]]]:
    """Load the bundled customer/location snapshot used for first deploys."""
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def ensure_unassigned_location(db_session, *, now: datetime | None = None) -> DeliveryLocation:
    """Guarantee the synthetic Unassigned location exists."""
    sync_time = now or datetime.utcnow()
    location = db_session.execute(
        select(DeliveryLocation).where(DeliveryLocation.id == UNASSIGNED_LOCATION_ID)
    ).scalar_one_or_none()
    if location is None:
        location = DeliveryLocation(
            id=UNASSIGNED_LOCATION_ID,
            name=UNASSIGNED_LOCATION_NAME,
            source_category_id=None,
            customer_count=0,
            last_synced_at=sync_time,
        )
        db_session.add(location)
    else:
        location.name = UNASSIGNED_LOCATION_NAME
        location.source_category_id = None
        location.last_synced_at = sync_time
    return location


def refresh_location_customer_counts(db_session, *, now: datetime | None = None) -> None:
    """Recompute customer counts for every delivery location."""
    sync_time = now or datetime.utcnow()
    db_session.flush()
    counts = {
        location_id: int(customer_count)
        for location_id, customer_count in db_session.execute(
            select(DeliveryCustomer.primary_location_id, func.count())
            .group_by(DeliveryCustomer.primary_location_id)
        ).all()
    }
    for location in db_session.execute(select(DeliveryLocation)).scalars():
        location.customer_count = counts.get(location.id, 0)
        location.last_synced_at = sync_time


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
        "unassigned_customers": location_counts.get(UNASSIGNED_LOCATION_ID, 0),
    }


def sync_delivery_customers_from_api_payload(
    db_session,
    customers_payload: List[Dict[str, object]],
) -> Dict[str, int]:
    """Upsert customer names/contact details from the Loyverse customers API."""
    now = datetime.utcnow()
    ensure_unassigned_location(db_session, now=now)

    normalized_customers: Dict[str, Dict[str, str | None]] = {}
    skipped_customers = 0
    for row in customers_payload:
        customer_id = str(row.get("id") or "").strip()
        if not customer_id:
            skipped_customers += 1
            continue
        normalized_customers[customer_id] = {
            "customer_id": customer_id,
            "name": str(row.get("name") or row.get("customer_code") or "Unknown").strip() or "Unknown",
            "customer_code": str(row.get("customer_code") or "").strip() or None,
            "phone": str(row.get("phone") or "").strip() or None,
        }

    if normalized_customers:
        existing_rows = db_session.execute(
            select(DeliveryCustomer).where(DeliveryCustomer.customer_id.in_(normalized_customers.keys()))
        ).scalars()
        existing_map = {row.customer_id: row for row in existing_rows}
    else:
        existing_map = {}

    new_customers = 0
    updated_customers = 0
    unchanged_customers = 0

    for customer_id, customer in normalized_customers.items():
        model = existing_map.get(customer_id)
        if model is None:
            db_session.add(
                DeliveryCustomer(
                    customer_id=customer_id,
                    name=customer["name"] or "Unknown",
                    customer_code=customer["customer_code"],
                    phone=customer["phone"],
                    primary_location_id=UNASSIGNED_LOCATION_ID,
                    last_synced_at=now,
                )
            )
            new_customers += 1
            continue

        changed = False
        if model.name != customer["name"]:
            model.name = customer["name"] or "Unknown"
            changed = True
        if model.customer_code != customer["customer_code"]:
            model.customer_code = customer["customer_code"]
            changed = True
        if model.phone != customer["phone"]:
            model.phone = customer["phone"]
            changed = True

        if changed:
            model.last_synced_at = now
            updated_customers += 1
        else:
            unchanged_customers += 1

    refresh_location_customer_counts(db_session, now=now)
    db_session.commit()

    location_count = db_session.execute(select(func.count()).select_from(DeliveryLocation)).scalar_one()
    unassigned_customers = db_session.execute(
        select(func.count()).select_from(DeliveryCustomer).where(
            DeliveryCustomer.primary_location_id == UNASSIGNED_LOCATION_ID
        )
    ).scalar_one()
    return {
        "locations": int(location_count or 0),
        "fetched_customers": len(customers_payload),
        "customers": len(normalized_customers),
        "new_customers": new_customers,
        "updated_customers": updated_customers,
        "unchanged_customers": unchanged_customers,
        "skipped_customers": skipped_customers,
        "unassigned_customers": int(unassigned_customers or 0),
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
