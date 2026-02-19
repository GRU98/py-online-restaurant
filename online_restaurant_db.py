from __future__ import annotations

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Optional
from urllib.parse import quote_plus

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from flask_login import UserMixin

import bcrypt

PGUSER_RAW = os.environ["PGUSER"]
PGPASSWORD_RAW = os.environ["PGPASSWORD"]
PGHOST = os.getenv("PGHOST", "127.0.0.1")
PGPORT = os.getenv("PGPORT", "5432")
PGDATABASE = os.getenv("PGDATABASE", "online_restaurant")

PGUSER = quote_plus(PGUSER_RAW)
PGPASSWORD = quote_plus(PGPASSWORD_RAW)

DATABASE_URL = (
    f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
)

engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):

    def create_db(self) -> None:
        Base.metadata.create_all(engine)

    def drop_db(self) -> None:
        Base.metadata.drop_all(engine)


class Users(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nickname: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    verification_code: Mapped[Optional[str]] = mapped_column(String(6), nullable=True)
    code_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    newsletter_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    balance: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    birthday_discount_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    reservations: Mapped[list["Reservation"]] = relationship(
        "Reservation", foreign_keys="Reservation.user_id", back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Orders"]] = relationship(
        "Orders", foreign_keys="Orders.user_id", back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), self.password.encode("utf-8"))


MENU_CATEGORIES = [
    "Бургери", "Гарніри", "Салати", "Напої",
    "Молочні коктейлі", "Алкоголь", "Десерти",
]


class Menu(Base):
    __tablename__ = "menu"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    weight: Mapped[str] = mapped_column(String(40), nullable=False)
    ingredients: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    file_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, default="Бургери")
    discount_percent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def as_short_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "price": f"{self.price:.2f}",
            "weight": self.weight,
        }


class RestaurantTable(Base):
    __tablename__ = "restaurant_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # e.g. "T1", "T2"
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    zone: Mapped[str] = mapped_column(String(40), nullable=False)  # bar, main, vip
    has_sofa: Mapped[bool] = mapped_column(Boolean, default=False)
    x: Mapped[float] = mapped_column(Float, nullable=False, default=0)  # position on floor plan
    y: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    bookable: Mapped[bool] = mapped_column(Boolean, default=True)

    reservations: Mapped[list["Reservation"]] = relationship("Reservation", back_populates="table", cascade="all, delete-orphan")


RESERVATION_DURATION_HOURS = 5


RESERVATION_PREPAYMENT = 500.0


class Reservation(Base):
    __tablename__ = "reservation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    time_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    table_id: Mapped[int] = mapped_column(ForeignKey("restaurant_tables.id", ondelete="CASCADE"), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    guest_phone: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prepaid: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    user: Mapped[Users] = relationship("Users", foreign_keys=[user_id], back_populates="reservations")
    table: Mapped[RestaurantTable] = relationship("RestaurantTable", back_populates="reservations")


class Orders(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_list: Mapped[Dict[str, int]] = mapped_column(JSONB, nullable=False)
    order_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_address: Mapped[str] = mapped_column(String(255), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped[Users] = relationship("Users", foreign_keys=[user_id], back_populates="orders")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped[Users] = relationship("Users", foreign_keys=[user_id])


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped[Users] = relationship("Users", foreign_keys=[user_id])


if __name__ == "__main__":
    Base.metadata.create_all(engine)
