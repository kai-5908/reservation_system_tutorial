from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List, Optional, Tuple, cast

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..domain.repositories import ReservationRepository, SlotRepository
from ..models import Reservation, ReservationStatus, Slot, SlotStatus


class SqlAlchemySlotRepository(SlotRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_update(self, slot_id: int) -> Slot | None:
        result = await self.session.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
        return result if isinstance(result, Slot) else None

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
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        slot = Slot(
            shop_id=shop_id,
            seat_id=seat_id,
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=capacity,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self.session.add(slot)
        await self.session.flush()
        return slot

    async def list_with_reserved(
        self,
        shop_id: int,
        start: datetime,
        end: datetime,
        seat_id: int | None,
    ) -> List[Tuple[Slot, int]]:
        stmt: Select[Tuple[Slot, Any]] = (
            select(
                Slot,
                func.coalesce(func.sum(Reservation.party_size), 0).label("reserved"),
            )
            .outerjoin(
                Reservation,
                (Reservation.slot_id == Slot.id) & (Reservation.status != ReservationStatus.CANCELLED),
            )
            .where(
                Slot.shop_id == shop_id,
                Slot.starts_at >= start,
                Slot.ends_at <= end,
            )
            .group_by(Slot.id)
        )
        if seat_id is not None:
            stmt = stmt.where(Slot.seat_id == seat_id)
        rows = await self.session.execute(stmt)
        return [(slot, int(reserved)) for slot, reserved in rows.all()]


class SqlAlchemyReservationRepository(ReservationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def user_has_active(self, slot_id: int, user_id: int) -> bool:
        stmt = select(Reservation.id).where(
            Reservation.slot_id == slot_id,
            Reservation.user_id == user_id,
            Reservation.status != ReservationStatus.CANCELLED,
        )
        return await self.session.scalar(stmt) is not None

    async def sum_reserved(self, slot_id: int) -> int:
        stmt = select(func.coalesce(func.sum(Reservation.party_size), 0)).where(
            Reservation.slot_id == slot_id,
            Reservation.status != ReservationStatus.CANCELLED,
        )
        return int(await self.session.scalar(stmt) or 0)

    async def get_for_user_for_update(self, reservation_id: int, user_id: int) -> Optional[Tuple[Reservation, Slot]]:
        stmt: Select[Tuple[Reservation, Slot]] = (
            select(Reservation, Slot)
            .join(Slot, Reservation.slot_id == Slot.id)
            .where(Reservation.id == reservation_id, Reservation.user_id == user_id)
            .with_for_update()
        )
        row = (await self.session.execute(stmt)).first()
        return cast(Optional[Tuple[Reservation, Slot]], row)

    async def create(
        self,
        slot_id: int,
        user_id: int,
        party_size: int,
        status: ReservationStatus,
    ) -> Reservation:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        reservation = Reservation(
            slot_id=slot_id,
            user_id=user_id,
            party_size=party_size,
            status=status,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self.session.add(reservation)
        await self.session.flush()
        return reservation

    async def list_by_user(self, user_id: int) -> List[Tuple[Reservation, Slot]]:
        stmt: Select[Tuple[Reservation, Slot]] = (
            select(Reservation, Slot)
            .join(Slot, Reservation.slot_id == Slot.id)
            .options(joinedload(Reservation.slot))
            .where(Reservation.user_id == user_id)
        )
        rows = await self.session.execute(stmt)
        return cast(List[Tuple[Reservation, Slot]], list(rows.all()))

    async def get_for_user(self, reservation_id: int, user_id: int) -> Optional[Tuple[Reservation, Slot]]:
        stmt: Select[Tuple[Reservation, Slot]] = (
            select(Reservation, Slot)
            .join(Slot, Reservation.slot_id == Slot.id)
            .where(Reservation.id == reservation_id, Reservation.user_id == user_id)
        )
        row = (await self.session.execute(stmt)).first()
        return cast(Optional[Tuple[Reservation, Slot]], row)

    async def cancel(self, reservation: Reservation) -> Reservation:
        self.session.add(reservation)
        await self.session.flush()
        return reservation

    async def reschedule(self, reservation: Reservation) -> Reservation:
        self.session.add(reservation)
        await self.session.flush()
        return reservation
