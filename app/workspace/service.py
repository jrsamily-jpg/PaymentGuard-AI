"""Owner-scoped application operations shared by UI and API."""

import csv
import io
import json
from decimal import Decimal
from html import escape

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.workspace.models import Audit, Investigation, PaymentEvent
from app.workspace.risk import assess
from app.workspace.schemas import (
    CaseChange,
    PaymentBatch,
    PaymentInput,
    SimulationRequest,
)

CSV_COLUMNS = [
    "external_id",
    "customer_ref",
    "occurred_at",
    "amount",
    "currency",
    "rail",
    "direction",
    "status",
    "country",
    "confirmed_fraud",
    "evidence",
]


def csv_template() -> str:
    return ",".join(column for column in CSV_COLUMNS if column != "rail") + "\n"


def parse_csv(content: bytes) -> list[PaymentInput]:
    if not content or len(content) > 2_000_000:
        raise ValueError("Upload a nonempty UTF-8 CSV smaller than 2 MB.")
    try:
        rows = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    except UnicodeError as error:
        raise ValueError("CSV must use UTF-8 encoding.") from error
    if not rows.fieldnames or len(rows.fieldnames) != len(set(rows.fieldnames)):
        raise ValueError("Missing or duplicate column names.")
    required = {
        "external_id",
        "customer_ref",
        "occurred_at",
        "amount",
        "direction",
    }
    if not required.issubset(rows.fieldnames) or set(rows.fieldnames) - set(
        CSV_COLUMNS
    ):
        raise ValueError("Column names do not match the template.")
    payments = []
    for index, row in enumerate(rows, start=2):
        if len(payments) >= 5000:
            raise ValueError("Import at most 5,000 payments at a time.")
        if None in row:
            raise ValueError(f"Row {index}: extra columns.")
        values = {key: value for key, value in row.items() if value not in [None, ""]}
        if "evidence" in values:
            try:
                values["evidence"] = json.loads(values["evidence"])
            except (ValueError, TypeError) as error:
                raise ValueError(
                    f"Row {index}: evidence must be a JSON object."
                ) from error
        try:
            payments.append(PaymentInput.model_validate(values))
        except ValueError as error:
            raise ValueError(f"Row {index}: {str(error)[:500]}") from error
    if not payments:
        raise ValueError(
            "The file contains no payments. The downloaded template is intentionally empty."
        )
    PaymentBatch(payments=payments)
    return payments


def serialize(event: PaymentEvent) -> dict:
    return {
        "id": event.id,
        "external_id": event.external_id,
        "customer_ref": event.customer_ref,
        "occurred_at": event.occurred_at,
        "amount": str(Decimal(event.amount_minor) / 100),
        "amount_minor": event.amount_minor,
        "currency": event.currency,
        "rail": event.rail,
        "direction": event.direction,
        "status": event.status,
        "country": event.country,
        "confirmed_fraud": event.confirmed_fraud,
        "score": event.score,
        "signals": event.signals,
        "evaluated_rules": event.evaluated_rules,
        "evidence": event.evidence,
    }


def event_input(event: dict) -> PaymentInput:
    fields = [
        "external_id",
        "customer_ref",
        "occurred_at",
        "amount",
        "currency",
        "rail",
        "direction",
        "status",
        "country",
        "confirmed_fraud",
        "evidence",
    ]
    return PaymentInput.model_validate({key: event[key] for key in fields})


def ingest(session, owner_id: str, payments: list[PaymentInput]) -> dict:
    PaymentBatch(payments=payments)
    refs = [item.external_id for item in payments]
    if len(refs) != len(set(refs)):
        raise ValueError("Duplicate payment references in this batch.")
    # Chunked predicates avoid SQLite parameter limits without loosening owner scoping.
    for start in range(0, len(refs), 400):
        found = session.scalar(
            select(PaymentEvent.id)
            .where(
                PaymentEvent.owner_id == owner_id,
                PaymentEvent.external_id.in_(refs[start : start + 400]),
            )
            .limit(1)
        )
        if found:
            raise ValueError(
                "A payment reference already exists in your workspace. Nothing was imported."
            )
    try:
        for item in payments:
            risk = assess(item)
            session.add(
                PaymentEvent(
                    owner_id=owner_id,
                    external_id=item.external_id,
                    customer_ref=item.customer_ref,
                    occurred_at=item.occurred_at.isoformat(),
                    amount_minor=int(item.amount * 100),
                    currency=item.currency,
                    rail=item.rail,
                    direction=item.direction,
                    status=item.status,
                    country=item.country,
                    confirmed_fraud=item.confirmed_fraud,
                    score=risk["score"],
                    signals=risk["signals"],
                    evaluated_rules=risk["evaluated_rules"],
                    evidence=item.evidence.model_dump(exclude_none=True),
                )
            )
        session.add(
            Audit(
                owner_id=owner_id,
                entity_id="payments",
                action="payments_imported",
                details={"count": len(payments)},
            )
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ValueError(
            "Import conflicted with an existing payment. Nothing was imported."
        ) from error
    return {"imported": len(payments)}


def events(session, owner_id: str) -> list[dict]:
    return [
        serialize(row)
        for row in session.scalars(
            select(PaymentEvent)
            .where(PaymentEvent.owner_id == owner_id)
            .order_by(PaymentEvent.occurred_at.desc(), PaymentEvent.id)
        )
    ]


def event_page(session, owner_id: str, limit: int, offset: int) -> dict:
    query = select(PaymentEvent).where(PaymentEvent.owner_id == owner_id)
    total = session.scalar(
        select(func.count(PaymentEvent.id)).where(PaymentEvent.owner_id == owner_id)
    )
    records = session.scalars(
        query.order_by(PaymentEvent.occurred_at.desc(), PaymentEvent.id)
        .offset(offset)
        .limit(limit)
    )
    return {"total": total, "items": [serialize(row) for row in records]}


def payment(session, owner_id: str, payment_id: str) -> dict:
    event = session.scalar(
        select(PaymentEvent).where(
            PaymentEvent.id == payment_id, PaymentEvent.owner_id == owner_id
        )
    )
    if event is None:
        raise LookupError("Payment not found.")
    return serialize(event)


def case_dict(row: Investigation) -> dict:
    return {
        key: getattr(row, key)
        for key in [
            "id",
            "payment_id",
            "assignee",
            "status",
            "decision",
            "reason",
            "version",
        ]
    }


def cases(session, owner_id: str) -> list[dict]:
    return [
        case_dict(case)
        for case in session.scalars(
            select(Investigation)
            .where(Investigation.owner_id == owner_id)
            .order_by(Investigation.id)
        )
    ]


def create_case(session, owner_id: str, payment_id: str) -> dict:
    payment(session, owner_id, payment_id)
    case = Investigation(owner_id=owner_id, payment_id=payment_id)
    try:
        session.add(case)
        session.flush()
        session.add(
            Audit(
                owner_id=owner_id,
                entity_id=case.id,
                action="case_created",
                details={"payment_id": payment_id},
            )
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise ValueError("This payment already has an investigation.") from error
    return case_dict(case)


def update_case(session, owner_id: str, case_id: str, change: CaseChange) -> dict:
    case = session.scalar(
        select(Investigation).where(
            Investigation.id == case_id, Investigation.owner_id == owner_id
        )
    )
    if case is None:
        raise LookupError("Investigation not found.")
    if change.status == "closed" and not (change.decision or case.decision):
        raise ValueError("Choose a decision before closing the investigation.")
    values = change.model_dump(exclude={"version", "note"}, exclude_none=True)
    result = session.execute(
        update(Investigation)
        .where(
            Investigation.owner_id == owner_id,
            Investigation.id == case_id,
            Investigation.version == change.version,
        )
        .values(**values, version=change.version + 1)
    )
    if result.rowcount != 1:
        session.rollback()
        raise ValueError("This investigation changed. Refresh before saving.")
    session.add(
        Audit(
            owner_id=owner_id,
            entity_id=case_id,
            action="case_updated",
            details=change.model_dump(exclude_none=True),
        )
    )
    session.commit()
    session.refresh(case)
    return case_dict(case)


def audit(session, owner_id: str, entity_id: str | None = None) -> list[dict]:
    query = select(Audit).where(Audit.owner_id == owner_id)
    if entity_id:
        query = query.where(Audit.entity_id == entity_id)
    return [
        {
            "id": row.id,
            "action": row.action,
            "entity_id": row.entity_id,
            "details": row.details,
            "timestamp": row.created_at,
        }
        for row in session.scalars(query.order_by(Audit.id.desc()).limit(200))
    ]


def summary(rows: list[dict], case_rows: list[dict] | None = None) -> dict:
    def dollars(predicate):
        return sum(row["amount_minor"] for row in rows if predicate(row)) / 100

    confirmed = [r for r in rows if r["confirmed_fraud"] is not None]
    legitimate = [r for r in rows if r["confirmed_fraud"] is False]
    false_blocks = sum(r["status"] == "blocked" for r in legitimate)
    volume = dollars(lambda _: True)
    loss = dollars(
        lambda r: (
            r["confirmed_fraud"] is True and r["status"] in ["settled", "returned"]
        )
    )
    return {
        "payment_volume": volume,
        "transactions": len(rows),
        "confirmed_fraud_loss": loss,
        "blocked_fraud_amount": dollars(
            lambda r: r["confirmed_fraud"] is True and r["status"] == "blocked"
        ),
        "legitimate_blocked_amount": dollars(
            lambda r: r["confirmed_fraud"] is False and r["status"] == "blocked"
        ),
        "legitimate_blocks": false_blocks,
        "confirmed_outcomes": len(confirmed),
        "false_positive_rate": false_blocks / len(legitimate) if legitimate else None,
        "fraud_loss_rate": loss / volume if volume and confirmed else None,
        "flagged_transactions": sum(bool(r["signals"]) for r in rows),
        "unassessed_transactions": sum(r["score"] is None for r in rows),
        "open_cases": sum(c["status"] != "closed" for c in (case_rows or [])),
        "currency": "USD",
        "source": "user-submitted payment events",
    }


def rule_performance(rows: list[dict]) -> list[dict]:
    from app.risk_engine.rules import RULES

    results = []
    for rule in RULES:
        hits = [
            row
            for row in rows
            if any(s["rule_id"] == rule.rule_id for s in row["signals"])
        ]
        labeled = [row for row in hits if row["confirmed_fraud"] is not None]
        true = sum(row["confirmed_fraud"] is True for row in labeled)
        results.append(
            {
                "Rule": rule.rule_id,
                "Name": rule.name,
                "Signals": len(hits),
                "Confirmed fraud": true,
                "Confirmed legitimate": len(labeled) - true,
                "Precision": true / len(labeled) if labeled else None,
            }
        )
    return results


def simulate(rows: list[dict], request: SimulationRequest) -> dict:
    if not request.confirmed:
        raise ValueError("Confirm simulation settings first.")
    if not rows:
        raise ValueError("Add payment events before running a simulation.")
    results = [assess(event_input(row), request.thresholds) for row in rows]
    current = [row["score"] is not None and row["score"] >= 60 for row in rows]
    proposed = [
        r["score"] is not None and r["score"] >= request.decision_threshold
        for r in results
    ]

    def measure(flags):
        return {
            "flagged": sum(flags),
            "confirmed_fraud_flagged": sum(
                flag and row["confirmed_fraud"] is True
                for row, flag in zip(rows, flags)
            ),
            "confirmed_legitimate_flagged": sum(
                flag and row["confirmed_fraud"] is False
                for row, flag in zip(rows, flags)
            ),
            "confirmed_fraud_exposure": sum(
                row["amount_minor"]
                for row, flag in zip(rows, flags)
                if flag and row["confirmed_fraud"] is True
            )
            / 100,
        }

    return {
        "current": measure(current),
        "proposed": measure(proposed),
        "settings": request.model_dump(),
        "note": "Retrospective rules-only comparison. Unassessed events remain unassessed. No policy or payment status is changed.",
    }


def report(rows: list[dict], case_rows: list[dict]) -> str:
    metrics = summary(rows, case_rows)
    content = "".join(
        f"<tr><td>{escape(key.replace('_', ' ').title())}</td><td>{escape(str(value))}</td></tr>"
        for key, value in metrics.items()
        if value is not None
    )
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><title>PaymentGuard — Risk report</title><style>body{{font:15px system-ui;max-width:900px;margin:60px auto;color:#16322a;padding:24px}}h1{{font-size:36px}}td{{padding:12px;border-bottom:1px solid #dde4e0}}table{{width:100%}}small{{color:#5b7068}}</style><small>PAYMENTGUARD / WORKSPACE REPORT</small><h1>Payment risk overview</h1><p>Based only on payment events submitted to this workspace. All monetary values are USD. Missing outcomes are not counted as legitimate. Blocked fraud amount is reported exposure, not a claim of realized savings. This report does not certify payment settlement or model performance.</p><table>{content}</table></html>'


def rail_analysis(session, owner_id: str) -> list[dict]:
    query = (
        select(
            PaymentEvent.rail,
            func.count(PaymentEvent.id).label("transactions"),
            func.sum(PaymentEvent.amount_minor).label("amount_minor"),
        )
        .where(PaymentEvent.owner_id == owner_id)
        .group_by(PaymentEvent.rail)
    )
    return [
        {"Payment rail": rail, "Transactions": count, "Amount / USD": amount / 100}
        for rail, count, amount in session.execute(query)
    ]
