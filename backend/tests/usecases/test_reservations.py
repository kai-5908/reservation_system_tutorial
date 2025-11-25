from datetime import datetime
from typing import List, Optional, Tuple, cast

import pytest
from app.domain.errors import VersionConflictError
from app.models import Reservation, ReservationStatus, Slot, SlotStatus
from app.usecases import reservations as uc


class FakeResRepo:
    def __init__(self, reservation: Reservation) -> None:
        self.reservation = reservation
        self.cancel_called = False

    async def get_for_user_for_update(self, reservation_id: int, user_id: int) -> Tuple[Reservation, Slot]:
        return self.reservation, self.reservation.slot

    async def get_for_user(self, reservation_id: int, user_id: int) -> Tuple[Reservation, Slot]:
        return self.reservation, self.reservation.slot

    async def cancel(self, reservation: Reservation) -> Reservation:
        self.cancel_called = True
        return reservation

    # unused in these tests
    async def user_has_active(self, slot_id: int, user_id: int) -> bool:  # pragma: no cover
        return False

    async def sum_reserved(self, slot_id: int) -> int:  # pragma: no cover
        return 0

    async def create(  # pragma: no cover
        self,
        slot_id: int,
        user_id: int,
        party_size: int,
        status: ReservationStatus,
    ) -> Reservation:
        return self.reservation

    async def list_by_user(self, user_id: int) -> List[Tuple[Reservation, Slot]]:  # pragma: no cover
        return [(self.reservation, self.reservation.slot)]


class FakeReservationStruct:
    def __init__(self, status: ReservationStatus) -> None:
        self.id: int = 1
        self.slot: Slot = Slot(
            id=1,
            shop_id=1,
            seat_id=None,
            starts_at=datetime.utcnow(),
            ends_at=datetime.utcnow(),
            capacity=4,
            status=SlotStatus.OPEN,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.status: ReservationStatus = status
        self.version: int = 1
        self.party_size: int = 1
        self.slot_id: int = 1
        self.user_id: int = 1
        self.updated_at: Optional[object] = None


@pytest.mark.asyncio
async def test_cancel_returns_existing_when_already_cancelled() -> None:
    reservation_struct = FakeReservationStruct(ReservationStatus.CANCELLED)
    reservation = cast(Reservation, reservation_struct)
    repo = FakeResRepo(reservation)
    updated, _, status_value = await uc.cancel_reservation(repo, reservation_id=1, user_id=1, version=1)
    assert updated is reservation
    assert status_value == ReservationStatus.CANCELLED
    assert repo.cancel_called is False


@pytest.mark.asyncio
async def test_cancel_updates_when_booked() -> None:
    reservation_struct = FakeReservationStruct(ReservationStatus.BOOKED)
    reservation = cast(Reservation, reservation_struct)
    repo = FakeResRepo(reservation)
    updated, _, status_value = await uc.cancel_reservation(repo, reservation_id=1, user_id=1, version=1)
    assert status_value == ReservationStatus.CANCEL_PENDING
    assert repo.cancel_called is True


@pytest.mark.asyncio
async def test_cancel_raises_on_version_conflict() -> None:
    reservation_struct = FakeReservationStruct(ReservationStatus.BOOKED)
    reservation_struct.version = 2
    reservation = cast(Reservation, reservation_struct)
    repo = FakeResRepo(reservation)
    with pytest.raises(VersionConflictError):
        await uc.cancel_reservation(repo, reservation_id=1, user_id=1, version=1)
