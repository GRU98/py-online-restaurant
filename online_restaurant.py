"""Flask application powering the "Шепіт Мандрагори" online restaurant."""
from __future__ import annotations

import math
import os
import uuid
import secrets
from datetime import datetime
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

from online_restaurant_db import Base, Session, Users, Menu, Orders, Reservation, engine
from sqlalchemy.orm import joinedload

APP_NAME = "Шепіт Мандрагори"
ADMIN_NICKNAME = "Admin"
ADMIN_PASSWORD = "123456789"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "menu")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TABLE_NUM: Dict[str, int] = {"1-2": 6, "3-4": 4, "4+": 2}
VENUE_COORDS = (49.9935, 36.2304)  # Kharkiv, French Boulevard area
VENUE_RADIUS_KM = 8.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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


app = Flask(__name__)
app.config["SECRET_KEY"] = "winter_hogsmeade_secret_key"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


def ensure_admin_exists() -> None:
    Base.metadata.create_all(engine)

    with Session() as db:
        admin = db.query(Users).filter(Users.nickname == ADMIN_NICKNAME).first()
        if not admin:
            admin = Users(nickname=ADMIN_NICKNAME, email="admin@hogwarts.feast")
            admin.set_password(ADMIN_PASSWORD)
            db.add(admin)
            db.commit()


def seed_initial_menu() -> None:
    seasonal_items = [
        {
            "name": "Гарячий Гарбузовий Еліксир",
            "weight": "250",
            "ingredients": "гарбузове пюре, вершки, кориця, краплина чараів",
            "description": "Ніжний напій, що зігріває, мов плед у великій залі, з іскрами чарівного морозу.",
            "price": 89.0,
        },
        {
            "name": "Пиріг Сніжної Сови",
            "weight": "140",
            "ingredients": "листкове тісто, журавлина, вершковий крем, льодяні перлини",
            "description": "Хрусткий пиріг із солодко-кислим серцем, натхненний нічними польотами гогвортських сов.",
            "price": 74.0,
        },
        {
            "name": "Льодяний Ростбіф Грифіндору",
            "weight": "320",
            "ingredients": "мармурова яловичина, ялівцевий маринад, карамелізована цибуля",
            "description": "Ситна страва для сміливців: тепла серцевина та холодна ароматна глазур із зимового квасу.",
            "price": 189.0,
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
                )
                db.add(menu_item)
        db.commit()


@login_manager.user_loader
def load_user(user_id: str):
    with Session() as db:
        return db.query(Users).filter(Users.id == int(user_id)).first()


@app.context_processor
def inject_defaults():
    has_reservations = False
    if current_user.is_authenticated:
        with Session() as db:
            has_reservations = (
                db.query(Reservation.id)
                .filter(Reservation.user_id == current_user.id)
                .first()
                is not None
            )
    
    return {
        "app_name": APP_NAME,
        "current_year": datetime.utcnow().year,
        "logged_user": current_user if current_user.is_authenticated else None,
        "is_admin": current_user.is_authenticated and current_user.nickname == ADMIN_NICKNAME
        if current_user.is_authenticated
        else False,
        "has_reservations": has_reservations,
        "csrf_token": session.get("csrf_token"),
    }


@app.before_request
def guarantee_csrf_token() -> None:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)


@app.after_request
def security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


def validate_csrf(form_token: str) -> bool:
    return bool(form_token and session.get("csrf_token") == form_token)


def normalize_price(value: str) -> float:
    return float(Decimal(value).quantize(Decimal("0.01")))


@app.route("/")
@app.route("/home")
def home():
    with Session() as db:
        highlights = (
            db.query(Menu).filter(Menu.active.is_(True)).order_by(Menu.price.asc()).limit(3).all()
        )
    return render_template("home.html", app_name=APP_NAME, highlights=highlights)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if len(password) < 8:
            flash("Пароль має містити щонайменше 8 символів.", "danger")
            return render_template("register.html")

        if not nickname or not email:
            flash("Будь ласка, заповніть усі поля.", "danger")
            return render_template("register.html")

        with Session() as db:
            duplicate = (
                db.query(Users)
                .filter((Users.email == email) | (Users.nickname == nickname))
                .first()
            )
            if duplicate:
                flash("Користувач з такими даними вже існує.", "danger")
                return render_template("register.html")

            user = Users(nickname=nickname, email=email)
            user.set_password(password)
            db.add(user)
            db.commit()
            login_user(user)
            flash("Вітаємо у зимовому банкеті Гоґвортсу!", "success")
            return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        nickname = request.form.get("nickname", "").strip()
        password = request.form.get("password", "")
        persona = request.form.get("persona", "guest")

        if persona == "admin" and (nickname != ADMIN_NICKNAME or password != ADMIN_PASSWORD):
            flash("Для входу як адмін використайте облікові дані Admin / 123456789.", "danger")
            return render_template("login.html")

        if persona == "guest" and nickname == ADMIN_NICKNAME:
            flash("Обліковий запис адміністратора доступний лише в режимі Admin.", "warning")
            return render_template("login.html")

        with Session() as db:
            user = db.query(Users).filter(Users.nickname == nickname).first()
            if not user:
                flash("Користувача не знайдено.", "danger")
                return render_template("login.html")

            if user.check_password(password):
                login_user(user)
                flash("Ви успішно ввійшли до зимового залу!", "success")
                return redirect(url_for("home"))

            flash("Неправильний пароль.", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("До нових зимових зустрічей!", "info")
    return redirect(url_for("home"))


@app.route("/menu")
def menu():
    with Session() as db:
        all_positions = db.query(Menu).filter(Menu.active.is_(True)).all()
    return render_template("menu.html", all_positions=all_positions)


@app.route("/position/<string:name>", methods=["GET", "POST"])
def position(name: str):
    with Session() as db:
        menu_item = db.query(Menu).filter(Menu.active.is_(True), Menu.name == name).first()
        if not menu_item:
            flash("Обрана позиція недоступна.", "danger")
            return redirect(url_for("menu"))

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        amount = request.form.get("num", "1").strip()
        try:
            qty = max(1, int(amount))
        except ValueError:
            qty = 1

        basket = session.get("basket", {})
        basket[menu_item.name] = basket.get(menu_item.name, 0) + qty
        session["basket"] = basket
        flash("Позицію додано до чарівного кошика!", "success")
        return redirect(url_for("position", name=menu_item.name))

    return render_template("position.html", position=menu_item)


@app.route("/test_basket")
def test_basket():
    return session.get("basket", {})


@app.route("/create_order", methods=["GET", "POST"])
@login_required
def create_order():
    basket = session.get("basket", {})
    form_data = {
        "customer_name": current_user.nickname if current_user.is_authenticated else "",
        "customer_phone": "",
        "customer_address": "",
        "delivery_notes": "",
        "payment_method": "card",
    }

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        if not basket:
            flash("Ваш кошик порожній.", "warning")
            return render_template("create_order.html", basket=basket, form_data=form_data)

        form_data.update(
            {
                "customer_name": request.form.get("customer_name", "").strip(),
                "customer_phone": request.form.get("customer_phone", "").strip(),
                "customer_address": request.form.get("customer_address", "").strip(),
                "delivery_notes": request.form.get("delivery_notes", "").strip(),
                "payment_method": request.form.get("payment_method", "card"),
            }
        )

        if not form_data["customer_name"] or not form_data["customer_phone"] or not form_data["customer_address"]:
            flash("Будь ласка, заповніть усі контактні дані.", "danger")
            return render_template("create_order.html", basket=basket, form_data=form_data)

        with Session() as db:
            names = list(basket.keys())
            menu_items = db.query(Menu).filter(Menu.name.in_(names)).all()
            prices = {item.name: Decimal(str(item.price)) for item in menu_items}
            total = sum(prices.get(name, Decimal("0")) * Decimal(str(qty)) for name, qty in basket.items())

            new_order = Orders(
                order_list=basket,
                order_time=datetime.utcnow(),
                total_cost=float(total),
                customer_name=form_data["customer_name"],
                customer_phone=form_data["customer_phone"],
                customer_address=form_data["customer_address"],
                payment_method=form_data["payment_method"],
                delivery_notes=form_data["delivery_notes"] or None,
                user_id=current_user.id,
            )
            db.add(new_order)
            db.commit()
            session.pop("basket", None)
            flash("Замовлення створено!", "success")
            return redirect(url_for("my_order", id=new_order.id))

    return render_template("create_order.html", basket=basket, form_data=form_data)


@app.route("/my_orders")
@login_required
def my_orders():
    with Session() as db:
        orders = db.query(Orders).filter(Orders.user_id == current_user.id).order_by(Orders.order_time.desc()).all()
    return render_template("my_orders.html", orders=orders)


@app.route("/my_order/<int:id>", methods=["GET", "POST"])
@login_required
def my_order(id: int):
    with Session() as db:
        if current_user.nickname == ADMIN_NICKNAME:
            order = db.query(Orders).filter(Orders.id == id).first()
        else:
            order = db.query(Orders).filter(Orders.id == id, Orders.user_id == current_user.id).first()
        if not order:
            flash("Таке замовлення не знайдено.", "danger")
            if current_user.nickname == ADMIN_NICKNAME:
                return redirect(url_for("orders_check"))
            return redirect(url_for("my_orders"))

        menu_items = db.query(Menu).filter(Menu.name.in_(order.order_list.keys())).all()
        price_lookup = {item.name: Decimal(str(item.price)) for item in menu_items}
        total_price = sum(
            price_lookup.get(name, Decimal("0")) * Decimal(str(quantity))
            for name, quantity in order.order_list.items()
        )

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        action = request.form.get("action")
        if action == "cancel":
            with Session() as db:
                if current_user.nickname == ADMIN_NICKNAME:
                    doomed = db.query(Orders).filter(Orders.id == id).first()
                else:
                    doomed = db.query(Orders).filter(Orders.id == id, Orders.user_id == current_user.id).first()
                if doomed:
                    db.delete(doomed)
                    db.commit()
                    flash("Замовлення скасовано.", "info")
            if current_user.nickname == ADMIN_NICKNAME:
                return redirect(url_for("orders_check"))
            return redirect(url_for("my_orders"))

    return render_template("my_order.html", order=order, total_price=float(total_price))


@app.route("/cancel_order/<int:id>", methods=["POST"])
@login_required
def cancel_order(id: int):
    if not validate_csrf(request.form.get("csrf_token")):
        return "Запит заблоковано!", 403

    with Session() as db:
        if current_user.nickname == ADMIN_NICKNAME:
            order = db.query(Orders).filter(Orders.id == id).first()
        else:
            order = db.query(Orders).filter(Orders.id == id, Orders.user_id == current_user.id).first()
        if order:
            db.delete(order)
            db.commit()
            flash("Замовлення скасовано.", "info")
    if current_user.nickname == ADMIN_NICKNAME:
        return redirect(url_for("orders_check"))
    return redirect(url_for("my_orders"))


@app.route("/add_position", methods=["GET", "POST"])
@login_required
def add_position():
    if current_user.nickname != ADMIN_NICKNAME:
        flash("Доступ дозволено лише адміністратору.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        name = request.form.get("name", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "0").strip()
        weight = request.form.get("weight", "").strip()
        image = request.files.get("img")

        if not all([name, ingredients, description, price_raw, weight, image]):
            flash("Будь ласка, заповніть усі поля і додайте ілюстрацію.", "danger")
            return render_template("add_position.html")

        try:
            price = normalize_price(price_raw)
        except Exception:
            flash("Некоректне значення ціни.", "danger")
            return render_template("add_position.html")

        filename = f"{uuid.uuid4()}_{image.filename}"
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image.save(image_path)

        with Session() as db:
            duplicate = db.query(Menu).filter(Menu.name == name).first()
            if duplicate:
                flash("Позиція з такою назвою вже існує.", "warning")
                return render_template("add_position.html")

            menu_item = Menu(
                name=name,
                ingredients=ingredients,
                description=description,
                price=price,
                weight=weight,
                file_name=filename,
                active=True,
            )
            db.add(menu_item)
            db.commit()
            flash("Чарівну страву додано!", "success")

    return render_template("add_position.html")


@app.route("/menu_check", methods=["GET", "POST"])
@login_required
def menu_check():
    if current_user.nickname != ADMIN_NICKNAME:
        flash("Лише адміністратор може перевіряти меню.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        position_id = request.form.get("pos_id")
        action = request.form.get("action")

        if not position_id:
            flash("Не вдалось обробити запит без ідентифікатора.", "danger")
            return redirect(url_for("menu_check"))

        try:
            pos_id_int = int(position_id)
        except ValueError:
            flash("Некоректний ідентифікатор позиції.", "danger")
            return redirect(url_for("menu_check"))

        with Session() as db:
            item = db.query(Menu).filter(Menu.id == pos_id_int).first()
            if item:
                if action == "toggle":
                    item.active = not item.active
                elif action == "delete":
                    if item.file_name:
                        try:
                            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], item.file_name))
                        except FileNotFoundError:
                            pass
                    db.delete(item)
                db.commit()

    with Session() as db:
        all_positions = db.query(Menu).order_by(Menu.id.asc()).all()

    return render_template("check_menu.html", all_positions=all_positions)


@app.route("/orders_check")
@login_required
def orders_check():
    if current_user.nickname != ADMIN_NICKNAME:
        flash("Ця сторінка доступна лише адміністратору.", "danger")
        return redirect(url_for("home"))

    with Session() as db:
        all_orders = (
            db.query(Orders)
            .options(joinedload(Orders.user))
            .order_by(Orders.order_time.desc())
            .all()
        )

    return render_template("orders_check.html", all_orders=all_orders)


@app.route("/all_users")
@login_required
def all_users():
    if current_user.nickname != ADMIN_NICKNAME:
        flash("Ця сторінка лише для адміністратора.", "danger")
        return redirect(url_for("home"))

    with Session() as db:
        users = db.query(Users).order_by(Users.id.asc()).all()
    return render_template("all_users.html", users=users)


@app.route("/reservations_check", methods=["GET", "POST"])
@login_required
def reservations_check():
    if current_user.nickname != ADMIN_NICKNAME:
        flash("Адміністратор перевіряє бронювання.", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        reserv_id = request.form.get("reserv_id")
        with Session() as db:
            reservation = db.query(Reservation).filter(Reservation.id == int(reserv_id)).first()
            if reservation:
                db.delete(reservation)
                db.commit()
                flash("Бронювання видалено.", "info")

    with Session() as db:
        all_reservations = (
            db.query(Reservation)
            .options(joinedload(Reservation.user))
            .order_by(Reservation.time_start.asc())
            .all()
        )

    return render_template("reservations_check.html", all_reservations=all_reservations)


@app.route("/reserved", methods=["GET", "POST"])
@login_required
def reserved():
    message = ""
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        table_type = request.form.get("table_type", "1-2")
        reserved_time_start = request.form.get("time")
        guest_name = request.form.get("customer_name", "").strip()
        guest_phone = request.form.get("customer_phone", "").strip()
        guest_email = request.form.get("customer_email", "").strip()
        guest_notes = request.form.get("notes", "").strip()
        guest_address = request.form.get("customer_address", "").strip()

        if not all([guest_name, guest_phone, guest_email, guest_address, reserved_time_start]):
            message = "Будь ласка, заповніть усі поля, включно з контактними даними та адресою."
        else:
            with Session() as db:
                existing = db.query(Reservation).filter(
                    Reservation.user_id == current_user.id
                ).first()
                taken = db.query(Reservation).filter(
                    Reservation.type_table == table_type
                ).count()
                if existing:
                    message = "Ви вже маєте активну бронь."
                elif taken >= TABLE_NUM.get(table_type, 0):
                    message = "Усі столики цього типу наразі зайняті."
                else:
                    try:
                        booking_time = datetime.fromisoformat(reserved_time_start)
                    except ValueError:
                        message = "Невірний формат дати та часу. Використайте YYYY-MM-DDTHH:MM."
                    else:
                        reservation = Reservation(
                            type_table=table_type,
                            time_start=booking_time,
                            user_id=current_user.id,
                            guest_name=guest_name,
                            guest_phone=guest_phone,
                            guest_email=guest_email,
                            guest_notes=guest_notes,
                            guest_address=guest_address or None,
                        )
                        db.add(reservation)
                        db.commit()
                        message = "Бронювання успішно створено!"

    return render_template("reserved.html", message=message)


@app.route("/my_reservations")
@login_required
def my_reservations():
    with Session() as db:
        reservations = (
            db.query(Reservation)
            .filter(Reservation.user_id == current_user.id)
            .order_by(Reservation.time_start.desc())
            .all()
        )
    return render_template("my_reservations.html", reservations=reservations)


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_):
    flash("Сталася помилка. Спробуйте ще раз.", "danger")
    return redirect(url_for("home"))


if __name__ == "__main__":
    ensure_admin_exists()
    seed_initial_menu()
    app.run(debug=True)
