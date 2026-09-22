"""Individual credentials, salted scrypt, hashed expiring sessions and login throttling."""

import hashlib
import secrets
import time

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.workspace.models import AccessSession, LoginThrottle, User
from app.workspace.schemas import Credentials


class AuthenticationError(ValueError):
    pass


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode(),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        dklen=32,
        maxmem=64 * 1024 * 1024,
    )


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    return salt.hex() + ":" + _derive(password, salt).hex()


def verify_password(password: str, stored: str) -> bool:
    salt, digest = stored.split(":")
    return secrets.compare_digest(_derive(password, bytes.fromhex(salt)).hex(), digest)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _issue(session, user: User) -> dict:
    token = secrets.token_urlsafe(48)
    session.add(
        AccessSession(
            token_hash=_token_hash(token),
            owner_id=user.id,
            expires_at=int(time.time()) + 12 * 3600,
        )
    )
    session.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 43200,
        "user": {"id": user.id, "username": user.username},
    }


def register(session, credentials: Credentials) -> dict:
    user = User(
        username=credentials.username, password_hash=password_hash(credentials.password)
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise ValueError("Unable to create account. Choose another username.")
    return _issue(session, user)


def login(session, credentials: Credentials) -> dict:
    now = int(time.time())
    subject = hashlib.sha256(credentials.username.encode()).hexdigest()
    limit = session.get(LoginThrottle, subject)
    if limit and now - limit.window_start < 900 and limit.failures >= 5:
        raise AuthenticationError("Too many attempts. Try again in 15 minutes.")
    user = session.scalar(select(User).where(User.username == credentials.username))
    # Perform scrypt even for absent users to reduce obvious timing differences.
    stored = user.password_hash if user else "00" * 16 + ":" + "00" * 32
    if not verify_password(credentials.password, stored) or user is None:
        if limit is None:
            limit = LoginThrottle(subject=subject, failures=0, window_start=now)
            session.add(limit)
        elif now - limit.window_start >= 900:
            limit.failures = 0
            limit.window_start = now
        limit.failures += 1
        session.commit()
        raise AuthenticationError("Username or password is incorrect.")
    if limit:
        session.delete(limit)
    return _issue(session, user)


def authenticate(session, token: str) -> dict:
    if not token or len(token) > 256:
        raise AuthenticationError("Sign in to continue.")
    access = session.get(AccessSession, _token_hash(token))
    if access is None or access.expires_at <= int(time.time()):
        raise AuthenticationError("Session expired. Sign in again.")
    user = session.get(User, access.owner_id)
    if user is None:
        raise AuthenticationError("Sign in to continue.")
    return {"id": user.id, "username": user.username}


def logout(session, token: str) -> None:
    session.execute(
        delete(AccessSession).where(AccessSession.token_hash == _token_hash(token))
    )
    session.commit()
