"""Bounded input contracts; unknown fields and unsupported currencies fail closed."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RAILS = ["ACH", "Debit card", "Credit card", "Wire", "Real-time payment", "Crypto"]


class Strict(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, allow_inf_nan=False
    )


class Credentials(Strict):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=12, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize(cls, value):
        return value.lower()


class Evidence(Strict):
    account_age: int | None = Field(None, ge=0, le=36500)
    customer_avg_amount: float | None = Field(None, gt=0, le=1e9)
    tx_count_1h: int | None = Field(None, ge=0, le=1000000)
    minutes_since_deposit: float | None = Field(None, ge=0, le=1e8)
    failed_logins: int | None = Field(None, ge=0, le=100000)
    device_trusted: bool | None = None
    password_reset: bool | None = None
    customer_devices: int | None = Field(None, ge=1, le=100000)
    distance_km: float | None = Field(None, ge=0, le=50000)
    hours_since_last_location: float | None = Field(None, gt=0, le=1e7)
    shared_accounts: int | None = Field(None, ge=1, le=1000000)
    ownership_match: bool | None = None
    prior_chargebacks: int | None = Field(None, ge=0, le=100000)
    recipient_risk: Literal["low", "medium", "high"] | None = None
    recipient_age: int | None = Field(None, ge=0, le=36500)
    vpn_proxy: bool | None = None


class PaymentInput(Strict):
    external_id: str = Field(
        min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )
    customer_ref: str = Field(
        min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
    )
    occurred_at: datetime
    amount: Decimal = Field(
        gt=0, le=Decimal(1000000000), max_digits=12, decimal_places=2
    )
    currency: Literal["USD"] = "USD"
    rail: Literal[
        "ACH",
        "Debit card",
        "Credit card",
        "Wire",
        "Real-time payment",
        "Crypto",
        "Unspecified",
    ] = "Unspecified"
    direction: Literal["deposit", "withdrawal"]
    status: Literal["pending", "settled", "blocked", "returned"] = "pending"
    country: str | None = Field(None, pattern=r"^[A-Z]{2}$")
    confirmed_fraud: bool | None = None
    evidence: Evidence = Field(default_factory=Evidence)

    @field_validator("occurred_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Include a timezone offset in occurred_at")
        if value > datetime.now(UTC):
            raise ValueError("Payment time cannot be in the future")
        return value.astimezone(UTC)


class PaymentBatch(Strict):
    payments: list[PaymentInput] = Field(min_length=1, max_length=5000)


class CaseInput(Strict):
    payment_id: str = Field(min_length=1, max_length=36)


class CaseChange(Strict):
    version: int = Field(ge=1)
    assignee: str = Field(min_length=1, max_length=80)
    status: Literal["open", "in review", "escalated", "closed"]
    decision: (
        Literal["approve", "decline", "escalate", "request verification"] | None
    ) = None
    reason: (
        Literal[
            "verified customer",
            "suspicious behavior",
            "ownership mismatch",
            "insufficient evidence",
            "policy exception",
        ]
        | None
    ) = None
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def decision_reason(self):
        if self.decision and not self.reason:
            raise ValueError("A decision needs a reason")
        return self


class SimulationRequest(Strict):
    thresholds: dict[str, float] = Field(default_factory=dict, max_length=12)
    decision_threshold: int = Field(default=60, ge=1, le=100)
    confirmed: bool = False
