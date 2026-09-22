"""API key role concepts. Demo mode is deliberately unauthenticated and local-only."""

import os
import secrets
from fastapi import Header, HTTPException
from app.utils.config import APP_MODE


def validate_security():
    if APP_MODE not in {"demo", "authenticated"}:
        raise RuntimeError("Unknown APP_MODE")
    if APP_MODE == "authenticated":
        keys = [
            os.getenv(f"{role}_API_KEY", "")
            for role in ["ANALYST", "MANAGER", "AUDITOR"]
        ]
        if any(len(k) < 24 for k in keys) or len(set(keys)) != 3:
            raise RuntimeError("Set three unique API keys of at least 24 characters")


def identity(x_api_key: str | None = Header(default=None)):
    if APP_MODE == "demo":
        return {"role": "manager", "actor": "demo-local"}
    for role in ["analyst", "manager", "auditor"]:
        expected = os.getenv(f"{role.upper()}_API_KEY", "")
        if expected and x_api_key and secrets.compare_digest(expected, x_api_key):
            return {"role": role, "actor": role}
    raise HTTPException(401, "Valid API key required")


def authorize(user, roles):
    if user["role"] not in roles:
        raise HTTPException(403, "Role is not permitted to perform this action")
