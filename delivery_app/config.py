"""Runtime configuration for the delivery companion app."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class DeliverySettings:
    delivery_database_url: str
    line_liff_id: str
    line_channel_id: str
    line_channel_secret: str
    loyverse_token: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_region: str
    app_base_url: str
    admin_password: str
    sync_secret: str
    source_sqlite_path: str
    session_cookie_name: str = "delivery_session"
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    photo_route_prefix: str = "/api/photos"
    max_upload_bytes: int = 10 * 1024 * 1024
    allow_guest_mode: bool = True
    enforce_location_access: bool = False
    bootstrap_seed_metadata: bool = True


def _parse_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> DeliverySettings:
    """Load settings from environment variables."""
    return DeliverySettings(
        delivery_database_url=os.getenv("DELIVERY_DATABASE_URL", "sqlite:///delivery_app.db"),
        line_liff_id=os.getenv("LINE_LIFF_ID", ""),
        line_channel_id=os.getenv("LINE_CHANNEL_ID", ""),
        line_channel_secret=os.getenv("LINE_CHANNEL_SECRET", "dev-line-secret"),
        loyverse_token=os.getenv("LOYVERSE_TOKEN", "").strip(),
        s3_endpoint=os.getenv("S3_ENDPOINT", ""),
        s3_bucket=os.getenv("S3_BUCKET", ""),
        s3_access_key_id=os.getenv("S3_ACCESS_KEY_ID", ""),
        s3_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", ""),
        s3_region=os.getenv("S3_REGION", "auto"),
        app_base_url=os.getenv("APP_BASE_URL", "").rstrip("/"),
        admin_password=os.getenv("ADMIN_PASSWORD", "change-me"),
        sync_secret=os.getenv("DELIVERY_SYNC_SECRET", "").strip(),
        source_sqlite_path=os.getenv("SOURCE_SQLITE_PATH", os.getenv("DATABASE_PATH", "loyverse_data.db")),
        allow_guest_mode=_parse_bool(os.getenv("DELIVERY_ALLOW_GUEST_MODE"), True),
        enforce_location_access=_parse_bool(os.getenv("DELIVERY_ENFORCE_LOCATION_ACCESS"), False),
        bootstrap_seed_metadata=_parse_bool(os.getenv("DELIVERY_BOOTSTRAP_SEED_METADATA"), True),
    )
