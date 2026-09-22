"""Environment configuration, anchored to the repository rather than working directory."""

import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
DATA = ROOT / "data" / "processed"
DATA.mkdir(parents=True, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA / 'paymentguard.db'}")
APP_MODE = os.getenv("APP_MODE", "demo")
