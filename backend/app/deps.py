from typing import AsyncIterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .database import async_session
from .infrastructure.repositories import SqlAlchemyReservationRepository, SqlAlchemySlotRepository
from .models import User
from .utils.auth import decode_access_token


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session() as session:
        yield session


async def get_current_user_id(
    authorization: str | None = Header(default=None, convert_underscores=False),
    session: AsyncSession = Depends(get_session),
) -> int:
    settings = get_settings()
    if not settings.auth_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AUTH_SECRET must be configured",
        )
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ", 1)[1].strip()
    try:
        user_id = decode_access_token(
            token,
            secret=settings.auth_secret,
            algorithms=[settings.auth_algorithm],
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure user exists
    try:
        exists = await session.scalar(select(User.id).where(User.id == user_id))
    except (OperationalError, ProgrammingError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="users table unavailable (apply migrations)",
        ) from exc
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return int(user_id)


async def get_slot_repo(session: AsyncSession = Depends(get_session)) -> SqlAlchemySlotRepository:
    return SqlAlchemySlotRepository(session)


async def get_reservation_repo(
    session: AsyncSession = Depends(get_session),
) -> SqlAlchemyReservationRepository:
    return SqlAlchemyReservationRepository(session)
