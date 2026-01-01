from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import BigInteger, DateTime, Integer, String


class Base(DeclarativeBase):
    pass


class SlotStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    BLOCKED = "blocked"


class ReservationStatus(StrEnum):
    REQUEST_PENDING = "request_pending"
    BOOKED = "booked"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    auth_provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    slots: Mapped[list["Slot"]] = relationship(back_populates="shop")


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="chk_slots_time"),
        CheckConstraint("capacity >= 1", name="chk_slots_capacity"),
        UniqueConstraint("shop_id", "seat_id", "starts_at", "ends_at", name="uq_slots"),
        Index("idx_slots_shop", "shop_id"),
        Index("idx_slots_seat", "seat_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), nullable=False)
    seat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[SlotStatus] = mapped_column(
        Enum(
            SlotStatus,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            native_enum=False,
        ),
        nullable=False,
        default=SlotStatus.OPEN,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    shop: Mapped["Shop"] = relationship(back_populates="slots")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="slot")


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("party_size >= 1", name="chk_res_party_size"),
        UniqueConstraint("user_id", "slot_id", name="uq_res_user_slot"),
        Index("idx_res_slot", "slot_id"),
        Index("idx_res_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(
            ReservationStatus,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
            native_enum=False,
        ),
        nullable=False,
        default=ReservationStatus.REQUEST_PENDING,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)

    slot: Mapped["Slot"] = relationship(back_populates="reservations")
