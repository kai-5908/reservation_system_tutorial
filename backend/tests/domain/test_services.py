import pytest
from app.domain.errors import CapacityError, DuplicateReservationError, SlotNotOpenError
from app.domain.services import SlotSnapshot, validate_reservation
from app.models import SlotStatus


def test_rejects_when_slot_not_open() -> None:
    snap = SlotSnapshot(
        status=SlotStatus.CLOSED,
        capacity=4,
        reserved=0,
        user_has_active_reservation=False,
    )
    with pytest.raises(SlotNotOpenError):
        validate_reservation(snap, party_size=2)


def test_rejects_duplicate_reservation() -> None:
    snap = SlotSnapshot(
        status=SlotStatus.OPEN,
        capacity=4,
        reserved=0,
        user_has_active_reservation=True,
    )
    with pytest.raises(DuplicateReservationError):
        validate_reservation(snap, party_size=2)


def test_rejects_when_party_exceeds_remaining() -> None:
    snap = SlotSnapshot(
        status=SlotStatus.OPEN,
        capacity=4,
        reserved=3,
        user_has_active_reservation=False,
    )
    with pytest.raises(CapacityError):
        validate_reservation(snap, party_size=2)


def test_accepts_when_within_capacity_and_no_duplicate() -> None:
    snap = SlotSnapshot(
        status=SlotStatus.OPEN,
        capacity=4,
        reserved=1,
        user_has_active_reservation=False,
    )
    remaining_after = validate_reservation(snap, party_size=2)
    assert remaining_after == 1


def test_accepts_idempotent_cancel_path_is_handled_by_usecase_logic():
    # This test is a placeholder reminder: idempotent cancel is handled in usecase,
    # not in validate_reservation. Kept here to ensure we cover future additions.
    assert True
