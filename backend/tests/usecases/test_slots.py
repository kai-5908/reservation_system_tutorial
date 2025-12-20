from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from app.models import Slot, SlotStatus
from app.usecases import slots as uc


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class FakeSlotRepo:
    def __init__(self) -> None:
        self.created: Optional[Slot] = None

    async def create(
        self,
        *,
        shop_id: int,
        seat_id: int | None,
        starts_at: datetime,
        ends_at: datetime,
        capacity: int,
        status: SlotStatus,
    ) -> Slot:
        now = _utc_now_naive()
        self.created = Slot(
            id=1,
            shop_id=shop_id,
            seat_id=seat_id,
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=capacity,
            status=status,
            created_at=now,
            updated_at=now,
        )
        return self.created


@pytest.mark.asyncio
async def test_create_slot_persists_when_valid() -> None:
    repo = FakeSlotRepo()
    start = _utc_now_naive()
    end = start + timedelta(hours=1)
    slot = await uc.create_slot(
        repo,
        shop_id=1,
        seat_id=None,
        starts_at=start,
        ends_at=end,
        capacity=4,
        status=SlotStatus.OPEN,
    )
    assert slot is repo.created
    assert slot.capacity == 4


@pytest.mark.asyncio
async def test_create_slot_rejects_invalid_time_range() -> None:
    repo = FakeSlotRepo()
    start = _utc_now_naive()
    with pytest.raises(ValueError):
        await uc.create_slot(
            repo,
            shop_id=1,
            seat_id=None,
            starts_at=start,
            ends_at=start,
            capacity=4,
            status=SlotStatus.OPEN,
        )


@pytest.mark.asyncio
async def test_create_slot_rejects_capacity_below_one() -> None:
    repo = FakeSlotRepo()
    start = _utc_now_naive()
    with pytest.raises(ValueError):
        await uc.create_slot(
            repo,
            shop_id=1,
            seat_id=None,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            capacity=0,
            status=SlotStatus.OPEN,
        )
