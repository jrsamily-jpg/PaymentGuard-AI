"""Idempotent startup; never overwrite existing cases or partially built datasets."""

from sqlalchemy import select, func
from app.database.session import Base, engine, SessionLocal
from app.database.models import Transaction
from app.utils.config import DATA
from app.services.pipeline import build

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(Transaction))
    artifacts = all(
        (DATA / name).exists() for name in ["transactions.csv", "results.json"]
    )
    if count and artifacts:
        print(f"Using existing synthetic cohort: {count:,} transactions")
    elif not count and not artifacts:
        build()
    else:
        raise RuntimeError(
            "Incomplete dataset. Restore matching DB and analytics artifacts before starting."
        )
