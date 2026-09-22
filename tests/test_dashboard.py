"""All pages and critical interactions against an isolated, reproducible test dataset."""

from pathlib import Path
import subprocess
import sys
import os


def test_dashboard_pages_and_simulation(tmp_path):
    # Subprocess isolates Streamlit caches, service globals, and case writes from user data.
    root = Path(__file__).resolve().parents[1]
    code = r"""
from pathlib import Path
import app.utils.config as config
config.DATA=Path(__import__('os').environ['TEST_DATA'])
config.DATA.mkdir(exist_ok=True)
from app.services.pipeline import build
build(500)
from streamlit.testing.v1 import AppTest
at=AppTest.from_file(str(Path.cwd()/'app/dashboard/research.py'),default_timeout=60).run()
assert not at.exception
selected_priority = next(item for item in at.selectbox if item.label == 'Inspect priority payment').value
next(button for button in at.button if button.label == 'Inspect payment').click().run()
assert not at.exception
assert at.session_state['page'] == 'Transaction Monitor'
assert at.text_input[0].value == selected_priority
assert next(item for item in at.selectbox if item.label == 'Inspect a transaction').value == selected_priority
at.sidebar.radio[0].set_value('Executive Overview').run()
next(button for button in at.button if button.label.startswith('Review queue')).click().run()
assert not at.exception
assert at.session_state['page']=='Transaction Monitor'
assert at.session_state['monitor_queue_only'] is True
assert next(item for item in at.multiselect if item.label=='Transaction status').value==['review']
at.toggle[0].set_value(False).run()
next(item for item in at.multiselect if item.label=='Transaction status').set_value([]).run()
for page in ['Transaction Monitor','Investigation Workbench','Fraud Trends','Rule Performance','Rule Simulator','Model Performance','Leadership Recommendations','SQL Explorer','Executive Overview']:
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, [e.message for e in at.exception]
at.sidebar.radio[0].set_value('Rule Simulator').run()
at.checkbox[0].check()
at.button[0].click().run()
assert not at.exception
assert at.session_state['simulation_result']['delta']['tp']==0
at.sidebar.radio[0].set_value('Transaction Monitor').run()
at.text_input[0].set_value('NO-SUCH-TRANSACTION').run()
assert not at.exception
assert any('No payments match' in info.value for info in at.info)
at.text_input[0].set_value('').run()
at.button[0].click().run()
assert not at.exception
at.sidebar.radio[0].set_value('Investigation Workbench').run()
assert not at.exception
at.text_input[0].set_value('Demo Analyst')
at.text_area[0].set_value('Verified evidence and requested step-up authentication.')
next(x for x in at.selectbox if x.label=='Decision').set_value('request verification')
next(x for x in at.selectbox if x.label=='Case status').set_value('in review')
at.button[0].click().run()
assert not at.exception
from app.database.session import SessionLocal
from app.repositories.cases import list_cases,audit_history
with SessionLocal() as session:
    cases=list_cases(session)
    assert len(cases)==1 and cases[0]['assignee']=='Demo Analyst'
    assert cases[0]['decision']=='request verification'
    assert len(audit_history(session,cases[0]['id']))==2
"""
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}",
        "TEST_DATA": str(tmp_path / "data"),
        "APP_MODE": "demo",
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
