"""FastAPI entrypoint for the LINE delivery photo app."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import secrets
from typing import List, Optional
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBasic, HTTPBasicCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from delivery_app.auth import LineVerifier, SessionManager, hash_admin_password
from delivery_app.config import DeliverySettings, load_settings
from delivery_app.db import create_db_engine, create_session_factory, init_db
from delivery_app.loyverse_sync import sync_delivery_customers_from_loyverse
from delivery_app.metadata import bootstrap_seed_metadata_if_empty
from delivery_app.photo_metadata import build_photo_variants, build_variant_object_key
from delivery_app.repository import (
    create_visit_report,
    GUEST_USER_ID,
    get_customer,
    get_delivery_user,
    get_or_create_guest_user,
    get_report_by_submission_id,
    get_allowed_location_ids,
    list_customers,
    list_delivery_users_with_access,
    list_locations,
    list_reports_page,
    set_user_location_access,
    upsert_delivery_user,
    user_can_access_location,
)
from delivery_app.storage import NullStorage, S3Storage


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
basic_auth = HTTPBasic(auto_error=False)
bearer_auth = HTTPBearer(auto_error=False)


class SessionCreateRequest(BaseModel):
    id_token: str


class UserLocationAccessUpdateRequest(BaseModel):
    access_mode: str
    location_ids: List[str] = []


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO timestamps from the mobile client."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="captured_at_client must be an ISO-8601 timestamp") from exc


def build_photo_key(customer_id: str, filename: str) -> str:
    """Generate a stable object key layout by day and customer."""
    suffix = Path(filename or "photo.jpg").suffix or ".jpg"
    now = datetime.utcnow()
    return (
        f"reports/{now.year:04d}/{now.month:02d}/{now.day:02d}/"
        f"{customer_id}/{uuid4().hex}{suffix.lower()}"
    )


def build_photo_url(settings: DeliverySettings, object_key: str, *, variant: str = "original") -> str:
    """Build the admin-view image route for a stored object."""
    base = settings.app_base_url or ""
    suffix = "" if variant == "original" else f"?variant={variant}"
    return f"{base}{settings.photo_route_prefix}/{object_key}{suffix}"


def build_default_storage(settings: DeliverySettings):
    """Construct the configured storage backend, or a disabled fallback for local imports."""
    s3_values = [
        settings.s3_bucket,
        settings.s3_endpoint,
        settings.s3_access_key_id,
        settings.s3_secret_access_key,
    ]
    has_real_s3_config = all(value and not value.startswith("REPLACE_WITH_") for value in s3_values)
    if has_real_s3_config:
        return S3Storage(
            endpoint=settings.s3_endpoint,
            bucket=settings.s3_bucket,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            region=settings.s3_region,
        )
    return NullStorage()


def describe_database_backend(database_url: str) -> dict:
    """Return a safe summary of the active report metadata database."""
    if database_url.startswith("sqlite"):
        return {
            "backend": "sqlite",
            "label": "SQLite fallback",
            "persistent": False,
            "detail": "Report rows are stored inside the web service filesystem.",
            "warning": "Deploys can wipe old reports unless DELIVERY_DATABASE_URL points to Render Postgres.",
        }
    return {
        "backend": "postgres",
        "label": "Postgres",
        "persistent": True,
        "detail": "Report rows are stored in the shared delivery database.",
        "warning": "",
    }


def describe_photo_storage(storage) -> dict:
    """Return a safe summary of the active photo storage backend."""
    if isinstance(storage, S3Storage):
        return {
            "backend": "s3",
            "label": "R2 / S3",
            "detail": "Photos are stored in object storage.",
        }
    if isinstance(storage, NullStorage):
        return {
            "backend": "disabled",
            "label": "Disabled",
            "detail": "Photo storage is not configured.",
        }
    return {
        "backend": "custom",
        "label": "Custom",
        "detail": "Photos are stored through a custom backend.",
    }


def create_app(
    settings: Optional[DeliverySettings] = None,
    *,
    session_factory=None,
    storage=None,
    line_verifier=None,
) -> FastAPI:
    """Application factory used by production and tests."""
    settings = settings or load_settings()
    engine = create_db_engine(settings.delivery_database_url)
    init_db(engine)
    session_factory = session_factory or create_session_factory(engine)
    if settings.bootstrap_seed_metadata:
        bootstrap_seed_metadata_if_empty(session_factory)
    storage = storage or build_default_storage(settings)
    line_verifier = line_verifier or LineVerifier(settings.line_channel_id)
    session_manager = SessionManager(settings.line_channel_secret)
    system_status = {
        "database": describe_database_backend(settings.delivery_database_url),
        "photoStorage": describe_photo_storage(storage),
    }
    if not system_status["database"]["persistent"]:
        print(
            "WARNING: Delivery app is using SQLite fallback. "
            "Set DELIVERY_DATABASE_URL to Render Postgres for persistent reports."
        )

    app = FastAPI(title="Snow AI Delivery Photo App")
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.storage = storage
    app.state.line_verifier = line_verifier
    app.state.session_manager = session_manager
    app.state.system_status = system_status
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    def get_db():
        db = app.state.session_factory()
        try:
            yield db
        finally:
            db.close()

    def serialize_user(user, db: Session):
        allowed_location_ids = get_allowed_location_ids(
            db,
            user,
            enforce_access=settings.enforce_location_access,
        )
        return {
            "lineUserId": user.line_user_id,
            "displayName": user.display_name,
            "pictureUrl": user.picture_url,
            "accessMode": user.access_mode if settings.enforce_location_access else "all",
            "allowedLocationIds": allowed_location_ids if allowed_location_ids is not None else [],
        }

    def require_user(request: Request, db: Session = Depends(get_db)):
        token = request.cookies.get(settings.session_cookie_name)
        if not token:
            if settings.allow_guest_mode:
                return get_or_create_guest_user(db)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        try:
            line_user_id = session_manager.loads(token, max_age=settings.session_ttl_seconds)
        except ValueError as exc:
            if settings.allow_guest_mode:
                return get_or_create_guest_user(db)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        user = get_delivery_user(db, line_user_id)
        if user is None or user.status != "active":
            if settings.allow_guest_mode:
                return get_or_create_guest_user(db)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown delivery user")
        return user

    def require_admin(credentials: Optional[HTTPBasicCredentials] = Depends(basic_auth)):
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin authentication required",
                headers={"WWW-Authenticate": "Basic"},
            )
        if (
            credentials.username != "admin"
            or hash_admin_password(credentials.password) != hash_admin_password(settings.admin_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return True

    def require_admin_api(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_auth)):
        expected_token = settings.admin_internal_api_token.strip()
        if not expected_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Admin API token is not configured",
            )
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin API authentication required",
            )
        if not secrets.compare_digest(credentials.credentials.strip(), expected_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin API token",
            )
        return True

    def require_sync_secret(request: Request):
        expected_secret = settings.sync_secret.strip()
        if not expected_secret:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Sync secret is not configured")
        provided_secret = request.headers.get("X-Delivery-Sync-Secret", "").strip()
        if provided_secret != expected_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sync secret")
        return True

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "liff_id": settings.line_liff_id,
            },
        )

    @app.get("/admin", response_class=HTMLResponse)
    def admin_page(request: Request, _: bool = Depends(require_admin)):
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "system_status": app.state.system_status,
            },
        )

    @app.get("/admin/system")
    def admin_system(_: bool = Depends(require_admin)):
        return app.state.system_status

    @app.get("/admin-api/system")
    def admin_api_system(_: bool = Depends(require_admin_api)):
        return app.state.system_status

    @app.post("/internal/sync/customers")
    def internal_sync_customers(
        _: bool = Depends(require_sync_secret),
        db: Session = Depends(get_db),
    ):
        if not settings.loyverse_token:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LOYVERSE_TOKEN is not configured")
        result = sync_delivery_customers_from_loyverse(db, settings.loyverse_token)
        return {"ok": True, "result": result}

    @app.get("/api/session")
    def get_session(request: Request, db: Session = Depends(get_db)):
        token = request.cookies.get(settings.session_cookie_name)
        if not token:
            if settings.allow_guest_mode:
                user = get_or_create_guest_user(db)
                return {
                    "authenticated": True,
                    "guestMode": True,
                    "liffId": settings.line_liff_id,
                    "user": serialize_user(user, db),
                }
            return {"authenticated": False, "liffId": settings.line_liff_id}
        try:
            line_user_id = session_manager.loads(token, max_age=settings.session_ttl_seconds)
        except ValueError:
            if settings.allow_guest_mode:
                user = get_or_create_guest_user(db)
                return {
                    "authenticated": True,
                    "guestMode": True,
                    "liffId": settings.line_liff_id,
                    "user": serialize_user(user, db),
                }
            return {"authenticated": False, "liffId": settings.line_liff_id}
        user = get_delivery_user(db, line_user_id)
        if user is None:
            if settings.allow_guest_mode:
                guest = get_or_create_guest_user(db)
                return {
                    "authenticated": True,
                    "guestMode": True,
                    "liffId": settings.line_liff_id,
                    "user": serialize_user(guest, db),
                }
            return {"authenticated": False, "liffId": settings.line_liff_id}
        return {
            "authenticated": True,
            "guestMode": user.line_user_id == GUEST_USER_ID,
            "liffId": settings.line_liff_id,
            "user": serialize_user(user, db),
        }

    @app.post("/api/session")
    def create_session(payload: SessionCreateRequest, response: Response, db: Session = Depends(get_db)):
        try:
            profile = app.state.line_verifier.verify_id_token(payload.id_token)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        user = upsert_delivery_user(db, profile)
        cookie = session_manager.dumps(user.line_user_id)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=cookie,
            httponly=True,
            secure=bool(settings.app_base_url.startswith("https://")),
            samesite="lax",
            max_age=settings.session_ttl_seconds,
        )
        return {
            "authenticated": True,
            "user": serialize_user(user, db),
        }

    @app.post("/api/logout")
    def logout(response: Response):
        response.delete_cookie(settings.session_cookie_name)
        return {"ok": True}

    @app.get("/api/locations")
    def api_locations(user=Depends(require_user), db: Session = Depends(get_db)):
        return {"locations": list_locations(db, user=user, enforce_access=settings.enforce_location_access)}

    @app.get("/api/customers")
    def api_customers(
        location_id: Optional[str] = None,
        q: Optional[str] = None,
        user=Depends(require_user),
        db: Session = Depends(get_db),
    ):
        if location_id and not user_can_access_location(
            db,
            user,
            location_id,
            enforce_access=settings.enforce_location_access,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Location is not authorized for this user")
        return {
            "customers": list_customers(
                db,
                location_id=location_id,
                query=q,
                user=user,
                enforce_access=settings.enforce_location_access,
            )
        }

    @app.post("/api/reports")
    async def api_reports(
        request: Request,
        client_submission_id: str = Form(...),
        customer_id: str = Form(...),
        latitude: float = Form(...),
        longitude: float = Form(...),
        captured_at_client: str = Form(...),
        accuracy_m: Optional[float] = Form(None),
        photo: UploadFile = File(...),
        user=Depends(require_user),
        db: Session = Depends(get_db),
    ):
        existing = get_report_by_submission_id(db, client_submission_id)
        if existing is not None:
            return {
                "duplicate": True,
                "reportId": existing.id,
                "photoUrl": existing.photo_url,
            }

        customer = get_customer(db, customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Unknown customer")
        if not user_can_access_location(
            db,
            user,
            customer.primary_location_id,
            enforce_access=settings.enforce_location_access,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Customer location is not authorized for this user")
        if not photo.filename:
            raise HTTPException(status_code=400, detail="A photo is required")
        if not photo.content_type or not photo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Photo must be an image")
        payload = await photo.read()
        if not payload:
            raise HTTPException(status_code=400, detail="Photo file is empty")
        if len(payload) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Photo exceeds size limit")
        captured_at = parse_iso_datetime(captured_at_client)
        photo_variants = build_photo_variants(
            payload=payload,
            filename=photo.filename,
            content_type=photo.content_type,
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
            captured_at_client=captured_at,
        )

        object_key = build_photo_key(customer_id, photo.filename)
        try:
            for variant_name, variant in photo_variants.items():
                app.state.storage.upload_bytes(
                    object_key=build_variant_object_key(object_key, variant_name),
                    payload=variant.payload,
                    content_type=variant.content_type,
                )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        photo_url = build_photo_url(settings, object_key)
        report = create_visit_report(
            db,
            client_submission_id=client_submission_id,
            line_user_id=user.line_user_id,
            customer_id=customer.customer_id,
            location_id=customer.primary_location_id,
            photo_object_key=object_key,
            photo_url=photo_url,
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy_m,
            captured_at_client=captured_at,
            received_at_server=datetime.utcnow(),
        )
        return {
            "duplicate": False,
            "reportId": report.id,
            "photoUrl": report.photo_url,
            "locationId": report.location_id,
        }

    @app.get("/api/photos/{object_key:path}")
    def api_photo(
        object_key: str,
        variant: str = Query("original"),
        _: bool = Depends(require_admin),
    ):
        if variant not in {"original", "display", "thumb"}:
            raise HTTPException(status_code=400, detail="Unknown photo variant")

        keys_to_try = [build_variant_object_key(object_key, variant)]
        if variant != "original":
            keys_to_try.append(object_key)

        for candidate_key in keys_to_try:
            try:
                stored = app.state.storage.read_bytes(candidate_key)
                return StreamingResponse(stored.content, media_type=stored.content_type)
            except Exception:
                continue

        raise HTTPException(status_code=404, detail="Photo not found")

    @app.get("/admin-api/photos/{object_key:path}")
    def admin_api_photo(
        object_key: str,
        variant: str = Query("original"),
        _: bool = Depends(require_admin_api),
    ):
        if variant not in {"original", "display", "thumb"}:
            raise HTTPException(status_code=400, detail="Unknown photo variant")

        keys_to_try = [build_variant_object_key(object_key, variant)]
        if variant != "original":
            keys_to_try.append(object_key)

        for candidate_key in keys_to_try:
            try:
                stored = app.state.storage.read_bytes(candidate_key)
                return StreamingResponse(stored.content, media_type=stored.content_type)
            except Exception:
                continue

        raise HTTPException(status_code=404, detail="Photo not found")

    @app.get("/admin/reports")
    def admin_reports(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        location_ids: Optional[List[str]] = Query(None),
        customer_id: Optional[str] = None,
        user_id: Optional[str] = None,
        before_received_at: Optional[str] = None,
        before_id: Optional[str] = None,
        limit: int = Query(60, ge=1, le=120),
        _: bool = Depends(require_admin),
        db: Session = Depends(get_db),
        ):
        parsed_from = parse_iso_datetime(f"{date_from}T00:00:00") if date_from else None
        parsed_to = parse_iso_datetime(f"{date_to}T23:59:59") if date_to else None
        parsed_before = parse_iso_datetime(before_received_at) if before_received_at else None
        return list_reports_page(
            db,
            date_from=parsed_from,
            date_to=parsed_to,
            location_ids=location_ids,
            customer_id=customer_id,
            user_id=user_id,
            before_received_at=parsed_before,
            before_id=before_id,
            limit=limit,
        )

    @app.get("/admin-api/reports")
    def admin_api_reports(
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        location_ids: Optional[List[str]] = Query(None),
        customer_id: Optional[str] = None,
        user_id: Optional[str] = None,
        before_received_at: Optional[str] = None,
        before_id: Optional[str] = None,
        limit: int = Query(60, ge=1, le=120),
        _: bool = Depends(require_admin_api),
        db: Session = Depends(get_db),
    ):
        parsed_from = parse_iso_datetime(f"{date_from}T00:00:00") if date_from else None
        parsed_to = parse_iso_datetime(f"{date_to}T23:59:59") if date_to else None
        parsed_before = parse_iso_datetime(before_received_at) if before_received_at else None
        return list_reports_page(
            db,
            date_from=parsed_from,
            date_to=parsed_to,
            location_ids=location_ids,
            customer_id=customer_id,
            user_id=user_id,
            before_received_at=parsed_before,
            before_id=before_id,
            limit=limit,
        )

    @app.get("/admin/locations")
    def admin_locations(_: bool = Depends(require_admin), db: Session = Depends(get_db)):
        return {"locations": list_locations(db)}

    @app.get("/admin-api/locations")
    def admin_api_locations(_: bool = Depends(require_admin_api), db: Session = Depends(get_db)):
        return {"locations": list_locations(db)}

    @app.get("/admin/access/users")
    def admin_access_users(_: bool = Depends(require_admin), db: Session = Depends(get_db)):
        return {"users": list_delivery_users_with_access(db)}

    @app.get("/admin-api/access/users")
    def admin_api_access_users(_: bool = Depends(require_admin_api), db: Session = Depends(get_db)):
        return {"users": list_delivery_users_with_access(db)}

    @app.put("/admin/access/users/{line_user_id}/locations")
    def admin_set_user_access(
        line_user_id: str,
        payload: UserLocationAccessUpdateRequest,
        _: bool = Depends(require_admin),
        db: Session = Depends(get_db),
    ):
        try:
            updated = set_user_location_access(
                db,
                line_user_id=line_user_id,
                access_mode=payload.access_mode,
                location_ids=payload.location_ids,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return updated

    @app.put("/admin-api/access/users/{line_user_id}/locations")
    def admin_api_set_user_access(
        line_user_id: str,
        payload: UserLocationAccessUpdateRequest,
        _: bool = Depends(require_admin_api),
        db: Session = Depends(get_db),
    ):
        try:
            updated = set_user_location_access(
                db,
                line_user_id=line_user_id,
                access_mode=payload.access_mode,
                location_ids=payload.location_ids,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return updated

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "delivery_app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
