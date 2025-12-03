"""Database models for the Hogwarts Winter Feast online restaurant."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import quote_plus

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from flask_login import UserMixin

import bcrypt

PGUSER_RAW = os.getenv("PGUSER", "your user name")
PGPASSWORD_RAW = os.getenv("PGPASSWORD", "your password")
PGHOST = os.getenv("PGHOST", "your host")
PGPORT = os.getenv("PGPORT", "your port")
PGDATABASE = os.getenv("PGDATABASE", "your database name")

PGUSER = quote_plus(PGUSER_RAW)
PGPASSWORD = quote_plus(PGPASSWORD_RAW)

DATABASE_URL = (
    f"postgresql+psycopg2://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
)

engine = create_engine(DATABASE_URL, echo=False, future=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base with helpers."""

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

    def as_short_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "price": f"{self.price:.2f}",
            "weight": self.weight,
        }


class Reservation(Base):
    __tablename__ = "reservation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    type_table: Mapped[str] = mapped_column(String(40), nullable=False)
    guest_name: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    guest_phone: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    guest_email: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    guest_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    guest_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped[Users] = relationship("Users", foreign_keys=[user_id], back_populates="reservations")


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
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    user: Mapped[Users] = relationship("Users", foreign_keys=[user_id], back_populates="orders")


if __name__ == "__main__":
    Base.metadata.create_all(engine)
