"""Recovery helpers for moving delivery reports from fallback SQLite into the main database."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from sqlalchemy import inspect, select, text

from delivery_app.db import (
    DeliveryCustomer,
    DeliveryLocation,
    DeliveryUser,
    VisitReport,
    create_db_engine,
    create_session_factory,
    init_db,
)


def _sqlite_url(path: str) -> str:
    resolved = Path(path).expanduser().resolve()
    return f"sqlite:///{resolved}"


def _load_table_rows(engine, table_name: str) -> List[Dict]:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if table_name not in table_names:
        return []
    with engine.connect() as connection:
        rows = connection.execute(text(f"SELECT * FROM {table_name}")).mappings().all()
    return [dict(row) for row in rows]


def _coerce_datetime(value):
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        return value
    text_value = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text_value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def import_reports_from_sqlite(
    source_sqlite_path: str,
    destination_database_url: str,
) -> Dict[str, int]:
    """Import delivery users, metadata, and visit reports from a fallback SQLite database."""
    source_engine = create_db_engine(_sqlite_url(source_sqlite_path))
    destination_engine = create_db_engine(destination_database_url)
    init_db(destination_engine)

    source_locations = _load_table_rows(source_engine, "delivery_locations")
    source_customers = _load_table_rows(source_engine, "delivery_customers")
    source_users = _load_table_rows(source_engine, "delivery_users")
    source_reports = _load_table_rows(source_engine, "visit_reports")

    destination_session_factory = create_session_factory(destination_engine)
    db_session = destination_session_factory()
    try:
        existing_locations = {
            location.id: location
            for location in db_session.execute(select(DeliveryLocation)).scalars().all()
        }
        existing_customers = {
            customer.customer_id: customer
            for customer in db_session.execute(select(DeliveryCustomer)).scalars().all()
        }
        existing_users = {
            user.line_user_id: user
            for user in db_session.execute(select(DeliveryUser)).scalars().all()
        }
        existing_submission_ids = {
            submission_id
            for submission_id, in db_session.execute(select(VisitReport.client_submission_id)).all()
        }

        imported_locations = 0
        imported_customers = 0
        imported_users = 0
        imported_reports = 0
        skipped_reports = 0

        for row in source_locations:
            location = existing_locations.get(row["id"])
            if location is None:
                location = DeliveryLocation(
                    id=row["id"],
                    name=row["name"],
                    source_category_id=row.get("source_category_id"),
                    customer_count=int(row.get("customer_count") or 0),
                    last_synced_at=_coerce_datetime(row.get("last_synced_at")) or datetime.utcnow(),
                )
                db_session.add(location)
                existing_locations[location.id] = location
                imported_locations += 1

        for row in source_customers:
            customer = existing_customers.get(row["customer_id"])
            if customer is None:
                customer = DeliveryCustomer(
                    customer_id=row["customer_id"],
                    name=row["name"],
                    customer_code=row.get("customer_code"),
                    phone=row.get("phone"),
                    primary_location_id=row["primary_location_id"],
                    last_synced_at=_coerce_datetime(row.get("last_synced_at")) or datetime.utcnow(),
                )
                db_session.add(customer)
                existing_customers[customer.customer_id] = customer
                imported_customers += 1

        for row in source_users:
            user = existing_users.get(row["line_user_id"])
            if user is None:
                user = DeliveryUser(
                    id=row.get("id"),
                    line_user_id=row["line_user_id"],
                    display_name=row.get("display_name") or row["line_user_id"],
                    picture_url=row.get("picture_url"),
                    status=row.get("status") or "active",
                    access_mode=row.get("access_mode") or "all",
                    created_at=_coerce_datetime(row.get("created_at")) or datetime.utcnow(),
                    last_login_at=_coerce_datetime(row.get("last_login_at")) or datetime.utcnow(),
                )
                db_session.add(user)
                existing_users[user.line_user_id] = user
                imported_users += 1

        for row in source_reports:
            if row["client_submission_id"] in existing_submission_ids:
                skipped_reports += 1
                continue

            if row["customer_id"] not in existing_customers or row["location_id"] not in existing_locations:
                skipped_reports += 1
                continue

            if row["line_user_id"] not in existing_users:
                skipped_reports += 1
                continue

            report = VisitReport(
                id=row.get("id"),
                client_submission_id=row["client_submission_id"],
                line_user_id=row["line_user_id"],
                customer_id=row["customer_id"],
                location_id=row["location_id"],
                photo_object_key=row["photo_object_key"],
                photo_url=row["photo_url"],
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                accuracy_m=float(row["accuracy_m"]) if row.get("accuracy_m") is not None else None,
                captured_at_client=_coerce_datetime(row["captured_at_client"]) or datetime.utcnow(),
                received_at_server=_coerce_datetime(row["received_at_server"]) or datetime.utcnow(),
            )
            db_session.add(report)
            existing_submission_ids.add(report.client_submission_id)
            imported_reports += 1

        db_session.commit()
        return {
            "locations_imported": imported_locations,
            "customers_imported": imported_customers,
            "users_imported": imported_users,
            "reports_imported": imported_reports,
            "reports_skipped": skipped_reports,
            "source_reports": len(source_reports),
        }
    finally:
        db_session.close()
