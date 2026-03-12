"""Database primitives for the delivery app."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, inspect, text
from sqlalchemy.orm import declarative_base, mapped_column, relationship, sessionmaker


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.utcnow()


def create_db_engine(database_url: str):
    """Create an engine that works for Postgres or SQLite."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, pool_pre_ping=True, connect_args=connect_args)


def create_session_factory(engine):
    """Return a configured SQLAlchemy sessionmaker."""
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db(engine) -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    if "delivery_users" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("delivery_users")}
        if "access_mode" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE delivery_users ADD COLUMN access_mode VARCHAR(32) NOT NULL DEFAULT 'all'")
                )


class DeliveryUser(Base):
    __tablename__ = "delivery_users"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    line_user_id = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name = mapped_column(String(255), nullable=False)
    picture_url = mapped_column(Text, nullable=True)
    status = mapped_column(String(32), nullable=False, default="active")
    access_mode = mapped_column(String(32), nullable=False, default="all")
    created_at = mapped_column(DateTime, nullable=False, default=utcnow)
    last_login_at = mapped_column(DateTime, nullable=False, default=utcnow)

    reports = relationship("VisitReport", back_populates="user")
    location_access = relationship("DeliveryUserLocationAccess", back_populates="user", cascade="all, delete-orphan")


class DeliveryLocation(Base):
    __tablename__ = "delivery_locations"

    id = mapped_column(String(64), primary_key=True)
    name = mapped_column(String(255), nullable=False, unique=True)
    source_category_id = mapped_column(String(64), nullable=True, unique=True)
    customer_count = mapped_column(Integer, nullable=False, default=0)
    last_synced_at = mapped_column(DateTime, nullable=False, default=utcnow)

    customers = relationship("DeliveryCustomer", back_populates="location")
    reports = relationship("VisitReport", back_populates="location")
    user_access = relationship("DeliveryUserLocationAccess", back_populates="location", cascade="all, delete-orphan")


class DeliveryCustomer(Base):
    __tablename__ = "delivery_customers"

    customer_id = mapped_column(String(64), primary_key=True)
    name = mapped_column(String(255), nullable=False)
    customer_code = mapped_column(String(255), nullable=True)
    phone = mapped_column(String(64), nullable=True)
    primary_location_id = mapped_column(String(64), ForeignKey("delivery_locations.id"), nullable=False, index=True)
    last_synced_at = mapped_column(DateTime, nullable=False, default=utcnow)

    location = relationship("DeliveryLocation", back_populates="customers")
    reports = relationship("VisitReport", back_populates="customer")


class DeliveryUserLocationAccess(Base):
    __tablename__ = "delivery_user_location_access"
    __table_args__ = (
        UniqueConstraint("line_user_id", "location_id", name="uq_delivery_user_location_access"),
    )

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    line_user_id = mapped_column(String(255), ForeignKey("delivery_users.line_user_id"), nullable=False, index=True)
    location_id = mapped_column(String(64), ForeignKey("delivery_locations.id"), nullable=False, index=True)
    created_at = mapped_column(DateTime, nullable=False, default=utcnow)

    user = relationship("DeliveryUser", back_populates="location_access")
    location = relationship("DeliveryLocation", back_populates="user_access")


class VisitReport(Base):
    __tablename__ = "visit_reports"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    client_submission_id = mapped_column(String(255), unique=True, nullable=False, index=True)
    line_user_id = mapped_column(String(255), ForeignKey("delivery_users.line_user_id"), nullable=False, index=True)
    customer_id = mapped_column(String(64), ForeignKey("delivery_customers.customer_id"), nullable=False, index=True)
    location_id = mapped_column(String(64), ForeignKey("delivery_locations.id"), nullable=False, index=True)
    photo_object_key = mapped_column(Text, nullable=False)
    photo_url = mapped_column(Text, nullable=False)
    latitude = mapped_column(Float, nullable=False)
    longitude = mapped_column(Float, nullable=False)
    accuracy_m = mapped_column(Float, nullable=True)
    captured_at_client = mapped_column(DateTime, nullable=False)
    received_at_server = mapped_column(DateTime, nullable=False, default=utcnow)

    user = relationship("DeliveryUser", back_populates="reports")
    customer = relationship("DeliveryCustomer", back_populates="reports")
    location = relationship("DeliveryLocation", back_populates="reports")
