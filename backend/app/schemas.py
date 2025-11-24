from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .models import ReservationStatus, SlotStatus
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

    model_config = {"json_encoders": {datetime: lambda v: v.astimezone(JST).isoformat()}}


class ReservationCreate(BaseModel):
    slot_id: int
    party_size: int = Field(ge=1)


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

    model_config = {"json_encoders": {datetime: lambda v: v.astimezone(JST).isoformat()}}

    @classmethod
    def from_db(cls, *, reservation, slot, shop_id: Optional[int] = None) -> "ReservationRead":
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
