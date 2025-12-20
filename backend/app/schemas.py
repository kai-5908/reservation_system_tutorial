from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_serializer

from .models import Reservation, ReservationStatus, Slot, SlotStatus
from .utils.time import JST, utc_naive_to_jst


class SlotAvailability(BaseModel):
    slot_id: int
    shop_id: int
    seat_id: Optional[int]
    starts_at: datetime
    ends_at: datetime
    capacity: int
    status: SlotStatus
    remaining: int

    @field_serializer("starts_at", "ends_at")
    def _ser_datetime(self, dt: datetime) -> str:
        return dt.astimezone(JST).isoformat()


class SlotCreate(BaseModel):
    seat_id: Optional[int] = None
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(ge=1)
    status: SlotStatus = SlotStatus.OPEN


class SlotRead(BaseModel):
    slot_id: int
    shop_id: int
    seat_id: Optional[int]
    starts_at: datetime
    ends_at: datetime
    capacity: int
    status: SlotStatus

    @field_serializer("starts_at", "ends_at")
    def _ser_datetime(self, dt: datetime) -> str:
        return dt.astimezone(JST).isoformat()

    @classmethod
    def from_db(cls, *, slot: Slot) -> "SlotRead":
        return cls(
            slot_id=slot.id,
            shop_id=slot.shop_id,
            seat_id=slot.seat_id,
            starts_at=utc_naive_to_jst(slot.starts_at),
            ends_at=utc_naive_to_jst(slot.ends_at),
            capacity=slot.capacity,
            status=slot.status,
        )


class ReservationCreate(BaseModel):
    slot_id: int
    party_size: int = Field(ge=1)


class ReservationCancel(BaseModel):
    version: Optional[int] = Field(default=None, ge=1)


class ReservationReschedule(BaseModel):
    slot_id: int
    version: Optional[int] = Field(default=None, ge=1)


class ReservationRead(BaseModel):
    reservation_id: int
    slot_id: int
    user_id: int
    party_size: int
    status: ReservationStatus
    version: int
    starts_at: datetime
    ends_at: datetime
    seat_id: Optional[int]
    shop_id: Optional[int] = None

    @field_serializer("starts_at", "ends_at")
    def _ser_datetime(self, dt: datetime) -> str:
        return dt.astimezone(JST).isoformat()

    @classmethod
    def from_db(
        cls,
        *,
        reservation: Reservation,
        slot: Slot,
        shop_id: Optional[int] = None,
    ) -> "ReservationRead":
        return cls(
            reservation_id=reservation.id,
            slot_id=reservation.slot_id,
            user_id=reservation.user_id,
            party_size=reservation.party_size,
            status=reservation.status,
            version=reservation.version,
            starts_at=utc_naive_to_jst(slot.starts_at),
            ends_at=utc_naive_to_jst(slot.ends_at),
            seat_id=slot.seat_id,
            shop_id=shop_id,
        )
