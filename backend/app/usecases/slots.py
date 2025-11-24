from ..domain.repositories import SlotRepository
from ..models import SlotStatus


async def list_availability(
    slot_repo: SlotRepository,
    *,
    shop_id: int,
    start,
    end,
    seat_id: int | None,
):
    rows = await slot_repo.list_with_reserved(shop_id=shop_id, start=start, end=end, seat_id=seat_id)
    items = []
    for slot, reserved in rows:
        if slot.status != SlotStatus.OPEN:
            continue
        remaining = max(slot.capacity - int(reserved), 0)
        items.append(
            {
                "slot": slot,
                "remaining": remaining,
            }
        )
    return items
