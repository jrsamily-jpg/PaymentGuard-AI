"""Transactional case changes with optimistic concurrency and immutable application audit."""

from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from app.database.models import Case, AuditEvent, Transaction
from app.models.schemas import CaseCreate, CaseUpdate


def serialize_case(c: Case) -> dict[str, Any]:
    return {
        k: getattr(c, k)
        for k in [
            "id",
            "transaction_id",
            "assignee",
            "status",
            "decision",
            "reason_code",
            "version",
        ]
    }


def create_case(session: Session, data: CaseCreate, actor: str) -> dict[str, Any]:
    if session.get(Transaction, data.transaction_id) is None:
        raise LookupError("Transaction not found")
    case = Case(transaction_id=data.transaction_id, assignee=data.assignee)
    try:
        session.add(case)
        session.flush()
        session.add(
            AuditEvent(
                case_id=case.id,
                actor=actor,
                action="created",
                details=data.model_dump(),
            )
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ValueError("A case already exists for this transaction")
    return serialize_case(case)


def update_case(
    session: Session, case_id: int, data: CaseUpdate, actor: str
) -> dict[str, Any]:
    case = session.get(Case, case_id)
    if case is None:
        raise LookupError("Case not found")
    changes = data.model_dump(exclude_none=True, exclude={"version", "note"})
    if data.status == "closed" and not (data.decision or case.decision):
        raise ValueError("Closing a case requires a decision")
    if case.version != data.version:
        raise ValueError("Case changed; refresh before saving")
    result = session.execute(
        update(Case)
        .where(Case.id == case_id, Case.version == data.version)
        .values(**changes, version=data.version + 1)
    )
    if result.rowcount != 1:
        session.rollback()
        raise ValueError("Concurrent update; refresh before saving")
    session.add(
        AuditEvent(
            case_id=case_id,
            actor=actor,
            action="updated",
            details=data.model_dump(exclude_none=True),
        )
    )
    session.commit()
    session.refresh(case)
    return serialize_case(case)


def list_cases(session: Session) -> list[dict[str, Any]]:
    return [
        serialize_case(c)
        for c in session.scalars(select(Case).order_by(Case.id.desc()))
    ]


def audit_history(session: Session, case_id: int) -> list[dict[str, Any]]:
    return [
        {
            "id": a.id,
            "actor": a.actor,
            "action": a.action,
            "details": a.details,
            "timestamp": a.created_at.isoformat(),
        }
        for a in session.scalars(
            select(AuditEvent)
            .where(AuditEvent.case_id == case_id)
            .order_by(AuditEvent.id)
        )
    ]


def review_backlog(session: Session) -> int:
    """Policy-review payments without a closed investigation, including unassigned work."""
    from sqlalchemy import func

    closed = select(Case.transaction_id).where(Case.status == "closed")
    return session.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.status == "review", Transaction.transaction_id.not_in(closed)
        )
    )
