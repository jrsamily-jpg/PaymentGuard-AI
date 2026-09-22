"""Owner-scoped operational records. Amounts use integer minor units, never floats."""

import time
import uuid

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.workspace.database import Base


def new_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "workspace_users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[int] = mapped_column(
        BigInteger, default=lambda: int(time.time())
    )


class AccessSession(Base):
    __tablename__ = "workspace_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("workspace_users.id"), index=True)
    expires_at: Mapped[int] = mapped_column(BigInteger)


class LoginThrottle(Base):
    __tablename__ = "workspace_login_limits"
    subject: Mapped[str] = mapped_column(String(64), primary_key=True)
    failures: Mapped[int] = mapped_column(Integer, default=0)
    window_start: Mapped[int] = mapped_column(BigInteger)


class PaymentEvent(Base):
    __tablename__ = "workspace_payments"
    __table_args__ = (
        UniqueConstraint("owner_id", "external_id"),
        Index("ix_workspace_payment_time", "owner_id", "occurred_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("workspace_users.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(80))
    customer_ref: Mapped[str] = mapped_column(String(80))
    occurred_at: Mapped[str] = mapped_column(String(32))
    amount_minor: Mapped[int] = mapped_column(BigInteger)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    rail: Mapped[str] = mapped_column(String(30))
    direction: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(20))
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    confirmed_fraud: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSON)
    signals: Mapped[list] = mapped_column(JSON)
    evaluated_rules: Mapped[int] = mapped_column(Integer)


class Investigation(Base):
    __tablename__ = "workspace_cases"
    __table_args__ = (UniqueConstraint("owner_id", "payment_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(ForeignKey("workspace_users.id"), index=True)
    payment_id: Mapped[str] = mapped_column(ForeignKey("workspace_payments.id"))
    assignee: Mapped[str] = mapped_column(String(80), default="Unassigned")
    status: Mapped[str] = mapped_column(String(20), default="open")
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(80), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class Audit(Base):
    __tablename__ = "workspace_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("workspace_users.id"), index=True)
    entity_id: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[int] = mapped_column(
        BigInteger, default=lambda: int(time.time())
    )
