"""Database operations used by the delivery app."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import and_, delete, func, or_, select

from delivery_app.auth import LineProfile
from delivery_app.db import DeliveryCustomer, DeliveryLocation, DeliveryUser, DeliveryUserLocationAccess, VisitReport


UNASSIGNED_LOCATION_ID = "unassigned"
UNASSIGNED_LOCATION_NAME = "Unassigned"
GUEST_USER_ID = "guest-preview"


def upsert_delivery_user(db_session, profile: LineProfile) -> DeliveryUser:
    """Create or update a delivery user from LINE profile data."""
    user = db_session.execute(
        select(DeliveryUser).where(DeliveryUser.line_user_id == profile.line_user_id)
    ).scalar_one_or_none()
    now = datetime.utcnow()
    if user is None:
        user = DeliveryUser(
            line_user_id=profile.line_user_id,
            display_name=profile.display_name,
            picture_url=profile.picture_url,
            status="active",
            access_mode="all",
            created_at=now,
            last_login_at=now,
        )
        db_session.add(user)
    else:
        user.display_name = profile.display_name
        user.picture_url = profile.picture_url
        user.last_login_at = now
        user.status = "active"
    db_session.commit()
    db_session.refresh(user)
    return user


def get_delivery_user(db_session, line_user_id: str) -> Optional[DeliveryUser]:
    """Fetch a delivery user by LINE user id."""
    return db_session.execute(
        select(DeliveryUser).where(DeliveryUser.line_user_id == line_user_id)
    ).scalar_one_or_none()


def get_or_create_guest_user(db_session) -> DeliveryUser:
    """Return the synthetic guest user used for local/demo mode."""
    user = get_delivery_user(db_session, GUEST_USER_ID)
    now = datetime.utcnow()
    if user is None:
        user = DeliveryUser(
            line_user_id=GUEST_USER_ID,
            display_name="Guest Preview",
            picture_url=None,
            status="active",
            access_mode="all",
            created_at=now,
            last_login_at=now,
        )
        db_session.add(user)
    else:
        user.status = "active"
        user.last_login_at = now
    db_session.commit()
    db_session.refresh(user)
    return user


def get_allowed_location_ids(db_session, user: DeliveryUser, *, enforce_access: bool = True) -> Optional[List[str]]:
    """Return allowed location ids for a user, or None when the user can access all locations."""
    if not enforce_access:
        return None
    if user.access_mode != "assigned":
        return None
    rows = db_session.execute(
        select(DeliveryUserLocationAccess.location_id).where(
            DeliveryUserLocationAccess.line_user_id == user.line_user_id
        )
    ).all()
    return [row[0] for row in rows]


def user_can_access_location(db_session, user: DeliveryUser, location_id: str, *, enforce_access: bool = True) -> bool:
    """Check whether the user can access a specific location."""
    allowed_location_ids = get_allowed_location_ids(db_session, user, enforce_access=enforce_access)
    if allowed_location_ids is None:
        return True
    return location_id in set(allowed_location_ids)


def list_locations(db_session, *, user: Optional[DeliveryUser] = None, enforce_access: bool = True) -> List[Dict]:
    """Return location picker data sorted by name."""
    stmt = select(DeliveryLocation)
    if user is not None:
        allowed_location_ids = get_allowed_location_ids(db_session, user, enforce_access=enforce_access)
        if allowed_location_ids is not None:
            if not allowed_location_ids:
                return []
            stmt = stmt.where(DeliveryLocation.id.in_(allowed_location_ids))
    rows = db_session.execute(stmt.order_by(DeliveryLocation.name.asc())).scalars()
    return [
        {"id": row.id, "name": row.name, "customerCount": row.customer_count}
        for row in rows
    ]


def list_customers(
    db_session,
    *,
    location_id: Optional[str],
    query: Optional[str],
    user: Optional[DeliveryUser] = None,
    enforce_access: bool = True,
) -> List[Dict]:
    """Return customers optionally filtered by location and search text."""
    stmt = select(DeliveryCustomer, DeliveryLocation.name.label("location_name")).join(DeliveryLocation)
    if user is not None:
        allowed_location_ids = get_allowed_location_ids(db_session, user, enforce_access=enforce_access)
        if allowed_location_ids is not None:
            if not allowed_location_ids:
                return []
            stmt = stmt.where(DeliveryCustomer.primary_location_id.in_(allowed_location_ids))
    if location_id:
        stmt = stmt.where(DeliveryCustomer.primary_location_id == location_id)
    if query:
        token = f"%{query.strip()}%"
        stmt = stmt.where(
            DeliveryCustomer.name.ilike(token)
            | DeliveryCustomer.customer_code.ilike(token)
            | DeliveryCustomer.phone.ilike(token)
        )
    stmt = stmt.order_by(DeliveryCustomer.name.asc()).limit(200)
    rows = db_session.execute(stmt).all()
    return [
        {
            "customerId": customer.customer_id,
            "name": customer.name,
            "customerCode": customer.customer_code,
            "phone": customer.phone,
            "locationId": customer.primary_location_id,
            "locationName": location_name,
        }
        for customer, location_name in rows
    ]


def get_customer(db_session, customer_id: str) -> Optional[DeliveryCustomer]:
    """Fetch a delivery customer by id."""
    return db_session.execute(
        select(DeliveryCustomer).where(DeliveryCustomer.customer_id == customer_id)
    ).scalar_one_or_none()


def list_delivery_users_with_access(db_session) -> List[Dict]:
    """Return users plus their current location access state."""
    users = db_session.execute(
        select(DeliveryUser)
        .where(DeliveryUser.line_user_id != GUEST_USER_ID)
        .order_by(DeliveryUser.display_name.asc())
    ).scalars().all()
    access_rows = db_session.execute(select(DeliveryUserLocationAccess)).scalars().all()
    access_map: Dict[str, List[str]] = {}
    for row in access_rows:
        access_map.setdefault(row.line_user_id, []).append(row.location_id)
    for line_user_id in access_map:
        access_map[line_user_id].sort()
    return [
        {
            "lineUserId": user.line_user_id,
            "displayName": user.display_name,
            "status": user.status,
            "accessMode": user.access_mode,
            "allowedLocationIds": access_map.get(user.line_user_id, []),
            "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at else None,
        }
        for user in users
    ]


def set_user_location_access(
    db_session,
    *,
    line_user_id: str,
    access_mode: str,
    location_ids: List[str],
) -> Dict:
    """Persist access mode and location grants for a user."""
    user = get_delivery_user(db_session, line_user_id)
    if user is None:
        raise ValueError("Unknown delivery user")
    if access_mode not in {"all", "assigned"}:
        raise ValueError("access_mode must be 'all' or 'assigned'")

    normalized_location_ids = sorted(set(location_ids))
    if access_mode == "assigned" and normalized_location_ids:
        known_location_ids = {
            row[0]
            for row in db_session.execute(
                select(DeliveryLocation.id).where(DeliveryLocation.id.in_(normalized_location_ids))
            ).all()
        }
        missing = sorted(set(normalized_location_ids) - known_location_ids)
        if missing:
            raise ValueError(f"Unknown location ids: {', '.join(missing)}")

    user.access_mode = access_mode
    db_session.execute(
        delete(DeliveryUserLocationAccess).where(
            DeliveryUserLocationAccess.line_user_id == line_user_id
        )
    )
    if access_mode == "assigned":
        for location_id in normalized_location_ids:
            db_session.add(
                DeliveryUserLocationAccess(
                    line_user_id=line_user_id,
                    location_id=location_id,
                    created_at=datetime.utcnow(),
                )
            )

    db_session.commit()
    return {
        "lineUserId": user.line_user_id,
        "displayName": user.display_name,
        "accessMode": user.access_mode,
        "allowedLocationIds": normalized_location_ids if access_mode == "assigned" else [],
    }


def get_report_by_submission_id(db_session, client_submission_id: str) -> Optional[VisitReport]:
    """Return an existing report for idempotent form submits."""
    return db_session.execute(
        select(VisitReport).where(VisitReport.client_submission_id == client_submission_id)
    ).scalar_one_or_none()


def create_visit_report(db_session, **kwargs) -> VisitReport:
    """Insert a new visit report row."""
    report = VisitReport(**kwargs)
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


def list_reports_page(
    db_session,
    *,
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    location_ids: Optional[List[str]],
    customer_id: Optional[str],
    user_id: Optional[str],
    before_received_at: Optional[datetime] = None,
    before_id: Optional[str] = None,
    limit: int = 60,
) -> Dict:
    """Return a paginated slice of admin gallery rows."""
    stmt = (
        select(
            VisitReport,
            DeliveryCustomer.name.label("customer_name"),
            DeliveryLocation.name.label("location_name"),
            DeliveryUser.display_name.label("user_name"),
        )
        .join(DeliveryCustomer, VisitReport.customer_id == DeliveryCustomer.customer_id)
        .join(DeliveryLocation, VisitReport.location_id == DeliveryLocation.id)
        .join(DeliveryUser, VisitReport.line_user_id == DeliveryUser.line_user_id)
        .order_by(VisitReport.received_at_server.desc(), VisitReport.id.desc())
    )
    if date_from:
        stmt = stmt.where(VisitReport.received_at_server >= date_from)
    if date_to:
        stmt = stmt.where(VisitReport.received_at_server <= date_to)
    if location_ids:
        stmt = stmt.where(VisitReport.location_id.in_(location_ids))
    if customer_id:
        stmt = stmt.where(VisitReport.customer_id == customer_id)
    if user_id:
        stmt = stmt.where(VisitReport.line_user_id == user_id)
    if before_received_at:
        if before_id:
            stmt = stmt.where(
                or_(
                    VisitReport.received_at_server < before_received_at,
                    and_(
                        VisitReport.received_at_server == before_received_at,
                        VisitReport.id < before_id,
                    ),
                )
            )
        else:
            stmt = stmt.where(VisitReport.received_at_server < before_received_at)

    rows = db_session.execute(stmt.limit(limit + 1)).all()
    has_more = len(rows) > limit
    visible_rows = rows[:limit]
    reports = [
        {
            "id": report.id,
            "clientSubmissionId": report.client_submission_id,
            "lineUserId": report.line_user_id,
            "userName": user_name,
            "customerId": report.customer_id,
            "customerName": customer_name,
            "locationId": report.location_id,
            "locationName": location_name,
            "photoUrl": report.photo_url,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "accuracyM": report.accuracy_m,
            "capturedAtClient": report.captured_at_client.isoformat() if report.captured_at_client else None,
            "receivedAtServer": report.received_at_server.isoformat() if report.received_at_server else None,
        }
        for report, customer_name, location_name, user_name in visible_rows
    ]
    next_cursor = None
    if has_more and visible_rows:
        last_report = visible_rows[-1][0]
        next_cursor = {
            "beforeReceivedAt": last_report.received_at_server.isoformat() if last_report.received_at_server else None,
            "beforeId": last_report.id,
        }
    return {
        "reports": reports,
        "hasMore": has_more,
        "nextCursor": next_cursor,
    }


def count_reports(db_session) -> int:
    """Return report count for sanity checks."""
    return int(db_session.execute(select(func.count()).select_from(VisitReport)).scalar_one())
