from types import SimpleNamespace

import pytest
from app.routers.reservations import _extract_version
from app.schemas import ReservationCancel
from fastapi import HTTPException


def test_if_match_preferred_over_body() -> None:
    payload = ReservationCancel(version=5)
    assert _extract_version('W/"10"', payload) == 10


def test_body_used_when_no_header() -> None:
    payload = ReservationCancel(version=7)
    assert _extract_version(None, payload) == 7


def test_raises_when_missing() -> None:
    with pytest.raises(HTTPException) as excinfo:
        _extract_version(None, None)
    assert excinfo.value.status_code == 400


def test_invalid_header_raises_400() -> None:
    with pytest.raises(HTTPException) as excinfo:
        _extract_version("invalid", None)
    assert excinfo.value.status_code == 400


def test_header_zero_raises_400() -> None:
    with pytest.raises(HTTPException) as excinfo:
        _extract_version('"0"', None)
    assert excinfo.value.status_code == 400


def test_body_zero_raises_400() -> None:
    payload = SimpleNamespace(version=0)  # bypass Pydantic validation to hit router validation
    with pytest.raises(HTTPException) as excinfo:
        _extract_version(None, payload)  # type: ignore[arg-type]
    assert excinfo.value.status_code == 400
