from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session
from .infrastructure.repositories import SqlAlchemyReservationRepository, SqlAlchemySlotRepository


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session


async def get_current_user_id(x_user_id: str | None = Header(default=None)) -> int:
    if x_user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-User-Id header required")
    try:
        return int(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-User-Id") from exc


async def get_slot_repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemySlotRepository:
    return SqlAlchemySlotRepository(session)


async def get_reservation_repo(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyReservationRepository:
    return SqlAlchemyReservationRepository(session)
