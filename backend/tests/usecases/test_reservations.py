from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, cast

import pytest
from app.domain.errors import (
    CancelNotAllowedError,
    CapacityError,
    DuplicateReservationError,
    RescheduleNotAllowedError,
    SlotNotOpenError,
    VersionConflictError,
)
from app.models import Reservation, ReservationStatus, Slot, SlotStatus
from app.usecases import reservations as uc


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FakeResRepo:
    def __init__(self, reservation: Reservation) -> None:
        self.reservation = reservation
        self.cancel_called = False
        self.reschedule_called = False

    async def get_for_user_for_update(self, reservation_id: int, user_id: int) -> Tuple[Reservation, Slot]:
        return self.reservation, self.reservation.slot

    async def get_for_user(self, reservation_id: int, user_id: int) -> Tuple[Reservation, Slot]:
        return self.reservation, self.reservation.slot

    async def cancel(self, reservation: Reservation) -> Reservation:
        self.cancel_called = True
        return reservation

    async def reschedule(self, reservation: Reservation) -> Reservation:
        self.reschedule_called = True
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

    async def list_by_user(  # pragma: no cover
        self,
        user_id: int,
        status: ReservationStatus | None = None,
    ) -> List[Tuple[Reservation, Slot]]:
        return [(self.reservation, self.reservation.slot)]

    async def list_with_reserved(  # pragma: no cover - satisfy SlotRepository when used
        self,
        shop_id: int,
        start: datetime,
        end: datetime,
        seat_id: int | None,
    ) -> list[tuple[Slot, int]]:
        return []


class FakeReservationStruct:
    def __init__(self, status: ReservationStatus) -> None:
        starts_at = _utc_now_naive() + timedelta(days=3)
        self.id: int = 1
        self.slot: Slot = Slot(
            id=1,
            shop_id=1,
            seat_id=None,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            capacity=4,
            status=SlotStatus.OPEN,
            created_at=_utc_now_naive(),
            updated_at=_utc_now_naive(),
        )
        self.status: ReservationStatus = status
        self.version: int = 1
        self.party_size: int = 1
        self.slot_id: int = 1
        self.user_id: int = 1
        self.updated_at: Optional[object] = None
        self.starts_at = starts_at


class FakeSlotRepo:
    def __init__(self, slots: dict[int, Slot]) -> None:
        self.slots = slots

    async def get_for_update(self, slot_id: int) -> Slot | None:
        return self.slots.get(slot_id)

    async def create(
        self,
        *,
        shop_id: int,
        seat_id: int | None,
        starts_at: datetime,
        ends_at: datetime,
        capacity: int,
        status: SlotStatus,
    ) -> Slot:  # pragma: no cover - not used in these tests
        slot = Slot(
            id=max(self.slots.keys(), default=0) + 1,
            shop_id=shop_id,
            seat_id=seat_id,
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=capacity,
            status=status,
            created_at=_utc_now_naive(),
            updated_at=_utc_now_naive(),
        )
        self.slots[slot.id] = slot
        return slot

    async def list_with_reserved(  # pragma: no cover - not used in these tests
        self,
        shop_id: int,
        start: datetime,
        end: datetime,
        seat_id: int | None,
    ) -> list[tuple[Slot, int]]:
        return []


class FakeRescheduleRepo:
    def __init__(
        self,
        reservation: Reservation,
        *,
        reserved_by_slot: dict[int, int] | None = None,
        active_slots: set[int] | None = None,
    ) -> None:
        self.reservation = reservation
        self.reserved_by_slot = reserved_by_slot or {}
        self.active_slots = active_slots or set()
        self.reschedule_called = False

    async def get_for_user_for_update(self, reservation_id: int, user_id: int) -> Tuple[Reservation, Slot]:
        return self.reservation, self.reservation.slot

    async def get_for_user(self, reservation_id: int, user_id: int) -> Tuple[Reservation, Slot]:
        return self.reservation, self.reservation.slot

    async def cancel(self, reservation: Reservation) -> Reservation:  # pragma: no cover
        return reservation

    async def reschedule(self, reservation: Reservation) -> Reservation:
        self.reschedule_called = True
        self.reservation = reservation
        return reservation

    async def user_has_active(self, slot_id: int, user_id: int) -> bool:
        return slot_id in self.active_slots

    async def sum_reserved(self, slot_id: int) -> int:
        return self.reserved_by_slot.get(slot_id, 0)

    async def create(  # pragma: no cover
        self,
        slot_id: int,
        user_id: int,
        party_size: int,
        status: ReservationStatus,
    ) -> Reservation:
        return self.reservation

    async def list_by_user(  # pragma: no cover
        self,
        user_id: int,
        status: ReservationStatus | None = None,
    ) -> List[Tuple[Reservation, Slot]]:
        return [(self.reservation, self.reservation.slot)]

    async def list_with_reserved(  # pragma: no cover - satisfy SlotRepository when used
        self,
        shop_id: int,
        start: datetime,
        end: datetime,
        seat_id: int | None,
    ) -> list[tuple[Slot, int]]:
        return []


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
    assert status_value == ReservationStatus.CANCELLED
    assert repo.cancel_called is True


@pytest.mark.asyncio
async def test_cancel_raises_on_version_conflict() -> None:
    reservation_struct = FakeReservationStruct(ReservationStatus.BOOKED)
    reservation_struct.version = 2
    reservation = cast(Reservation, reservation_struct)
    repo = FakeResRepo(reservation)
    with pytest.raises(VersionConflictError):
        await uc.cancel_reservation(repo, reservation_id=1, user_id=1, version=1)


@pytest.mark.asyncio
async def test_cancel_idempotent_when_already_pending() -> None:
    reservation_struct = FakeReservationStruct(ReservationStatus.CANCELLED)
    reservation_struct.version = 5
    reservation = cast(Reservation, reservation_struct)
    repo = FakeResRepo(reservation)
    updated, _, status_value = await uc.cancel_reservation(repo, reservation_id=1, user_id=1, version=1)
    assert status_value == ReservationStatus.CANCELLED
    assert repo.cancel_called is False


@pytest.mark.asyncio
async def test_cancel_forbidden_within_cutoff() -> None:
    reservation_struct = FakeReservationStruct(ReservationStatus.BOOKED)
    # starts_at within 2 days from now
    reservation_struct.slot.starts_at = _utc_now_naive()
    reservation = cast(Reservation, reservation_struct)
    repo = FakeResRepo(reservation)
    with pytest.raises(CancelNotAllowedError):
        await uc.cancel_reservation(repo, reservation_id=1, user_id=1, version=1)


def _slot_with(
    slot_id: int,
    shop_id: int = 1,
    starts_at: datetime | None = None,
    status: SlotStatus = SlotStatus.OPEN,
    capacity: int = 4,
) -> Slot:
    start = starts_at or _utc_now_naive() + timedelta(days=3)
    return Slot(
        id=slot_id,
        shop_id=shop_id,
        seat_id=None,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        capacity=capacity,
        status=status,
        created_at=_utc_now_naive(),
        updated_at=_utc_now_naive(),
    )


@pytest.mark.asyncio
async def test_reschedule_moves_to_target_slot_and_increments_version() -> None:
    current_slot = _slot_with(1)
    target_slot = _slot_with(2)
    reservation = cast(Reservation, FakeReservationStruct(ReservationStatus.BOOKED))
    reservation.slot = current_slot
    reservation.slot_id = current_slot.id
    repo = FakeRescheduleRepo(reservation, reserved_by_slot={2: 1})
    slot_repo = FakeSlotRepo({1: current_slot, 2: target_slot})

    updated, slot = await uc.reschedule_reservation(
        slot_repo,
        repo,
        reservation_id=1,
        user_id=1,
        new_slot_id=2,
        version=1,
    )

    assert slot.id == 2
    assert updated.slot_id == 2
    assert updated.version == 2
    assert repo.reschedule_called is True


@pytest.mark.asyncio
async def test_reschedule_disallowed_within_cutoff() -> None:
    start = _utc_now_naive() + timedelta(hours=12)
    current_slot = _slot_with(1, starts_at=start)
    target_slot = _slot_with(2)
    reservation = cast(Reservation, FakeReservationStruct(ReservationStatus.BOOKED))
    reservation.slot = current_slot
    reservation.slot_id = current_slot.id
    repo = FakeRescheduleRepo(reservation)
    slot_repo = FakeSlotRepo({1: current_slot, 2: target_slot})

    with pytest.raises(RescheduleNotAllowedError):
        await uc.reschedule_reservation(
            slot_repo,
            repo,
            reservation_id=1,
            user_id=1,
            new_slot_id=2,
            version=1,
        )


@pytest.mark.asyncio
async def test_reschedule_raises_on_version_conflict() -> None:
    current_slot = _slot_with(1)
    target_slot = _slot_with(2)
    reservation_struct = FakeReservationStruct(ReservationStatus.BOOKED)
    reservation_struct.version = 2
    reservation_struct.slot = current_slot
    reservation_struct.slot_id = current_slot.id
    reservation = cast(Reservation, reservation_struct)
    repo = FakeRescheduleRepo(reservation)
    slot_repo = FakeSlotRepo({1: current_slot, 2: target_slot})

    with pytest.raises(VersionConflictError):
        await uc.reschedule_reservation(
            slot_repo,
            repo,
            reservation_id=1,
            user_id=1,
            new_slot_id=2,
            version=1,
        )


@pytest.mark.asyncio
async def test_reschedule_rejects_when_user_already_has_target() -> None:
    current_slot = _slot_with(1)
    target_slot = _slot_with(2)
    reservation = cast(Reservation, FakeReservationStruct(ReservationStatus.BOOKED))
    reservation.slot = current_slot
    reservation.slot_id = current_slot.id
    repo = FakeRescheduleRepo(reservation, active_slots={2})
    slot_repo = FakeSlotRepo({1: current_slot, 2: target_slot})

    with pytest.raises(DuplicateReservationError):
        await uc.reschedule_reservation(
            slot_repo,
            repo,
            reservation_id=1,
            user_id=1,
            new_slot_id=2,
            version=1,
        )


@pytest.mark.asyncio
async def test_reschedule_rejects_when_capacity_insufficient() -> None:
    current_slot = _slot_with(1)
    target_slot = _slot_with(2, capacity=2)
    reservation_struct = FakeReservationStruct(ReservationStatus.BOOKED)
    reservation_struct.party_size = 2
    reservation = cast(Reservation, reservation_struct)
    reservation.slot = current_slot
    reservation.slot_id = current_slot.id
    repo = FakeRescheduleRepo(reservation, reserved_by_slot={2: 2})
    slot_repo = FakeSlotRepo({1: current_slot, 2: target_slot})

    with pytest.raises(CapacityError):
        await uc.reschedule_reservation(
            slot_repo,
            repo,
            reservation_id=1,
            user_id=1,
            new_slot_id=2,
            version=1,
        )


@pytest.mark.asyncio
async def test_reschedule_rejects_when_target_slot_closed() -> None:
    current_slot = _slot_with(1)
    target_slot = _slot_with(2, status=SlotStatus.CLOSED)
    reservation = cast(Reservation, FakeReservationStruct(ReservationStatus.BOOKED))
    reservation.slot = current_slot
    reservation.slot_id = current_slot.id
    repo = FakeRescheduleRepo(reservation)
    slot_repo = FakeSlotRepo({1: current_slot, 2: target_slot})

    with pytest.raises(SlotNotOpenError):
        await uc.reschedule_reservation(
            slot_repo,
            repo,
            reservation_id=1,
            user_id=1,
            new_slot_id=2,
            version=1,
        )


@pytest.mark.asyncio
async def test_reschedule_rejects_when_shop_differs() -> None:
    current_slot = _slot_with(1, shop_id=1)
    target_slot = _slot_with(2, shop_id=2)
    reservation = cast(Reservation, FakeReservationStruct(ReservationStatus.BOOKED))
    reservation.slot = current_slot
    reservation.slot_id = current_slot.id
    repo = FakeRescheduleRepo(reservation)
    slot_repo = FakeSlotRepo({1: current_slot, 2: target_slot})

    with pytest.raises(RescheduleNotAllowedError):
        await uc.reschedule_reservation(
            slot_repo,
            repo,
            reservation_id=1,
            user_id=1,
            new_slot_id=2,
            version=1,
        )
