from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_current_user_id, get_session
from ..domain.errors import CapacityError, DuplicateReservationError, SlotNotOpenError
from ..infrastructure.repositories import SqlAlchemyReservationRepository, SqlAlchemySlotRepository
from ..schemas import ReservationCreate, ReservationRead
from ..usecases import reservations as reservation_usecase

router = APIRouter(prefix="", tags=["reservations"])


@router.post("/reservations", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
async def create_reservation(
    payload: ReservationCreate,
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> ReservationRead:
    slot_repo = SqlAlchemySlotRepository(session)
    res_repo = SqlAlchemyReservationRepository(session)
    async with session.begin():
        try:
            reservation, slot = await reservation_usecase.create_reservation(
                slot_repo,
                res_repo,
                slot_id=payload.slot_id,
                user_id=user_id,
                party_size=payload.party_size,
            )
        except SlotNotOpenError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="slot not available")
        except DuplicateReservationError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="duplicate reservation for this slot")
        except CapacityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="capacity exceeded")

    return ReservationRead.from_db(reservation=reservation, slot=slot, shop_id=slot.shop_id)


@router.get("/me/reservations", response_model=List[ReservationRead])
async def list_my_reservations(
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> list[ReservationRead]:
    res_repo = SqlAlchemyReservationRepository(session)
    rows = await reservation_usecase.list_user_reservations(res_repo, user_id=user_id)
    return [ReservationRead.from_db(reservation=res, slot=slot, shop_id=slot.shop_id) for res, slot in rows]


@router.get("/me/reservations/{reservation_id}", response_model=ReservationRead)
async def get_my_reservation(
    reservation_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> ReservationRead:
    res_repo = SqlAlchemyReservationRepository(session)
    row = await reservation_usecase.get_user_reservation(res_repo, reservation_id=reservation_id, user_id=user_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reservation not found")
    reservation, slot = row
    return ReservationRead.from_db(reservation=reservation, slot=slot, shop_id=slot.shop_id)


@router.post("/me/reservations/{reservation_id}/cancel", response_model=ReservationRead)
async def cancel_reservation(
    reservation_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> ReservationRead:
    res_repo = SqlAlchemyReservationRepository(session)
    async with session.begin():
        try:
            updated, slot, status_value = await reservation_usecase.cancel_reservation(
                res_repo,
                reservation_id=reservation_id,
                user_id=user_id,
            )
        except SlotNotOpenError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reservation not found")

    return ReservationRead.from_db(reservation=updated, slot=slot, shop_id=slot.shop_id)
