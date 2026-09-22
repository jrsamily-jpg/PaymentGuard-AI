"""Every operational page and an account lifecycle in a temporary database."""

import os
import subprocess
import sys
from pathlib import Path


def test_operational_dashboard(tmp_path):
    code = r"""
from pathlib import Path
from streamlit.testing.v1 import AppTest
from app.workspace import auth
from app.workspace.database import Session
from app.workspace.schemas import Credentials
path = str(Path.cwd()/'app/dashboard/main.py')
at = AppTest.from_file(path, default_timeout=30).run()
assert not at.exception, [e.message for e in at.exception]
assert not at.metric
next(x for x in at.button if x.label=='Explore workspace').click().run()
assert [m.value for m in at.metric][:4] == ['$0', '0', '$0', '$0']
for page in ['Payments','Investigations','Trends','Controls','Policy simulator','Model evaluation','Reports','Data & access']:
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, (page, [e.message for e in at.exception])
next(x for x in at.radio if x.label=='Account action').set_value('Create account').run()
next(x for x in at.text_input if x.label=='Username').set_value('test-alice')
next(x for x in at.text_input if x.label=='Password').set_value('test-password-not-real-42')
next(x for x in at.text_input if x.label=='Confirm password').set_value('test-password-not-real-42')
next(x for x in at.button if x.label=='Create account').click().run()
assert not at.exception, [e.message for e in at.exception]
assert at.session_state['workspace_page']=='Overview'
assert [m.value for m in at.metric][:4] == ['$0', '0', '$0', '$0']
at.sidebar.radio[0].set_value('Data & access').run()
assert not at.exception, [e.message for e in at.exception]
next(x for x in at.text_input if x.label=='Payment reference').set_value('TEST-ONLY')
next(x for x in at.text_input if x.label=='Customer reference').set_value('TEST-CUSTOMER')
next(x for x in at.text_input if x.label=='Amount · USD').set_value('25.50')
next(x for x in at.text_input if x.label=='Occurred at · ISO 8601').set_value('2026-01-01T00:00:00+00:00')
next(x for x in at.button if x.label=='Record payment').click().run()
assert not at.exception, [e.message for e in at.exception]
at.sidebar.radio[0].set_value('Overview').run()
assert [m.value for m in at.metric][:4] == ['$25.50', '1', '$0', '$0']
for page in ['Payments','Investigations','Trends','Controls','Policy simulator','Model evaluation','Reports','Data & access']:
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, (page,[e.message for e in at.exception])
at.sidebar.radio[0].set_value('Payments').run()
next(x for x in at.button if x.label=='Open investigation').click().run()
at.sidebar.radio[0].set_value('Investigations').run()
assert not at.exception, [e.message for e in at.exception]
next(x for x in at.text_input if x.label=='Assigned to').set_value('Test reviewer')
next(x for x in at.selectbox if x.label=='Decision').set_value('request verification')
next(x for x in at.selectbox if x.label=='Case status').set_value('in review')
next(x for x in at.text_area if x.label=='Investigation note').set_value('Test-only review')
next(x for x in at.button if x.label=='Save investigation').click().run()
assert not at.exception, [e.message for e in at.exception]
assert any('request verification' in x.value for x in at.caption)
# A second browser starts empty; signing in as another account also stays empty.
other = AppTest.from_file(path, default_timeout=30).run()
assert not other.metric
next(x for x in other.button if x.label=='Sign in').click().run()
assert other.session_state['workspace_auth_mode']=='Sign in'
other.sidebar.radio[0].set_value('Overview').run()
assert [m.value for m in other.metric][:4] == ['$0', '0', '$0', '$0']
with Session() as session:
    bob = auth.register(session, Credentials(username='test-bob', password='different-test-password-42'))
other.session_state['workspace_token'] = bob['access_token']
other.run()
assert [m.value for m in other.metric][:4] == ['$0', '0', '$0', '$0']
next(x for x in at.button if x.label=='Sign out').click().run()
assert not at.metric
next(x for x in at.button if x.label=='Create account').click().run()
assert at.session_state['workspace_auth_mode']=='Create account'
at.sidebar.radio[0].set_value('Overview').run()
assert not at.exception, [e.message for e in at.exception]
assert [m.value for m in at.metric][:4] == ['$0', '0', '$0', '$0']
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        env={
            **os.environ,
            "WORKSPACE_DATABASE_URL": f"sqlite:///{tmp_path / 'workspace.db'}",
        },
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
