from datetime import datetime
from typing import Any, Dict, List

from ..domain.repositories import SlotRepository
from ..models import SlotStatus


async def list_availability(
    slot_repo: SlotRepository,
    *,
    shop_id: int,
    start: datetime,
    end: datetime,
    seat_id: int | None,
) -> List[Dict[str, Any]]:
    rows = await slot_repo.list_with_reserved(shop_id=shop_id, start=start, end=end, seat_id=seat_id)
    items: List[Dict[str, Any]] = []
    for slot, reserved in rows:
        if slot.status != SlotStatus.OPEN:
            continue
        remaining = max(slot.capacity - int(reserved), 0)
        items.append({"slot": slot, "remaining": remaining})
    return items


async def create_slot(
    slot_repo: SlotRepository,
    *,
    shop_id: int,
    seat_id: int | None,
    starts_at: datetime,
    ends_at: datetime,
    capacity: int,
    status: SlotStatus,
):
    if starts_at >= ends_at:
        raise ValueError("starts_at must be earlier than ends_at")
    if capacity < 1:
        raise ValueError("capacity must be >= 1")
    slot = await slot_repo.create(
        shop_id=shop_id,
        seat_id=seat_id,
        starts_at=starts_at,
        ends_at=ends_at,
        capacity=capacity,
        status=status,
    )
    return slot
