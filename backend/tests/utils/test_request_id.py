from app.main import request_id_middleware
from app.utils.request_id import generate_request_id, get_request_id, set_request_id
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import AsyncClient, ASGITransport
import pytest


def test_request_id_set_and_get() -> None:
    set_request_id("req-abc")
    assert get_request_id() == "req-abc"
    set_request_id(None)
    assert get_request_id() is None


def test_generate_request_id_is_not_empty() -> None:
    value = generate_request_id()
    assert isinstance(value, str)
    assert len(value) > 0


@pytest.mark.asyncio
async def test_request_id_middleware_generates_and_sets_header() -> None:
    app = FastAPI()

    @app.get("/check")
    async def check() -> dict[str, str]:
        return {"rid": get_request_id() or ""}

    app.middleware("http")(request_id_middleware)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/check")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")
    assert resp.json()["rid"] == resp.headers["X-Request-ID"]


@pytest.mark.asyncio
async def test_request_id_middleware_uses_incoming_header() -> None:
    app = FastAPI()

    @app.get("/check")
    async def check() -> dict[str, str]:
        return {"rid": get_request_id() or ""}

    app.middleware("http")(request_id_middleware)

    incoming = "req-custom-123"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", headers={"X-Request-ID": incoming}) as client:
        resp = await client.get("/check")
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == incoming
    assert resp.json()["rid"] == incoming
