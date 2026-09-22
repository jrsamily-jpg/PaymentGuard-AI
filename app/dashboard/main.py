"""PaymentGuard operational entry point. Starts empty; all saved activity is owner-scoped."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.dashboard.workspace import render

render()
