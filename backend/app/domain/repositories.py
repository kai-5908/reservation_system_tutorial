from __future__ import annotations

from datetime import datetime
from typing import Iterable, Protocol

from ..models import Reservation, ReservationStatus, Slot, SlotStatus


class SlotRepository(Protocol):
    async def get_for_update(self, slot_id: int) -> Slot | None: ...

    async def create(
        self,
        *,
        shop_id: int,
        seat_id: int | None,
        starts_at: datetime,
        ends_at: datetime,
        capacity: int,
        status: SlotStatus,
    ) -> Slot: ...

    async def list_with_reserved(
        self,
        shop_id: int,
        start: datetime,
        end: datetime,
        seat_id: int | None,
    ) -> Iterable[tuple[Slot, int]]: ...


class ReservationRepository(Protocol):
    async def user_has_active(self, slot_id: int, user_id: int) -> bool: ...

    async def sum_reserved(self, slot_id: int) -> int: ...

    async def get_for_user_for_update(self, reservation_id: int, user_id: int) -> tuple[Reservation, Slot] | None: ...

    async def create(
        self,
        slot_id: int,
        user_id: int,
        party_size: int,
        status: ReservationStatus,
    ) -> Reservation: ...

    async def list_by_user(
        self,
        user_id: int,
        status: ReservationStatus | None = None,
    ) -> list[tuple[Reservation, Slot]]: ...

    async def get_for_user(self, reservation_id: int, user_id: int) -> tuple[Reservation, Slot] | None: ...

    async def cancel(self, reservation: Reservation) -> Reservation: ...

    async def reschedule(self, reservation: Reservation) -> Reservation: ...
