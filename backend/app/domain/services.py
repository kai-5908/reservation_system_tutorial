from dataclasses import dataclass

from ..models import SlotStatus
from .errors import CapacityError, DuplicateReservationError, SlotNotOpenError


@dataclass(frozen=True)
class SlotSnapshot:
    status: SlotStatus
    capacity: int
    reserved: int
    user_has_active_reservation: bool


def validate_reservation(snapshot: SlotSnapshot, *, party_size: int) -> int:
    """
    Pure validation: ensures slot is open, not duplicated, and capacity is sufficient.
    Returns remaining capacity after booking if OK. Raises domain errors otherwise.
    """
    if snapshot.user_has_active_reservation:
        raise DuplicateReservationError("user already has an active reservation for this slot")
    if snapshot.status != SlotStatus.OPEN:
        raise SlotNotOpenError("slot is not open")
    if party_size <= 0:
        raise CapacityError("party_size must be positive")

    remaining = snapshot.capacity - snapshot.reserved
    if party_size > remaining:
        raise CapacityError("capacity exceeded")
    return remaining - party_size
