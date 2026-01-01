from datetime import timedelta
from typing import Any

import pytest
from app.config import Settings, get_settings
from app.deps import get_current_user_id
from app.utils.auth import create_access_token
from fastapi import HTTPException
from sqlalchemy.exc import ProgrammingError


class DummySession:
    def __init__(self, user_exists: bool | Exception) -> None:
        self.user_exists = user_exists

    async def __aenter__(self) -> "DummySession":  # pragma: no cover
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:  # pragma: no cover
        return False

    async def scalar(self, *args: Any, **kwargs: Any) -> int | None:
        if isinstance(self.user_exists, Exception):
            raise self.user_exists
        return 1 if self.user_exists else None

    async def rollback(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _set_auth_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SECRET", "testsecret")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_get_current_user_id_accepts_valid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(auth_secret="testsecret")
    token = create_access_token(user_id=123, secret=settings.auth_secret, algorithm=settings.auth_algorithm)
    session = DummySession(user_exists=True)
    result = await get_current_user_id(authorization=f"Bearer {token}", session=session)  # type: ignore[arg-type]
    assert result == 123


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_missing_header() -> None:
    session = DummySession(user_exists=True)
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_id(authorization=None, session=session)  # type: ignore[arg-type]
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_expired_token(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(auth_secret="testsecret")
    token = create_access_token(
        user_id=1,
        secret=settings.auth_secret,
        algorithm=settings.auth_algorithm,
        expires_delta=timedelta(seconds=-1),
    )
    session = DummySession(user_exists=True)
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_id(authorization=f"Bearer {token}", session=session)  # type: ignore[arg-type]
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_id_rejects_when_user_missing() -> None:
    settings = Settings(auth_secret="testsecret")
    token = create_access_token(user_id=99, secret=settings.auth_secret, algorithm=settings.auth_algorithm)
    session = DummySession(user_exists=False)
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_id(authorization=f"Bearer {token}", session=session)  # type: ignore[arg-type]
    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_id_handles_missing_users_table() -> None:
    settings = Settings(auth_secret="testsecret")
    token = create_access_token(user_id=1, secret=settings.auth_secret, algorithm=settings.auth_algorithm)
    session = DummySession(user_exists=ProgrammingError("missing", None, Exception("cause")))
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user_id(authorization=f"Bearer {token}", session=session)  # type: ignore[arg-type]
    assert excinfo.value.status_code == 500
