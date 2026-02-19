from __future__ import annotations

import os

from dotenv import load_dotenv
load_dotenv()

from online_restaurant_db import Base, Session, Users, Menu, RestaurantTable, engine

ADMIN_NICKNAME = os.getenv("ADMIN_NICKNAME", "Admin")
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]


ADMIN_EMAIL = "ivanbatulin192@gmail.com"


def ensure_admin_exists() -> None:
    Base.metadata.create_all(engine)

    with Session() as db:
        admin = db.query(Users).filter(Users.nickname == ADMIN_NICKNAME).first()
        if not admin:
            admin = Users(nickname=ADMIN_NICKNAME, email=ADMIN_EMAIL, is_verified=True)
            admin.set_password(ADMIN_PASSWORD)
            db.add(admin)
            db.commit()
        else:
            changed = False
            if not admin.is_verified:
                admin.is_verified = True
                changed = True
            if admin.email != ADMIN_EMAIL:
                admin.email = ADMIN_EMAIL
                changed = True
            if changed:
                db.commit()


def seed_initial_menu() -> None:
    seasonal_items = [
        # бургери
        {
            "name": "Класичний бургер",
            "weight": "320",
            "ingredients": "яловича котлета, чеддер, томат, салат, фірмовий соус",
            "description": "Соковитий бургер з мармуровою яловичиною та розтопленим чеддером.",
            "price": 189.0,
            "category": "Бургери",
        },
        {
            "name": "Подвійний смокі",
            "weight": "420",
            "ingredients": "дві котлети, бекон, халапеньо, копчений соус, цибулеві кільця",
            "description": "Подвійна порція м'яса з копченим ароматом та гострим акцентом.",
            "price": 259.0,
            "category": "Бургери",
        },
        # гарніри
        {
            "name": "Картопля фрі",
            "weight": "200",
            "ingredients": "картопля, сіль, паприка, часникова олія",
            "description": "Хрустка золотиста картопля з паприкою та часниковим маслом.",
            "price": 79.0,
            "category": "Гарніри",
        },
        {
            "name": "Цибулеві кільця",
            "weight": "180",
            "ingredients": "цибуля, паніровка, спеції, соус тартар",
            "description": "Хрусткі кільця у золотистій паніровці з ніжним соусом тартар.",
            "price": 89.0,
            "category": "Гарніри",
        },
        # салати
        {
            "name": "Цезар з куркою",
            "weight": "280",
            "ingredients": "курка гриль, романо, пармезан, крутони, соус цезар",
            "description": "Класичний салат Цезар з соковитою куркою гриль.",
            "price": 169.0,
            "category": "Салати",
        },
        {
            "name": "Грецький салат",
            "weight": "250",
            "ingredients": "томати, огірки, фета, оливки, червона цибуля, оливкова олія",
            "description": "Свіжий середземноморський салат з оригінальною фетою.",
            "price": 139.0,
            "category": "Салати",
        },
        # напої
        {
            "name": "Домашній лимонад",
            "weight": "400",
            "ingredients": "лимон, м'ята, цукровий сироп, газована вода",
            "description": "Освіжаючий лимонад з м'ятою, приготований вручну.",
            "price": 69.0,
            "category": "Напої",
        },
        {
            "name": "Свіжий апельсиновий фреш",
            "weight": "300",
            "ingredients": "апельсини свіжого віджиму",
            "description": "100% натуральний фреш з відбірних апельсинів.",
            "price": 89.0,
            "category": "Напої",
        },
        # молочні коктейлі
        {
            "name": "Полуничний шейк",
            "weight": "350",
            "ingredients": "полуниця, вершкове морозиво, молоко, вершки",
            "description": "Ніжний молочний коктейль з натуральною полуницею.",
            "price": 109.0,
            "category": "Молочні коктейлі",
        },
        {
            "name": "Шоколадний шейк",
            "weight": "350",
            "ingredients": "бельгійський шоколад, морозиво, молоко, какао",
            "description": "Насичений шоколадний коктейль з бельгійським шоколадом.",
            "price": 119.0,
            "category": "Молочні коктейлі",
        },
        # алкоголь
        {
            "name": "Крафтове пиво IPA",
            "weight": "500",
            "ingredients": "солод, хміль, дріжджі, вода",
            "description": "Ароматне крафтове пиво з хмелевою гіркотою та цитрусовими нотами.",
            "price": 99.0,
            "category": "Алкоголь",
        },
        {
            "name": "Апероль Шпріц",
            "weight": "300",
            "ingredients": "апероль, просекко, содова, апельсин",
            "description": "Легкий італійський коктейль з гіркуватим апероль та просекко.",
            "price": 159.0,
            "category": "Алкоголь",
        },
        # десерти
        {
            "name": "Чізкейк Нью-Йорк",
            "weight": "180",
            "ingredients": "вершковий сир, печиво, вершки, ваніль",
            "description": "Класичний вершковий чізкейк з ніжною текстурою.",
            "price": 129.0,
            "category": "Десерти",
        },
        {
            "name": "Тірамісу",
            "weight": "170",
            "ingredients": "маскарпоне, савоярді, еспресо, какао",
            "description": "Італійський десерт з кавовим просоченням та маскарпоне.",
            "price": 139.0,
            "category": "Десерти",
        },
    ]

    with Session() as db:
        for item in seasonal_items:
            exists = db.query(Menu).filter(Menu.name == item["name"]).first()
            if not exists:
                menu_item = Menu(
                    name=item["name"],
                    weight=item["weight"],
                    ingredients=item["ingredients"],
                    description=item["description"],
                    price=item["price"],
                    active=True,
                    file_name=None,
                    category=item.get("category", "Бургери"),
                )
                db.add(menu_item)
        db.commit()


def seed_restaurant_tables() -> None:
    tables = [
        # vip 6 місць
        {"label": "V1", "capacity": 6, "zone": "vip", "has_sofa": True, "x": 27, "y": 36},
        {"label": "V2", "capacity": 6, "zone": "vip", "has_sofa": True, "x": 50, "y": 36},
        {"label": "V3", "capacity": 6, "zone": "vip", "has_sofa": True, "x": 73, "y": 36},
        {"label": "V4", "capacity": 6, "zone": "vip", "has_sofa": True, "x": 27, "y": 56},
        {"label": "V5", "capacity": 6, "zone": "vip", "has_sofa": True, "x": 50, "y": 56},
        {"label": "V6", "capacity": 6, "zone": "vip", "has_sofa": True, "x": 73, "y": 56},
        # 5 місць з диванами
        {"label": "S1", "capacity": 5, "zone": "main", "has_sofa": True, "x": 10, "y": 36},
        {"label": "S2", "capacity": 5, "zone": "main", "has_sofa": True, "x": 10, "y": 56},
        {"label": "S3", "capacity": 5, "zone": "main", "has_sofa": True, "x": 90, "y": 46},
        # 4 місця
        {"label": "A1", "capacity": 4, "zone": "main", "has_sofa": False, "x": 18, "y": 74},
        {"label": "A2", "capacity": 4, "zone": "main", "has_sofa": False, "x": 39, "y": 74},
        {"label": "A3", "capacity": 4, "zone": "main", "has_sofa": False, "x": 61, "y": 74},
        {"label": "A4", "capacity": 4, "zone": "main", "has_sofa": False, "x": 82, "y": 74},
        # 3 місця
        {"label": "C1", "capacity": 3, "zone": "main", "has_sofa": False, "x": 20, "y": 20},
        {"label": "C2", "capacity": 3, "zone": "main", "has_sofa": False, "x": 40, "y": 20},
        {"label": "C3", "capacity": 3, "zone": "main", "has_sofa": False, "x": 60, "y": 20},
        {"label": "C4", "capacity": 3, "zone": "main", "has_sofa": False, "x": 80, "y": 20},
        {"label": "C5", "capacity": 3, "zone": "main", "has_sofa": False, "x": 90, "y": 66},
        # 2 місця
        {"label": "D1", "capacity": 2, "zone": "main", "has_sofa": False, "x": 10, "y": 74},
        {"label": "D2", "capacity": 2, "zone": "main", "has_sofa": False, "x": 25, "y": 88},
        {"label": "D3", "capacity": 2, "zone": "main", "has_sofa": False, "x": 43, "y": 88},
        {"label": "D4", "capacity": 2, "zone": "main", "has_sofa": False, "x": 57, "y": 88},
        {"label": "D5", "capacity": 2, "zone": "main", "has_sofa": False, "x": 75, "y": 88},
        {"label": "D6", "capacity": 2, "zone": "main", "has_sofa": False, "x": 90, "y": 82},
        # бар (не бронюються)
        {"label": "B1",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 22, "y": 8, "bookable": False},
        {"label": "B2",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 27, "y": 8, "bookable": False},
        {"label": "B3",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 32, "y": 8, "bookable": False},
        {"label": "B4",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 37, "y": 8, "bookable": False},
        {"label": "B5",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 42, "y": 8, "bookable": False},
        {"label": "B6",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 47, "y": 8, "bookable": False},
        {"label": "B7",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 53, "y": 8, "bookable": False},
        {"label": "B8",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 58, "y": 8, "bookable": False},
        {"label": "B9",  "capacity": 1, "zone": "bar", "has_sofa": False, "x": 63, "y": 8, "bookable": False},
        {"label": "B10", "capacity": 1, "zone": "bar", "has_sofa": False, "x": 68, "y": 8, "bookable": False},
        {"label": "B11", "capacity": 1, "zone": "bar", "has_sofa": False, "x": 73, "y": 8, "bookable": False},
        {"label": "B12", "capacity": 1, "zone": "bar", "has_sofa": False, "x": 78, "y": 8, "bookable": False},
    ]
    with Session() as db:
        if db.query(RestaurantTable).first():
            return
        for t in tables:
            db.add(RestaurantTable(
                label=t["label"], capacity=t["capacity"], zone=t["zone"],
                has_sofa=t["has_sofa"], x=t["x"], y=t["y"],
                bookable=t.get("bookable", True),
            ))
        db.commit()
