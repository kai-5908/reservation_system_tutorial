import pytest

from app.domain.errors import SlotNotOpenError
from app.models import ReservationStatus, Slot
from app.usecases import reservations as uc


class FakeResRepo:
    def __init__(self, reservation):
        self.reservation = reservation
        self.cancel_called = False

    async def get_for_user(self, reservation_id, user_id):
        return self.reservation, self.reservation.slot

    async def cancel(self, reservation):
        self.cancel_called = True
        return reservation

    # unused in these tests
    async def user_has_active(self, slot_id, user_id): ...
    async def sum_reserved(self, slot_id): ...
    async def create(self, slot_id, user_id, party_size, status): ...
    async def list_by_user(self, user_id): ...


class FakeReservation:
    def __init__(self, status):
        self.id = 1
        self.slot = Slot(
            id=1,
            shop_id=1,
            seat_id=None,
            starts_at=None,
            ends_at=None,
            capacity=4,
            status=None,
            created_at=None,
            updated_at=None,
        )
        self.status = status
        self.version = 1
        self.party_size = 1
        self.slot_id = 1
        self.user_id = 1
        self.updated_at = None


@pytest.mark.asyncio
async def test_cancel_returns_existing_when_already_cancelled():
    reservation = FakeReservation(ReservationStatus.CANCELLED)
    repo = FakeResRepo(reservation)
    updated, _, status_value = await uc.cancel_reservation(repo, reservation_id=1, user_id=1)
    assert updated is reservation
    assert status_value == ReservationStatus.CANCELLED
    assert repo.cancel_called is False


@pytest.mark.asyncio
async def test_cancel_updates_when_booked():
    reservation = FakeReservation(ReservationStatus.BOOKED)
    repo = FakeResRepo(reservation)
    updated, _, status_value = await uc.cancel_reservation(repo, reservation_id=1, user_id=1)
    assert status_value == ReservationStatus.CANCELLED
    assert repo.cancel_called is True
