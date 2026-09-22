import pytest
from fastapi import HTTPException
import app.api.security as security


def test_authenticated_mode_rejects_missing_and_duplicate_keys(monkeypatch):
    monkeypatch.setattr(security, "APP_MODE", "authenticated")
    for role in ["ANALYST", "MANAGER", "AUDITOR"]:
        monkeypatch.delenv(f"{role}_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        security.validate_security()
    for role in ["ANALYST", "MANAGER", "AUDITOR"]:
        monkeypatch.setenv(f"{role}_API_KEY", "test-only-shared-key-00000000000")
    with pytest.raises(RuntimeError):
        security.validate_security()


def test_authenticated_mode_roles_and_denial(monkeypatch):
    monkeypatch.setattr(security, "APP_MODE", "authenticated")
    for role in ["ANALYST", "MANAGER", "AUDITOR"]:
        monkeypatch.setenv(f"{role}_API_KEY", f"test-only-{role}-0000000000000")
    security.validate_security()
    assert security.identity("test-only-ANALYST-0000000000000")["role"] == "analyst"
    with pytest.raises(HTTPException) as error:
        security.identity("invalid")
    assert error.value.status_code == 401
    with pytest.raises(HTTPException):
        security.authorize({"role": "auditor"}, ["manager"])
