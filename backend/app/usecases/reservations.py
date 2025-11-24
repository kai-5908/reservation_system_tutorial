from datetime import datetime, timezone

from ..domain.errors import SlotNotOpenError
from ..domain.repositories import ReservationRepository, SlotRepository
from ..domain.services import SlotSnapshot, validate_reservation
from ..models import ReservationStatus, Slot


async def create_reservation(
    slot_repo: SlotRepository,
    res_repo: ReservationRepository,
    *,
    slot_id: int,
    user_id: int,
    party_size: int,
) -> tuple[object, Slot]:
    slot = await slot_repo.get_for_update(slot_id)
    if slot is None:
        raise SlotNotOpenError("slot not found")

    user_has_active = await res_repo.user_has_active(slot_id, user_id)
    reserved = await res_repo.sum_reserved(slot_id)

    snapshot = SlotSnapshot(
        status=slot.status,
        capacity=slot.capacity,
        reserved=reserved,
        user_has_active_reservation=user_has_active,
    )
    validate_reservation(snapshot, party_size=party_size)

    reservation = await res_repo.create(
        slot_id=slot.id,
        user_id=user_id,
        party_size=party_size,
        status=ReservationStatus.BOOKED,
    )
    return reservation, slot


async def cancel_reservation(
    res_repo: ReservationRepository,
    *,
    reservation_id: int,
    user_id: int,
) -> tuple[object, Slot, ReservationStatus]:
    row = await res_repo.get_for_user(reservation_id, user_id)
    if row is None:
        raise SlotNotOpenError("reservation not found")
    reservation, slot = row
    if reservation.status == ReservationStatus.CANCELLED:
        return reservation, slot, reservation.status
    reservation.status = ReservationStatus.CANCELLED
    reservation.version += 1
    reservation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    updated = await res_repo.cancel(reservation)
    return updated, slot, updated.status


async def list_user_reservations(
    res_repo: ReservationRepository,
    *,
    user_id: int,
) -> list[tuple]:
    return await res_repo.list_by_user(user_id)


async def get_user_reservation(
    res_repo: ReservationRepository,
    *,
    reservation_id: int,
    user_id: int,
) -> tuple | None:
    return await res_repo.get_for_user(reservation_id, user_id)
