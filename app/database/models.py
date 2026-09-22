"""Searchable transaction facts, normalized rule hits, cases and append-only application audit."""

from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    JSON,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base


def utcnow():
    return datetime.now(timezone.utc)


class Transaction(Base):
    __tablename__ = "transactions"
    transaction_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(20), index=True)
    timestamp: Mapped[str] = mapped_column(String(30), index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    payment_rail: Mapped[str] = mapped_column(String(30), index=True)
    direction: Mapped[str] = mapped_column(String(15))
    country: Mapped[str] = mapped_column(String(3), index=True)
    device_id: Mapped[str] = mapped_column(String(25), index=True)
    ip_address: Mapped[str] = mapped_column(String(40))
    bank_account_id: Mapped[str] = mapped_column(String(30), index=True)
    recipient_id: Mapped[str] = mapped_column(String(30), index=True)
    account_age: Mapped[int] = mapped_column(Integer)
    tx_count_1h: Mapped[int] = mapped_column(Integer)
    failed_logins: Mapped[int] = mapped_column(Integer)
    distance_km: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), index=True)
    is_fraud: Mapped[bool] = mapped_column(Boolean)
    fraud_category: Mapped[str] = mapped_column(String(60))
    risk_score: Mapped[float] = mapped_column(Float, index=True)
    risk_level: Mapped[str] = mapped_column(String(15), index=True)
    payload: Mapped[dict] = mapped_column(JSON)


class RuleHit(Base):
    __tablename__ = "rule_hits"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.transaction_id"), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(8), index=True)


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (UniqueConstraint("transaction_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("transactions.transaction_id")
    )
    assignee: Mapped[str] = mapped_column(String(80), default="Unassigned")
    status: Mapped[str] = mapped_column(String(20), default="open")
    decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(40))
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
