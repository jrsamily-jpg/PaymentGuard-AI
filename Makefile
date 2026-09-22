.PHONY: install init api dashboard test research-data
PYTHON ?= python
install:
	$(PYTHON) -m pip install -r requirements.txt
init:
	$(PYTHON) -c "from app.workspace.database import initialize; initialize()"
api:
	$(PYTHON) -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
dashboard:
	$(PYTHON) -m streamlit run app/dashboard/main.py
test:
	$(PYTHON) -m pytest --cov=app/risk_engine --cov-report=term-missing
research-data:
	$(PYTHON) -m scripts.ensure_data
