from typing import List

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_current_user_id, get_session
from ..domain.errors import (
    CancelNotAllowedError,
    CapacityError,
    DuplicateReservationError,
    RescheduleNotAllowedError,
    SlotNotOpenError,
    VersionConflictError,
)
from ..infrastructure.repositories import SqlAlchemyReservationRepository, SqlAlchemySlotRepository
from ..models import ReservationStatus
from ..schemas import ReservationCancel, ReservationCreate, ReservationRead, ReservationReschedule
from ..usecases import reservations as reservation_usecase
from ..utils.audit_log import emit_audit_log

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
            try:
                emit_audit_log(
                    action="reservation.created",
                    initiator="user",
                    reservation_id=reservation.id,
                    slot_id=slot.id,
                    shop_id=slot.shop_id,
                    user_id=user_id,
                    party_size=reservation.party_size,
                    status_from=None,
                    status_to=reservation.status,
                    version=reservation.version,
                )
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="audit log failed"
                ) from exc
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
    status_filter: ReservationStatus | None = Query(default=None, alias="status"),
) -> list[ReservationRead]:
    res_repo = SqlAlchemyReservationRepository(session)
    rows = await reservation_usecase.list_user_reservations(
        res_repo,
        user_id=user_id,
        status=status_filter,
    )
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
    payload: ReservationCancel | None = Body(default=None),
    if_match: str | None = Header(default=None, alias="If-Match"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> ReservationRead:
    version = _extract_version(if_match, payload)
    res_repo = SqlAlchemyReservationRepository(session)
    async with session.begin():
        try:
            updated, slot, previous_status = await reservation_usecase.cancel_reservation(
                res_repo,
                reservation_id=reservation_id,
                user_id=user_id,
                version=version,
            )
            try:
                emit_audit_log(
                    action="reservation.cancelled",
                    initiator="user",
                    reservation_id=updated.id,
                    slot_id=slot.id,
                    shop_id=slot.shop_id,
                    user_id=user_id,
                    party_size=updated.party_size,
                    status_from=getattr(updated, "_previous_status", previous_status),
                    status_to=updated.status,
                    version=updated.version,
                )
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="audit log failed"
                ) from exc
        except SlotNotOpenError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="reservation not found")
        except VersionConflictError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="version conflict")
        except CancelNotAllowedError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="cancellation not allowed within cutoff")

    return ReservationRead.from_db(reservation=updated, slot=slot, shop_id=slot.shop_id)


@router.post("/me/reservations/{reservation_id}/reschedule", response_model=ReservationRead)
async def reschedule_reservation(
    reservation_id: int = Path(..., ge=1),
    payload: ReservationReschedule = Body(...),
    if_match: str | None = Header(default=None, alias="If-Match"),
    session: AsyncSession = Depends(get_session),
    user_id: int = Depends(get_current_user_id),
) -> ReservationRead:
    version = _extract_version(if_match, payload)
    slot_repo = SqlAlchemySlotRepository(session)
    res_repo = SqlAlchemyReservationRepository(session)
    async with session.begin():
        try:
            updated, slot, previous_slot_id = await reservation_usecase.reschedule_reservation(
                slot_repo,
                res_repo,
                reservation_id=reservation_id,
                user_id=user_id,
                new_slot_id=payload.slot_id,
                version=version,
            )
            try:
                emit_audit_log(
                    action="reservation.rescheduled",
                    initiator="user",
                    reservation_id=updated.id,
                    slot_id=slot.id,
                    shop_id=slot.shop_id,
                    user_id=user_id,
                    party_size=updated.party_size,
                    status_from=ReservationStatus.BOOKED,
                    status_to=updated.status,
                    version=updated.version,
                    extra={"slot_id_from": previous_slot_id},
                )
            except RuntimeError as exc:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="audit log failed"
                ) from exc
        except SlotNotOpenError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="slot not available")
        except VersionConflictError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="version conflict")
        except DuplicateReservationError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="duplicate reservation for this slot")
        except CapacityError:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="capacity exceeded")
        except RescheduleNotAllowedError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="reschedule not allowed")

    return ReservationRead.from_db(reservation=updated, slot=slot, shop_id=slot.shop_id)


def _extract_version(if_match: str | None, payload: ReservationCancel | ReservationReschedule | None) -> int:
    """Prefer If-Match; otherwise Body.version. Require version >= 1."""
    if if_match:
        token = if_match.strip()
        if token.startswith("W/"):
            token = token[2:].strip()
        token = token.strip('"')
        try:
            value = int(token)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid If-Match header")
        if value < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version must be >= 1")
        return value
    if payload is not None and payload.version is not None:
        if payload.version < 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version must be >= 1")
        return payload.version
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="version is required")
