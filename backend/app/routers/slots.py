from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_session
from ..infrastructure.repositories import SqlAlchemySlotRepository
from ..schemas import SlotAvailability
from ..usecases import slots as slot_usecase
from ..utils.time import to_utc_naive, utc_naive_to_jst

router = APIRouter(prefix="/shops", tags=["slots"])


@router.get("/{shop_id}/slots/availability", response_model=List[SlotAvailability])
async def list_availability(
    shop_id: int,
    start: datetime = Query(..., description="JST start datetime (ISO 8601)"),
    end: datetime = Query(..., description="JST end datetime (ISO 8601)"),
    seat_id: Optional[int] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[SlotAvailability]:
    slot_repo = SqlAlchemySlotRepository(session)
    if start.tzinfo is None or end.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start/end must have timezone")
    utc_start = to_utc_naive(start)
    utc_end = to_utc_naive(end)
    rows = await slot_usecase.list_availability(
        slot_repo,
        shop_id=shop_id,
        start=utc_start,
        end=utc_end,
        seat_id=seat_id,
    )
    return [
        SlotAvailability(
            slot_id=entry["slot"].id,
            shop_id=entry["slot"].shop_id,
            seat_id=entry["slot"].seat_id,
            starts_at=utc_naive_to_jst(entry["slot"].starts_at),
            ends_at=utc_naive_to_jst(entry["slot"].ends_at),
            capacity=entry["slot"].capacity,
            status=entry["slot"].status,
            remaining=entry["remaining"],
        )
        for entry in rows
    ]
