"""Validated public inputs. Unknown fields are rejected."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Decision = Literal["approve", "decline", "escalate", "request verification"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SimulationInput(StrictModel):
    thresholds: dict[str, float] = Field(default_factory=dict, max_length=12)
    decision_threshold: int = Field(default=60, ge=1, le=100)
    friction_cost: float = Field(default=8, ge=0, le=1000)
    confirmed: bool = False


class CaseCreate(StrictModel):
    transaction_id: str = Field(pattern=r"^TX-\d{7}$")
    assignee: str = Field(default="Unassigned", min_length=1, max_length=80)


class CaseUpdate(StrictModel):
    assignee: str | None = Field(default=None, min_length=1, max_length=80)
    note: str | None = Field(default=None, min_length=1, max_length=2000)
    decision: Decision | None = None
    reason_code: (
        Literal[
            "verified_customer",
            "suspicious_behavior",
            "ownership_mismatch",
            "insufficient_evidence",
            "policy_exception",
        ]
        | None
    ) = None
    status: Literal["open", "in review", "escalated", "closed"] | None = None
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def meaningful(self):
        if not any(
            [self.assignee, self.note, self.decision, self.reason_code, self.status]
        ):
            raise ValueError("At least one change is required")
        if self.decision and not self.reason_code:
            raise ValueError("A decision requires a reason code")
        return self
