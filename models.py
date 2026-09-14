"""
SQLAlchemy models for IGRIS Business Pulse.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    response_code = Column(String(20), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    business_type = Column(String(100), nullable=True)
    customer_channels = Column(JSONB, nullable=False, default=list)
    biggest_challenge = Column(String(200), nullable=True)
    time_consuming_task = Column(String(200), nullable=True)
    order_management = Column(String(200), nullable=True)
    payment_tracking = Column(String(200), nullable=True)
    technology_used = Column(JSONB, nullable=False, default=list)
    digital_barriers = Column(JSONB, nullable=False, default=list)
    desired_improvement = Column(Text, nullable=True)
    contact_permission = Column(Boolean, nullable=False, default=False)
    contact = Column(String(255), nullable=True)

    __table_args__ = (
        Index("ix_responses_business_type", "business_type"),
        Index("ix_responses_biggest_challenge", "biggest_challenge"),
        Index("ix_responses_contact_permission", "contact_permission"),
        Index("ix_responses_created_at", "created_at"),
    )


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
