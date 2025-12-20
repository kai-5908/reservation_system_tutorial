from datetime import datetime, timedelta, timezone
from typing import cast

import pytest
from app.models import Slot, SlotStatus
from app.routers import slots as router
from app.schemas import SlotCreate
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class DummySession:
    """Minimal async session stub that supports `async with session.begin()`."""

    async def __aenter__(self) -> "DummySession":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def begin(self) -> "DummySession":
        return self


class DummySlotRepo:
    def __init__(self, session: object) -> None:  # pragma: no cover - interface only
        self.session = session


def _slot() -> Slot:
    start = _utc_now_naive().replace(microsecond=0)
    return Slot(
        id=1,
        shop_id=1,
        seat_id=None,
        starts_at=start.replace(tzinfo=None),
        ends_at=(start + timedelta(hours=1)).replace(tzinfo=None),
        capacity=4,
        status=SlotStatus.OPEN,
        created_at=start.replace(tzinfo=None),
        updated_at=start.replace(tzinfo=None),
    )


@pytest.mark.asyncio
async def test_create_slot_returns_created_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    slot = _slot()

    async def fake_create_slot(
        slot_repo: DummySlotRepo,
        *,
        shop_id: int,
        seat_id: int | None,
        starts_at: datetime,
        ends_at: datetime,
        capacity: int,
        status: SlotStatus,
    ) -> Slot:
        assert isinstance(slot_repo, DummySlotRepo)
        assert shop_id == slot.shop_id
        assert capacity == slot.capacity
        assert status == slot.status
        slot.starts_at = starts_at
        slot.ends_at = ends_at
        return slot

    monkeypatch.setattr(router, "SqlAlchemySlotRepository", DummySlotRepo)
    monkeypatch.setattr(router.slot_usecase, "create_slot", fake_create_slot)

    payload = SlotCreate(
        seat_id=None,
        starts_at=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))),
        ends_at=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))) + timedelta(hours=1),
        capacity=4,
        status=SlotStatus.OPEN,
    )

    result = await router.create_slot(
        shop_id=1,
        payload=payload,
        session=cast(AsyncSession, session),
    )

    assert result.slot_id == slot.id
    assert result.shop_id == slot.shop_id
    assert result.capacity == payload.capacity


@pytest.mark.asyncio
async def test_create_slot_rejects_without_timezone() -> None:
    session = DummySession()
    payload = SlotCreate(
        seat_id=None,
        starts_at=_utc_now_naive(),
        ends_at=_utc_now_naive() + timedelta(hours=1),
        capacity=4,
        status=SlotStatus.OPEN,
    )
    with pytest.raises(HTTPException) as excinfo:
        await router.create_slot(
            shop_id=1,
            payload=payload,
            session=cast(AsyncSession, session),
        )
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_create_slot_rejects_non_jst_timezone() -> None:
    session = DummySession()
    payload = SlotCreate(
        seat_id=None,
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
        capacity=4,
        status=SlotStatus.OPEN,
    )
    with pytest.raises(HTTPException) as excinfo:
        await router.create_slot(
            shop_id=1,
            payload=payload,
            session=cast(AsyncSession, session),
        )
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_create_slot_returns_409_on_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()

    async def fake_create_slot(*args: object, **kwargs: object) -> Slot:
        raise IntegrityError(None, None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(router, "SqlAlchemySlotRepository", DummySlotRepo)
    monkeypatch.setattr(router.slot_usecase, "create_slot", fake_create_slot)

    payload = SlotCreate(
        seat_id=None,
        starts_at=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))),
        ends_at=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))) + timedelta(hours=1),
        capacity=4,
        status=SlotStatus.OPEN,
    )
    with pytest.raises(HTTPException) as excinfo:
        await router.create_slot(
            shop_id=1,
            payload=payload,
            session=cast(AsyncSession, session),
        )
    assert excinfo.value.status_code == 409
