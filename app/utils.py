from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

import requests
from flask import url_for


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1},
            headers={"User-Agent": "SmakokRestaurant/1.0"},
            timeout=5,
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        pass
    return None


def normalize_price(value: str) -> float:
    return float(Decimal(value).quantize(Decimal("0.01")))


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
_NICK_RE = re.compile(r"^[a-zA-Zа-яА-ЯіІїЇєЄґҐ0-9_\- ]{2,30}$")


def validate_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email)) and len(email) <= 254


def validate_nickname(nick: str) -> bool:
    return bool(_NICK_RE.match(nick))


def menu_item_to_dict(item, admin_nickname: str = "") -> Dict[str, Optional[str]]:
    image_url = (
        url_for("static", filename=f"menu/{item.file_name}")
        if item.file_name
        else None
    )
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "ingredients": item.ingredients,
        "weight": item.weight,
        "price": item.price,
        "active": item.active,
        "imageUrl": image_url,
        "category": item.category or "Бургери",
        "discount_percent": item.discount_percent or 0,
        "original_price": item.original_price,
    }


def order_to_dict(order) -> Dict[str, Any]:
    return {
        "id": order.id,
        "orderTime": order.order_time.isoformat(),
        "totalCost": order.total_cost,
        "orderList": order.order_list,
        "customerName": order.customer_name,
        "customerPhone": order.customer_phone,
        "customerAddress": order.customer_address,
        "paymentMethod": order.payment_method,
        "deliveryNotes": order.delivery_notes,
        "userId": order.user_id,
    }


def reservation_to_dict(reservation) -> Dict[str, Any]:
    return {
        "id": reservation.id,
        "timeStart": reservation.time_start.isoformat(),
        "timeEnd": reservation.time_end.isoformat(),
        "tableId": reservation.table_id,
        "tableLabel": reservation.table.label if reservation.table else "",
        "tableCapacity": reservation.table.capacity if reservation.table else 0,
        "guestName": reservation.guest_name,
        "guestPhone": reservation.guest_phone,
        "userId": reservation.user_id,
    }
