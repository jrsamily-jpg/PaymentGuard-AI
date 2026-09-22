"""Independent operational store; research artifacts are never read by this runtime."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DATA = ROOT / "data" / "workspaces"
DATA.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv(
    "WORKSPACE_DATABASE_URL", f"sqlite:///{DATA / 'workspaces.db'}"
)


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def setup(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")


Session = sessionmaker(bind=engine, expire_on_commit=False)


def initialize():
    from app.workspace import models  # noqa: F401

    Base.metadata.create_all(engine)
