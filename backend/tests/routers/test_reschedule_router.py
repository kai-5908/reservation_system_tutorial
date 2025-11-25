from datetime import datetime, timedelta
from typing import Any, Tuple, cast

import pytest
from app.domain.errors import RescheduleNotAllowedError
from app.models import Reservation, ReservationStatus, Slot, SlotStatus
from app.routers import reservations as router
from app.schemas import ReservationReschedule
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


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


class DummyReservationRepo:
    def __init__(self, session: object) -> None:  # pragma: no cover - interface only
        self.session = session


def _make_slot(slot_id: int) -> Slot:
    starts = datetime.utcnow() + timedelta(days=3)
    return Slot(
        id=slot_id,
        shop_id=1,
        seat_id=None,
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        capacity=4,
        status=SlotStatus.OPEN,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _make_reservation(slot: Slot) -> Reservation:
    return Reservation(
        id=10,
        slot_id=slot.id,
        user_id=99,
        party_size=2,
        status=ReservationStatus.BOOKED,
        version=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_reschedule_router_returns_200_and_uses_if_match(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    current_slot = _make_slot(1)
    target_slot = _make_slot(2)
    reservation = _make_reservation(current_slot)

    async def fake_reschedule(
        slot_repo: DummySlotRepo,
        res_repo: DummyReservationRepo,
        *,
        reservation_id: int,
        user_id: int,
        new_slot_id: int,
        version: int,
    ) -> Tuple[Reservation, Slot]:
        assert isinstance(slot_repo, DummySlotRepo)
        assert isinstance(res_repo, DummyReservationRepo)
        assert reservation_id == reservation.id
        assert user_id == reservation.user_id
        assert new_slot_id == target_slot.id
        assert version == 10  # If-Match優先で抽出されることを確認
        reservation.slot_id = target_slot.id
        reservation.version = version + 1
        return reservation, target_slot

    monkeypatch.setattr(router, "SqlAlchemySlotRepository", DummySlotRepo)
    monkeypatch.setattr(router, "SqlAlchemyReservationRepository", DummyReservationRepo)
    monkeypatch.setattr(cast(Any, router.reservation_usecase), "reschedule_reservation", fake_reschedule)  # type: ignore[attr-defined]

    payload = ReservationReschedule(slot_id=target_slot.id)
    result = await router.reschedule_reservation(
        reservation_id=reservation.id,
        payload=payload,
        if_match='"10"',
        session=cast(AsyncSession, session),
        user_id=reservation.user_id,
    )

    assert result.slot_id == target_slot.id
    assert result.version == reservation.version
    assert result.reservation_id == reservation.id


@pytest.mark.asyncio
async def test_reschedule_router_maps_domain_error_to_http_403(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    slot = _make_slot(1)
    reservation = _make_reservation(slot)

    async def fake_reschedule(*args: object, **kwargs: object) -> Tuple[Reservation, Slot]:
        raise RescheduleNotAllowedError("cutoff")

    monkeypatch.setattr(router, "SqlAlchemySlotRepository", DummySlotRepo)
    monkeypatch.setattr(router, "SqlAlchemyReservationRepository", DummyReservationRepo)
    monkeypatch.setattr(cast(Any, router.reservation_usecase), "reschedule_reservation", fake_reschedule)  # type: ignore[attr-defined]

    payload = ReservationReschedule(slot_id=2)
    with pytest.raises(HTTPException) as excinfo:
        await router.reschedule_reservation(
            reservation_id=reservation.id,
            payload=payload,
            if_match='"1"',
            session=cast(AsyncSession, session),
            user_id=reservation.user_id,
        )

    assert excinfo.value.status_code == 403
