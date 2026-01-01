from datetime import datetime, timedelta, timezone

from ..domain.errors import (
    CancelNotAllowedError,
    RescheduleNotAllowedError,
    SlotNotOpenError,
    VersionConflictError,
)
from ..domain.repositories import ReservationRepository, SlotRepository
from ..domain.services import SlotSnapshot, validate_reservation
from ..models import Reservation, ReservationStatus, Slot, SlotStatus


async def create_reservation(
    slot_repo: SlotRepository,
    res_repo: ReservationRepository,
    *,
    slot_id: int,
    user_id: int,
    party_size: int,
) -> tuple[Reservation, Slot]:
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
    version: int,
) -> tuple[Reservation, Slot, ReservationStatus]:
    row = await res_repo.get_for_user_for_update(reservation_id, user_id)
    if row is None:
        raise SlotNotOpenError("reservation not found")
    reservation, slot = row
    previous_status = reservation.status
    # Idempotent: already cancelled returns as-is
    if reservation.status == ReservationStatus.CANCELLED:
        return reservation, slot, previous_status
    # Version check after idempotent guard
    if reservation.version != version:
        raise VersionConflictError("version mismatch")
    # Cancellation cutoff: within 2 days before start is not cancellable by user
    if _is_within_cutoff(slot.starts_at, days=2):
        raise CancelNotAllowedError("cancellation window closed")

    reservation.status = ReservationStatus.CANCELLED
    reservation.version += 1
    reservation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    updated = await res_repo.cancel(reservation)
    return updated, slot, updated.status


async def reschedule_reservation(
    slot_repo: SlotRepository,
    res_repo: ReservationRepository,
    *,
    reservation_id: int,
    user_id: int,
    new_slot_id: int,
    version: int,
) -> tuple[Reservation, Slot, int]:
    row = await res_repo.get_for_user_for_update(reservation_id, user_id)
    if row is None:
        raise SlotNotOpenError("reservation not found")
    reservation, current_slot = row
    if reservation.status != ReservationStatus.BOOKED:
        raise RescheduleNotAllowedError("reservation is not reschedulable")
    if reservation.version != version:
        raise VersionConflictError("version mismatch")
    if _is_within_cutoff(current_slot.starts_at, days=2):
        raise RescheduleNotAllowedError("reschedule window closed")
    if reservation.slot_id == new_slot_id:
        # Idempotent: already on the requested slot
        return reservation, current_slot, reservation.slot_id

    target_slot = await slot_repo.get_for_update(new_slot_id)
    if target_slot is None or target_slot.status != SlotStatus.OPEN:
        raise SlotNotOpenError("slot not available")
    if target_slot.shop_id != current_slot.shop_id:
        raise RescheduleNotAllowedError("cannot reschedule to a different shop")

    user_has_active = await res_repo.user_has_active(new_slot_id, user_id)
    reserved = await res_repo.sum_reserved(new_slot_id)
    snapshot = SlotSnapshot(
        status=target_slot.status,
        capacity=target_slot.capacity,
        reserved=reserved,
        user_has_active_reservation=user_has_active,
    )
    validate_reservation(snapshot, party_size=reservation.party_size)

    previous_slot_id = reservation.slot_id
    reservation.slot_id = target_slot.id
    reservation.slot = target_slot
    reservation.version += 1
    reservation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    updated = await res_repo.reschedule(reservation)
    return updated, target_slot, previous_slot_id


async def list_user_reservations(
    res_repo: ReservationRepository,
    *,
    user_id: int,
    status: ReservationStatus | None = None,
) -> list[tuple[Reservation, Slot]]:
    return await res_repo.list_by_user(user_id, status=status)


async def get_user_reservation(
    res_repo: ReservationRepository,
    *,
    reservation_id: int,
    user_id: int,
) -> tuple[Reservation, Slot] | None:
    return await res_repo.get_for_user(reservation_id, user_id)


def _is_within_cutoff(starts_at: datetime, *, days: int) -> bool:
    """Return True if now UTC is within `days` before the slot starts."""
    now_utc = datetime.now(timezone.utc)
    if starts_at.tzinfo is None:
        starts_at_utc = starts_at.replace(tzinfo=timezone.utc)
    else:
        starts_at_utc = starts_at.astimezone(timezone.utc)
    cutoff = starts_at_utc - timedelta(days=days)
    return now_utc >= cutoff
