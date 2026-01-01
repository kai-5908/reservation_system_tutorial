from datetime import datetime, timedelta, timezone
from typing import Any, cast

import pytest
from app.models import Reservation, ReservationStatus, Slot, SlotStatus
from app.routers import reservations as router
from app.schemas import ReservationCancel, ReservationCreate, ReservationRead, ReservationReschedule
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


class DummySession:
    async def __aenter__(self) -> "DummySession":
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def begin(self) -> "DummySession":
        return self


def _slot(slot_id: int = 1) -> Slot:
    starts = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    return Slot(
        id=slot_id,
        shop_id=10,
        seat_id=None,
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        capacity=4,
        status=SlotStatus.OPEN,
        created_at=starts,
        updated_at=starts,
    )


def _reservation(slot_id: int = 1, status: ReservationStatus = ReservationStatus.BOOKED) -> Reservation:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return Reservation(
        id=100,
        slot_id=slot_id,
        user_id=200,
        party_size=2,
        status=status,
        version=1,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_create_reservation_emits_audit(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    slot = _slot()
    reservation = _reservation()

    async def fake_create_reservation(*args: object, **kwargs: object) -> tuple[Reservation, Slot]:
        return reservation, slot

    calls: list[dict[str, Any]] = []

    def fake_emit(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(router, "SqlAlchemySlotRepository", lambda s: s)  # type: ignore[assignment]
    monkeypatch.setattr(router, "SqlAlchemyReservationRepository", lambda s: s)  # type: ignore[assignment]
    monkeypatch.setattr(router.reservation_usecase, "create_reservation", fake_create_reservation)  # type: ignore[attr-defined]
    monkeypatch.setattr(router, "emit_audit_log", fake_emit)

    payload = ReservationCreate(slot_id=slot.id, party_size=2)
    result: ReservationRead = await router.create_reservation(
        payload=payload,
        session=cast(AsyncSession, session),
        user_id=reservation.user_id,
    )

    assert result.reservation_id == reservation.id
    assert len(calls) == 1
    assert calls[0]["action"] == "reservation.created"
    assert calls[0]["reservation_id"] == reservation.id


@pytest.mark.asyncio
async def test_cancel_reservation_log_failure_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    slot = _slot()
    reservation = _reservation(status=ReservationStatus.CANCELLED)

    async def fake_cancel(*args: object, **kwargs: object) -> tuple[Reservation, Slot, ReservationStatus]:
        return reservation, slot, ReservationStatus.BOOKED

    def fake_emit(**kwargs: Any) -> None:
        raise RuntimeError("fail log")

    monkeypatch.setattr(router, "SqlAlchemyReservationRepository", lambda s: s)  # type: ignore[assignment]
    monkeypatch.setattr(router.reservation_usecase, "cancel_reservation", fake_cancel)  # type: ignore[attr-defined]
    monkeypatch.setattr(router, "emit_audit_log", fake_emit)

    payload = ReservationCancel(version=1)
    with pytest.raises(HTTPException) as excinfo:
        await router.cancel_reservation(
            reservation_id=reservation.id,
            payload=payload,
            if_match='"1"',
            session=cast(AsyncSession, session),
            user_id=reservation.user_id,
        )
    assert excinfo.value.status_code == 500


@pytest.mark.asyncio
async def test_reschedule_sets_previous_slot_and_emits(monkeypatch: pytest.MonkeyPatch) -> None:
    session = DummySession()
    from_slot = _slot(1)
    to_slot = _slot(2)
    reservation = _reservation(slot_id=from_slot.id)

    async def fake_reschedule(*args: object, **kwargs: object) -> tuple[Reservation, Slot]:
        setattr(reservation, "_previous_slot_id", from_slot.id)  # mimic usecase behavior
        reservation.slot_id = to_slot.id
        return reservation, to_slot

    calls: list[dict[str, Any]] = []

    def fake_emit(**kwargs: Any) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(router, "SqlAlchemySlotRepository", lambda s: s)  # type: ignore[assignment]
    monkeypatch.setattr(router, "SqlAlchemyReservationRepository", lambda s: s)  # type: ignore[assignment]
    monkeypatch.setattr(router.reservation_usecase, "reschedule_reservation", fake_reschedule)  # type: ignore[attr-defined]
    monkeypatch.setattr(router, "emit_audit_log", fake_emit)

    payload = ReservationReschedule(slot_id=to_slot.id, version=1)
    result = await router.reschedule_reservation(
        reservation_id=reservation.id,
        payload=payload,
        if_match='"1"',
        session=cast(AsyncSession, session),
        user_id=reservation.user_id,
    )

    assert result.slot_id == to_slot.id
    assert len(calls) == 1
    assert calls[0]["action"] == "reservation.rescheduled"
    assert calls[0]["extra"]["slot_id_from"] == from_slot.id
