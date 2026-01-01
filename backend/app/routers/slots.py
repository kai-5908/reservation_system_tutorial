from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_current_user_id, get_session
from ..infrastructure.repositories import SqlAlchemySlotRepository
from ..schemas import SlotAvailability, SlotCreate, SlotRead
from ..usecases import slots as slot_usecase
from ..utils.time import to_utc_naive, utc_naive_to_jst

router = APIRouter(prefix="/shops", tags=["slots"], dependencies=[Depends(get_current_user_id)])


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


@router.post("/{shop_id}/slots", response_model=SlotRead, status_code=status.HTTP_201_CREATED)
async def create_slot(
    shop_id: int,
    payload: SlotCreate,
    session: AsyncSession = Depends(get_session),
) -> SlotRead:
    if payload.starts_at.tzinfo is None or payload.ends_at.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="starts_at/ends_at must have timezone")
    if not _is_jst(payload.starts_at) or not _is_jst(payload.ends_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="starts_at/ends_at must be JST (+09:00)")
    try:
        starts_utc = to_utc_naive(payload.starts_at)
        ends_utc = to_utc_naive(payload.ends_at)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="starts_at/ends_at must have timezone")

    slot_repo = SqlAlchemySlotRepository(session)
    async with session.begin():
        try:
            slot = await slot_usecase.create_slot(
                slot_repo,
                shop_id=shop_id,
                seat_id=payload.seat_id,
                starts_at=starts_utc,
                ends_at=ends_utc,
                capacity=payload.capacity,
                status=payload.status,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except IntegrityError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="slot already exists") from exc

    return SlotRead.from_db(slot=slot)


def _is_jst(dt: datetime) -> bool:
    """Return True when tz offset is exactly +09:00."""
    if dt.tzinfo is None:
        return False
    offset = dt.tzinfo.utcoffset(dt)
    return offset == timedelta(hours=9)
