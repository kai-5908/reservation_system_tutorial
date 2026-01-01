from datetime import timedelta
from typing import Any, AsyncIterator

import pytest
from app.config import get_settings
from app.deps import get_current_user_id, get_session
from app.utils.auth import create_access_token
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


class DummySession:
    def __init__(self, user_exists: bool) -> None:
        self.user_exists = user_exists

    async def __aenter__(self) -> "DummySession":  # pragma: no cover
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:  # pragma: no cover
        return False

    async def scalar(self, *args: Any, **kwargs: Any) -> int | None:
        return 1 if self.user_exists else None

    async def rollback(self) -> None:
        return None


def _make_app(user_exists: bool) -> TestClient:
    app = FastAPI()

    async def override_get_session() -> AsyncIterator[DummySession]:
        session = DummySession(user_exists=user_exists)
        yield session

    app.dependency_overrides[get_session] = override_get_session

    @app.get("/protected")
    async def protected(user_id: int = Depends(get_current_user_id)) -> dict[str, int]:
        return {"user_id": user_id}

    return TestClient(app)


def _token(secret: str, *, expired: bool = False) -> str:
    delta = timedelta(seconds=-1) if expired else timedelta(minutes=30)
    return create_access_token(user_id=123, secret=secret, expires_delta=delta)


@pytest.fixture(autouse=True)
def _auth_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SECRET", "testsecret")
    get_settings.cache_clear()


def test_protected_accepts_valid_token() -> None:
    client = _make_app(user_exists=True)
    token = _token("testsecret")
    res = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["user_id"] == 123


def test_protected_rejects_missing_header() -> None:
    client = _make_app(user_exists=True)
    res = client.get("/protected")
    assert res.status_code == 401
    assert res.headers.get("www-authenticate", "").lower().startswith("bearer")


def test_protected_rejects_invalid_token() -> None:
    client = _make_app(user_exists=True)
    res = client.get("/protected", headers={"Authorization": "Bearer invalid"})
    assert res.status_code == 401


def test_protected_rejects_expired_token() -> None:
    client = _make_app(user_exists=True)
    token = _token("testsecret", expired=True)
    res = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_protected_rejects_when_user_not_found() -> None:
    client = _make_app(user_exists=False)
    token = _token("testsecret")
    res = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
