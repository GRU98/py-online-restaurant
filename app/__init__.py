from __future__ import annotations

import functools
import os
import threading
import uuid
import secrets
import requests
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)

from dotenv import load_dotenv
load_dotenv()

from online_restaurant_db import (
    Base, Session, Users, Menu, Orders, Reservation,
    RestaurantTable, ChatMessage, Review, engine,
    MENU_CATEGORIES, RESERVATION_DURATION_HOURS, RESERVATION_PREPAYMENT,
)
import jwt as pyjwt
from sqlalchemy.orm import joinedload
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename

from app.config import (
    APP_NAME, ADMIN_NICKNAME, ADMIN_PASSWORD,
    UPLOAD_FOLDER, VENUE_COORDS, VENUE_RADIUS_KM,
    ALLOWED_IMAGE_EXTENSIONS,
)
from app.services.emails import (
    send_verification_email, send_discount_email,
    send_password_reset_email, send_invoice_email,
    send_admin_new_order_email, send_admin_new_reservation_email,
    send_birthday_email,
)
from app.services.invoices import build_order_invoice_html, build_reservation_invoice_html
from app.utils import (
    haversine_km, geocode_address, normalize_price,
    validate_email as _validate_email,
    validate_nickname as _validate_nickname,
    menu_item_to_dict, order_to_dict, reservation_to_dict,
)
from app.seed import ensure_admin_exists, seed_initial_menu, seed_restaurant_tables

# батчева розсилка знижок

_pending_discounts: list[Dict[str, Any]] = []
_pending_discounts_lock = threading.Lock()
_discount_sender_started = False

# перевірка днів народження
_birthday_checker_started = False
_last_birthday_check_date = None

NOMINATIM_HEADERS = {"User-Agent": "SmakokRestaurant/1.0"}

# знижки таймінг
def _discount_email_worker() -> None:
    import time
    while True:
        time.sleep(30)  # 5
        with _pending_discounts_lock:
            if not _pending_discounts:
                continue
            batch = list(_pending_discounts)
            _pending_discounts.clear()

        with Session() as db:
            subscribers = db.query(Users.email).filter(
                Users.newsletter_opt_in.is_(True),
                Users.is_verified.is_(True),
                Users.nickname != ADMIN_NICKNAME,
            ).all()

        if not subscribers:
            continue

        for (email,) in subscribers:
            try:
                _send_batch_discount_email(email, batch)
            except Exception as e:
                print(f"[BATCH DISCOUNT EMAIL ERROR] {e}")


def _send_batch_discount_email(to_email: str, discounts: list[dict]) -> None:
    from app.services.emails import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    items_html = ""
    items_text = ""
    for d in discounts:
        items_html += (
            f'<tr>'
            f'<td style="padding:10px 14px;border-bottom:1px solid rgba(198,167,94,0.1);color:#e8e0d0;font-size:14px;">{d["name"]}</td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid rgba(198,167,94,0.1);text-align:right;">'
            f'<span style="text-decoration:line-through;color:#5C5C55;font-size:0.85em;margin-right:8px;">{d["original_price"]:.0f} грн</span>'
            f'<strong style="color:#C6A75E;font-size:1.1em;">{d["new_price"]:.0f} грн</strong></td>'
            f'<td style="padding:10px 14px;border-bottom:1px solid rgba(198,167,94,0.1);text-align:center;">'
            f'<span style="background:rgba(192,57,43,0.15);color:#E74C3C;padding:3px 10px;border-radius:12px;font-weight:700;font-size:0.9em;">-{d["percent"]}%</span></td>'
            f'</tr>'
        )
        items_text += f"  • {d['name']}: {d['original_price']:.0f} → {d['new_price']:.0f} грн (-{d['percent']}%)\n"

    subject = f"СМАКОК — {'Нова знижка' if len(discounts) == 1 else f'{len(discounts)} нових знижок'}!"
    plain = f"Нові знижки в СМАКОК!\n\n{items_text}\nПоспішайте скористатися!"

    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;'
        'background:#08080C;border-radius:20px;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);'
        'padding:36px 32px 28px;text-align:center;border-bottom:1px solid rgba(198,167,94,0.1);">'
        '<div style="font-size:32px;font-weight:800;color:#C6A75E;letter-spacing:4px;">СМАКОК</div>'
        '<div style="color:#5C5C55;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-top:6px;">Преміальний ресторанний досвід</div>'
        '</div>'
        '<div style="padding:32px;">'
        '<p style="font-size:18px;color:#E74C3C;font-weight:700;text-align:center;margin:0 0 20px;">🔥 '
        + ('Нова знижка!' if len(discounts) == 1 else f'{len(discounts)} нових знижок!') +
        '</p>'
        '<table style="width:100%;border-collapse:collapse;">'
        '<thead><tr>'
        '<th style="padding:10px 14px;text-align:left;color:#C6A75E;font-size:12px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid rgba(198,167,94,0.2);">Страва</th>'
        '<th style="padding:10px 14px;text-align:right;color:#C6A75E;font-size:12px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid rgba(198,167,94,0.2);">Ціна</th>'
        '<th style="padding:10px 14px;text-align:center;color:#C6A75E;font-size:12px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid rgba(198,167,94,0.2);">Знижка</th>'
        '</tr></thead>'
        f'<tbody>{items_html}</tbody>'
        '</table>'
        '<p style="text-align:center;margin:24px 0 0;font-size:13px;color:#5C5C55;">Поспішайте скористатися пропозицією!</p>'
        '</div>'
        '<div style="padding:16px 32px;text-align:center;border-top:1px solid rgba(198,167,94,0.08);">'
        '<p style="font-size:11px;color:#3A3A35;margin:0;">© СМАКОК — Харків, Французький бульвар</p>'
        '</div></div>'
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.ehlo(); server.starttls(); server.ehlo()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, to_email, msg.as_string())


def _birthday_checker_worker() -> None:
    """Фоновий процес для перевірки днів народження та відправки привітального email."""
    import time
    global _last_birthday_check_date
    
    while True:
        today = datetime.now().date()
        
        # перевіряємо чи вже перевіряли сьогодні
        if _last_birthday_check_date != today:
            _last_birthday_check_date = today
            
            try:
                with Session() as db:
                    # знаходимо користувачів, у яких сьогодні день народження
                    users_with_birthday = db.query(Users).filter(
                        Users.date_of_birth.isnot(None),
                        Users.is_verified.is_(True),
                        Users.nickname != ADMIN_NICKNAME,
                    ).all()
                    
                    for user in users_with_birthday:
                        if user.date_of_birth.month == today.month and user.date_of_birth.day == today.day:
                            # відправляємо привітальний email (тільки якщо ще не відправляли сьогодні)
                            if not user.birthday_discount_active:
                                user.birthday_discount_active = True  # використовуємо як прапорець "email відправлено сьогодні"
                                
                                threading.Thread(
                                    target=send_birthday_email,
                                    args=(user.email, user.nickname),
                                    daemon=True
                                ).start()
                                
                                print(f"[BIRTHDAY] Sent birthday email to {user.nickname} ({user.email})")
                    
                    # скидаємо прапорець для користувачів, у яких день народження вже минув
                    users_to_reset = db.query(Users).filter(
                        Users.birthday_discount_active.is_(True)
                    ).all()
                    
                    for user in users_to_reset:
                        if user.date_of_birth and not (user.date_of_birth.month == today.month and user.date_of_birth.day == today.day):
                            user.birthday_discount_active = False
                    
                    db.commit()
            
            except Exception as e:
                print(f"[BIRTHDAY CHECKER ERROR] {e}")
        
        time.sleep(3600)  # перевірка кожну годину


def start_discount_sender() -> None:
    global _discount_sender_started
    if _discount_sender_started:
        return
    _discount_sender_started = True
    t = threading.Thread(target=_discount_email_worker, daemon=True)
    t.start()


def start_birthday_checker() -> None:
    """Запускає фоновий процес перевірки днів народження."""
    global _birthday_checker_started
    if _birthday_checker_started:
        return
    _birthday_checker_started = True
    t = threading.Thread(target=_birthday_checker_worker, daemon=True)
    t.start()
    print("[BIRTHDAY CHECKER] Started birthday checker thread")


# flask app

_root = os.path.dirname(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(_root, "templates"),
    static_folder=os.path.join(_root, "static"),
)
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)
app.config["CACHE_TYPE"] = "SimpleCache"
app.config["CACHE_DEFAULT_TIMEOUT"] = 86400

cache = Cache(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per minute"],
                  storage_uri="memory://")

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Будь ласка, увійдіть."
login_manager.init_app(app)


@login_manager.unauthorized_handler
def unauthorized_callback():
    if request.path.startswith("/api/"):
        return jsonify({"error": "Необхідна аутентифікація"}), 401
    flash("Будь ласка, увійдіть.", "warning")
    return redirect(url_for("login"))


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
        "current_year": datetime.now(timezone.utc).year,
        "logged_user": current_user if current_user.is_authenticated else None,
        "is_admin": current_user.is_authenticated and current_user.nickname == ADMIN_NICKNAME
        if current_user.is_authenticated
        else False,
        "has_reservations": has_reservations,
        "csrf_token": session.get("csrf_token"),
    }


def build_session_payload() -> Dict[str, Optional[Dict[str, str]]]:
    user_payload = None
    if current_user.is_authenticated:
        user_payload = {
            "id": current_user.id,
            "nickname": current_user.nickname,
            "email": current_user.email,
            "role": "admin" if current_user.nickname == ADMIN_NICKNAME else "user",
        }

    return {
        "authenticated": current_user.is_authenticated,
        "user": user_payload,
        "hasReservations": inject_defaults()["has_reservations"],
    }


# middleware

@app.before_request
def _before_request_security() -> None:
    session.permanent = True
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)


@app.after_request
def security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if os.getenv("FLASK_ENV") == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https://images.unsplash.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
    return response


# хелпери

def validate_csrf(form_token: str) -> bool:
    return bool(form_token and session.get("csrf_token") == form_token)


def _ensure_csrf_header() -> None:
    token = request.headers.get("X-CSRF-Token")
    if not validate_csrf(token):
        abort(403, description="CSRF token missing or invalid")


def _require_json() -> Dict[str, Any]:
    data = request.get_json(silent=True)
    if data is None:
        abort(400, description="Очікується JSON-тіло запиту")
    return data


def _ensure_authenticated() -> None:
    if not current_user.is_authenticated:
        abort(401, description="Необхідна аутентифікація")


def _ensure_admin() -> None:
    _ensure_authenticated()
    if current_user.nickname != ADMIN_NICKNAME:
        abort(403, description="Доступ дозволено лише адміністратору")


def admin_required(f):
    @functools.wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.nickname != ADMIN_NICKNAME:
            flash("Доступ дозволено лише адміністратору.", "danger")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


# роути — головна / сесія

@app.route("/")
@app.route("/home")
def home():
    with Session() as db:
        highlights = (
            db.query(Menu).filter(Menu.active.is_(True)).order_by(Menu.price.asc()).limit(3).all()
        )
    return render_template("home.html", app_name=APP_NAME, highlights=highlights)


@app.route("/privacy-policy")
def privacy_policy():
    return render_template("legal/privacy_policy.html")


@app.route("/terms-of-use")
def terms_of_use():
    return render_template("legal/terms_of_use.html")


@app.route("/api/session")
def api_session():
    return jsonify(build_session_payload())


@app.route("/api/csrf", methods=["GET"])
def api_csrf_token():
    _before_request_security()
    return jsonify({"csrfToken": session.get("csrf_token")})


# роути — авторизація

@app.route("/api/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def api_login():
    _ensure_csrf_header()
    payload = _require_json()

    nickname = payload.get("nickname", "").strip()
    password = payload.get("password", "")

    if not nickname or not password:
        abort(400, description="Невірні дані")

    with Session() as db:
        user = db.query(Users).filter(Users.nickname == nickname).first()
        if not user or not user.check_password(password):
            abort(401, description="Неправильні облікові дані")

        login_user(user)

    return jsonify(build_session_payload())


@app.route("/api/auth/register", methods=["POST"])
@limiter.limit("5 per minute")
def api_register():
    _ensure_csrf_header()
    payload = _require_json()

    nickname = payload.get("nickname", "").strip()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")

    if not (nickname and email and len(password) >= 8):
        abort(400, description="Перевірте введені дані")
    if not _validate_nickname(nickname):
        abort(400, description="Нікнейм: 2–30 символів, лише літери, цифри, пробіл, _ та -")
    if not _validate_email(email):
        abort(400, description="Некоректний формат email")

    with Session() as db:
        duplicate = (
            db.query(Users)
            .filter((Users.nickname == nickname) | (Users.email == email))
            .first()
        )
        if duplicate:
            abort(409, description="Користувач із такими даними вже існує")

        user = Users(nickname=nickname, email=email)
        user.set_password(password)
        db.add(user)
        db.commit()

        login_user(user)

    return jsonify(build_session_payload())


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    _ensure_csrf_header()
    _ensure_authenticated()
    logout_user()
    return jsonify({"ok": True})


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return jsonify({"error": "CSRF token invalid"}), 403

        nickname = request.form.get("nickname", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if len(password) < 8:
            return jsonify({"error": "Пароль має містити щонайменше 8 символів."}), 400

        if not nickname or not email:
            return jsonify({"error": "Будь ласка, заповніть усі поля."}), 400

        if not _validate_nickname(nickname):
            return jsonify({"error": "Нікнейм: 2–30 символів, лише літери, цифри, пробіл, _ та -"}), 400

        if not _validate_email(email):
            return jsonify({"error": "Некоректний формат email."}), 400

        with Session() as db:
            duplicate = (
                db.query(Users)
                .filter((Users.email == email) | (Users.nickname == nickname))
                .first()
            )
            if duplicate:
                if not duplicate.is_verified and duplicate.email == email:
                    code = str(secrets.randbelow(9000) + 1000)
                    duplicate.verification_code = code
                    duplicate.code_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
                    db.commit()
                    send_verification_email(email, code)
                    return jsonify({"ok": True, "email": email, "message": "Код надіслано повторно."})
                return jsonify({"error": "Користувач з такими даними вже існує."}), 409

            newsletter = request.form.get("newsletter") == "on"
            code = str(secrets.randbelow(9000) + 1000)
            user = Users(
                nickname=nickname,
                email=email,
                verification_code=code,
                code_expiry=datetime.now(timezone.utc) + timedelta(minutes=1),
                is_verified=False,
                newsletter_opt_in=newsletter,
            )
            user.set_password(password)
            db.add(user)
            db.commit()

        send_verification_email(email, code)
        return jsonify({"ok": True, "email": email})

    return render_template("auth/login.html", mode="register")


@app.route("/verify", methods=["POST"])
@limiter.limit("10 per minute")
def verify_email():
    data = request.get_json(silent=True) or request.form
    csrf_tok = data.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not validate_csrf(csrf_tok):
        return jsonify({"error": "CSRF token invalid"}), 403
    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()

    if not email or not code or len(code) != 4:
        return jsonify({"error": "Невірний код."}), 400

    with Session() as db:
        user = db.query(Users).filter(Users.email == email).first()
        if not user:
            return jsonify({"error": "Користувача не знайдено."}), 404

        if user.is_verified:
            return jsonify({"error": "Email вже підтверджено."}), 400

        if user.verification_code != code:
            return jsonify({"error": "Невірний код. Спробуйте ще раз."}), 400

        if user.code_expiry and user.code_expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return jsonify({"error": "Код прострочений. Зареєструйтесь повторно."}), 400

        user.is_verified = True
        user.verification_code = None
        user.code_expiry = None
        db.commit()

        login_user(user)

    return jsonify({"ok": True})


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        nickname = request.form.get("nickname", "").strip()
        password = request.form.get("password", "")

        with Session() as db:
            user = db.query(Users).filter(Users.nickname == nickname).first()
            if not user:
                flash("Користувача не знайдено.", "danger_login")
                return render_template("auth/login.html", mode="login")

            if not user.is_verified and user.nickname != ADMIN_NICKNAME:
                flash("Email не підтверджено. Зареєструйтесь повторно.", "danger_login")
                return render_template("auth/login.html", mode="login")

            if user.check_password(password):
                login_user(user)
                flash("Ви успішно ввійшли!", "success")
                return redirect(url_for("home"))

            flash("Неправильний пароль.", "danger_login")

    return render_template("auth/login.html", mode="login")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    if not validate_csrf(request.form.get("csrf_token")):
        abort(403)
    logout_user()
    flash("Ви вийшли з системи.", "info")
    return redirect(url_for("home"))


# роути — меню

@app.route("/api/menu", methods=["GET"])
def api_menu():
    with Session() as db:
        items = db.query(Menu).filter(Menu.active.is_(True)).order_by(Menu.price.asc()).all()

    return jsonify([menu_item_to_dict(item) for item in items])


@app.route("/menu")
def menu():
    with Session() as db:
        all_positions = db.query(Menu).filter(Menu.active.is_(True)).all()
    return render_template("menu/menu.html", all_positions=all_positions, categories=MENU_CATEGORIES)


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
        flash("Позицію додано до кошика!", "success")
        return redirect(url_for("position", name=menu_item.name))

    return render_template("menu/position.html", position=menu_item)


@app.route("/test_basket")
def test_basket():
    return session.get("basket", {})


# роути — замовлення


def _check_delivery_distance(address: str, coords: Optional[tuple[float, float]] = None):
    if coords is None:
        coords = geocode_address(address)
        if coords is None:
            return None, None
    try:
        lat = float(coords[0])
        lon = float(coords[1])
    except (TypeError, ValueError):
        return None, None
    dist = haversine_km(VENUE_COORDS[0], VENUE_COORDS[1], lat, lon)
    return dist, (lat, lon)


@app.route("/api/address/suggest", methods=["GET"])
@limiter.limit("20 per minute")
def api_address_suggest():

    query = request.args.get("q", "").strip()
    if len(query) < 3:
        return jsonify([])
    
    try:
        url = f"https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 10,
            "countrycodes": "ua",
        }
        response = requests.get(url, params=params, headers=NOMINATIM_HEADERS, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        suggestions = []
        for item in data:
            address_parts = []
            addr = item.get("address", {})
            
            # будуємо читабельну адресу
            road = addr.get("road") or addr.get("pedestrian") or addr.get("footway")
            house = addr.get("house_number")
            suburb = addr.get("suburb") or addr.get("neighbourhood") or addr.get("quarter")
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality")
            state = addr.get("state")
            
            if road:
                if house:
                    address_parts.append(f"{road}, {house}")
                else:
                    address_parts.append(road)
            
            if suburb and suburb != city:
                address_parts.append(suburb)
            
            if city:
                address_parts.append(city)
            elif state:
                address_parts.append(state)
            
            display_name = ", ".join(address_parts) if address_parts else item.get("display_name", "")
            
            suggestions.append({
                "displayName": display_name,
                "lat": float(item.get("lat", 0)),
                "lon": float(item.get("lon", 0)),
            })
        
        return jsonify(suggestions)
    
    except Exception as e:
        print(f"[ADDRESS SUGGEST ERROR] {e}")
        return jsonify([])


@app.route("/api/check_address", methods=["POST"])
@limiter.limit("10 per minute")
def api_check_address():
    _ensure_csrf_header()
    payload = _require_json()
    address = (payload.get("address") or "").strip()
    if not address:
        return jsonify({"ok": False, "error": "Вкажіть адресу"}), 400

    lat_val = payload.get("lat")
    lon_val = payload.get("lon")
    coords_override: Optional[tuple[float, float]] = None
    if lat_val is not None and lon_val is not None:
        try:
            coords_override = (float(lat_val), float(lon_val))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": "Некоректні координати"}), 400

    dist, coords = _check_delivery_distance(address, coords_override)
    if dist is None:
        return jsonify({"ok": False, "error": "Не вдалося визначити адресу. Перевірте правильність."}), 400

    if dist > VENUE_RADIUS_KM:
        return jsonify({
            "ok": False,
            "error": f"Ви не в зоні досяжності доставки ({dist:.1f} км). Максимум — {VENUE_RADIUS_KM:.0f} км.",
            "distance_km": round(dist, 1),
        }), 400

    response = {"ok": True, "distance_km": round(dist, 1)}
    if coords:
        response["lat"] = coords[0]
        response["lon"] = coords[1]
    return jsonify(response)


@app.route("/api/orders", methods=["GET", "POST"])
def api_orders():
    _ensure_authenticated()

    if request.method == "GET":
        with Session() as db:
            query = db.query(Orders).order_by(Orders.order_time.desc())
            if current_user.nickname != ADMIN_NICKNAME:
                query = query.filter(Orders.user_id == current_user.id)
            orders = query.all()
            return jsonify([order_to_dict(order) for order in orders])

    _ensure_csrf_header()
    payload = _require_json()

    items = payload.get("items")
    contact = payload.get("contact", {})

    if not isinstance(items, list) or not items:
        abort(400, description="Додайте позиції до замовлення")

    with Session() as db:
        names = [str(row.get("name")) for row in items if row.get("name")]
        menu_items = (
            db.query(Menu)
            .filter(Menu.active.is_(True), Menu.name.in_(names))
            .all()
        )

        prices = {item.name: Decimal(str(item.price)) for item in menu_items}

        order_list: Dict[str, int] = {}
        for row in items:
            name = row.get("name")
            qty = row.get("quantity", 1)
            if name not in prices:
                abort(400, description=f"Позиція {name} недоступна")
            try:
                qty_int = max(1, int(qty))
            except (TypeError, ValueError):
                abort(400, description="Некоректна кількість")
            order_list[name] = qty_int

        total = sum(prices[name] * Decimal(str(qty)) for name, qty in order_list.items())

        penalty_due = Decimal("0")
        user = db.query(Users).filter(Users.id == current_user.id).first()
        current_balance = Decimal(str(user.balance or 0)) if user else Decimal("0")
        if current_balance < 0:
            penalty_due = -current_balance

        total_with_penalty = total + penalty_due

        customer_name = contact.get("name", current_user.nickname).strip()
        customer_phone = contact.get("phone", "").strip()
        customer_address = contact.get("address", "").strip()
        payment_method = contact.get("payment", "card")
        delivery_notes = contact.get("notes")

        if not (customer_name and customer_phone and customer_address):
            abort(400, description="Заповніть контактні дані")

        dist, _ = _check_delivery_distance(customer_address)
        if dist is None:
            abort(400, description="Не вдалося визначити адресу. Перевірте правильність.")
        if dist > VENUE_RADIUS_KM:
            abort(400, description=f"Ви не в зоні досяжності доставки ({dist:.1f} км). Максимум — {VENUE_RADIUS_KM:.0f} км.")

        order_time = datetime.now(timezone.utc)
        invoice_num = f"INV-{order_time.strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

        new_order = Orders(
            order_list=order_list,
            order_time=order_time,
            total_cost=float(total_with_penalty),
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            payment_method=payment_method,
            delivery_notes=delivery_notes or None,
            invoice_number=invoice_num,
            user_id=current_user.id,
        )
        db.add(new_order)

        if penalty_due > 0 and user:
            user.balance = float(current_balance + penalty_due)
            db.add(user)

        db.commit()

        # Email адміну про нове замовлення
        admin_order_data = {
            "order_id": new_order.id,
            "invoice_number": invoice_num,
            "customer_name": customer_name,
            "customer_email": current_user.email,
            "customer_phone": customer_phone,
            "customer_address": customer_address,
            "payment_method": payment_method,
            "total_cost": float(total_with_penalty),
            "order_list": dict(order_list),
            "delivery_notes": delivery_notes or None,
        }
        threading.Thread(target=send_admin_new_order_email, kwargs=admin_order_data, daemon=True).start()

        cache.delete("order_trends")
        result = order_to_dict(new_order)
        result["penaltyApplied"] = float(penalty_due)
        return jsonify(result), 201


@app.route("/api/orders/<int:order_id>", methods=["GET", "DELETE"])
def api_order_detail(order_id: int):
    _ensure_authenticated()

    with Session() as db:
        query = db.query(Orders).filter(Orders.id == order_id)
        if current_user.nickname != ADMIN_NICKNAME:
            query = query.filter(Orders.user_id == current_user.id)
        order = query.first()

        if not order:
            abort(404, description="Замовлення не знайдено")

        if request.method == "GET":
            return jsonify(order_to_dict(order))

        _ensure_csrf_header()
        db.delete(order)
        db.commit()
        return jsonify({"ok": True})


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
            return render_template("orders/create_order.html", basket=basket, form_data=form_data)

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
            return render_template("orders/create_order.html", basket=basket, form_data=form_data)

        dist, _ = _check_delivery_distance(form_data["customer_address"])
        if dist is None:
            flash("Не вдалося визначити адресу. Перевірте правильність.", "danger")
            return render_template("orders/create_order.html", basket=basket, form_data=form_data)
        if dist > VENUE_RADIUS_KM:
            flash(f"Ви не в зоні досяжності доставки ({dist:.1f} км). Максимум — {VENUE_RADIUS_KM:.0f} км.", "danger")
            return render_template("orders/create_order.html", basket=basket, form_data=form_data)

        with Session() as db:
            names = list(basket.keys())
            menu_items = db.query(Menu).filter(Menu.name.in_(names)).all()
            prices = {item.name: Decimal(str(item.price)) for item in menu_items}
            total = sum(prices.get(name, Decimal("0")) * Decimal(str(qty)) for name, qty in basket.items())

            penalty_due = Decimal("0")
            user = db.query(Users).filter(Users.id == current_user.id).first()
            current_balance = Decimal(str(user.balance or 0)) if user else Decimal("0")
            if current_balance < 0:
                penalty_due = -current_balance

            total_with_penalty = total + penalty_due

            order_time = datetime.now(timezone.utc)
            invoice_num = f"INV-{order_time.strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

            new_order = Orders(
                order_list=basket,
                order_time=order_time,
                total_cost=float(total_with_penalty),
                customer_name=form_data["customer_name"],
                customer_phone=form_data["customer_phone"],
                customer_address=form_data["customer_address"],
                payment_method=form_data["payment_method"],
                delivery_notes=form_data["delivery_notes"] or None,
                invoice_number=invoice_num,
                user_id=current_user.id,
            )
            db.add(new_order)

            if penalty_due > 0 and user:
                user.balance = float(current_balance + penalty_due)
                db.add(user)

            db.commit()

            price_lookup = {item.name: item.price for item in menu_items}
            invoice_html = build_order_invoice_html(new_order, price_lookup)
            user_email = current_user.email
            order_id = new_order.id

            # Дані для email адміну
            admin_order_data = {
                "order_id": new_order.id,
                "invoice_number": invoice_num,
                "customer_name": form_data["customer_name"],
                "customer_email": user_email,
                "customer_phone": form_data["customer_phone"],
                "customer_address": form_data["customer_address"],
                "payment_method": form_data["payment_method"],
                "total_cost": float(total_with_penalty),
                "order_list": dict(basket),
                "delivery_notes": form_data["delivery_notes"] or None,
            }

            def _send():
                send_invoice_email(
                    to_email=user_email,
                    subject=f"{APP_NAME} — Розрахунковий рахунок {invoice_num}",
                    body_text=f"Дякуємо за замовлення #{order_id}!\nУ вкладенні — ваш розрахунковий рахунок.",
                    filename=f"{invoice_num}.html",
                    attachment_html=invoice_html,
                )
                send_admin_new_order_email(**admin_order_data)
            threading.Thread(target=_send, daemon=True).start()

            cache.delete("order_trends")
            session.pop("basket", None)
            flash("Замовлення створено! Рахунок надіслано на вашу пошту.", "success")
            return redirect(url_for("my_order", id=order_id))

    return render_template("orders/create_order.html", basket=basket, form_data=form_data)


@app.route("/my_orders")
@login_required
def my_orders():
    with Session() as db:
        orders = db.query(Orders).filter(Orders.user_id == current_user.id).order_by(Orders.order_time.desc()).all()
    return render_template("orders/my_orders.html", orders=orders)


@app.route("/my_order/<int:id>", methods=["GET", "POST"])
@login_required
def my_order(id: int):
    is_admin = current_user.nickname == ADMIN_NICKNAME

    with Session() as db:
        order_query = db.query(Orders).filter(Orders.id == id)
        if not is_admin:
            order_query = order_query.filter(Orders.user_id == current_user.id)
        order = order_query.first()

        if not order:
            flash("Таке замовлення не знайдено.", "danger")
            return redirect(url_for("orders_check" if is_admin else "my_orders"))

        menu_items = db.query(Menu).filter(Menu.name.in_(order.order_list.keys())).all()
        price_lookup = {item.name: Decimal(str(item.price)) for item in menu_items}
        total_price = sum(
            price_lookup.get(name, Decimal("0")) * Decimal(str(quantity))
            for name, quantity in order.order_list.items()
        )

    owns_order = order.user_id == current_user.id

    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        action = request.form.get("action")
        if action == "cancel":
            with Session() as db:
                doomed_query = db.query(Orders).filter(Orders.id == id)
                if not is_admin:
                    doomed_query = doomed_query.filter(Orders.user_id == current_user.id)
                doomed = doomed_query.first()
                if doomed:
                    db.delete(doomed)
                    db.commit()
                    flash("Замовлення скасовано.", "info")
            if is_admin and not owns_order:
                return redirect(url_for("orders_check"))
            return redirect(url_for("my_orders"))

    return render_template("orders/my_order.html", order=order, total_price=float(total_price))


@app.route("/cancel_order/<int:id>", methods=["POST"])
@login_required
def cancel_order(id: int):
    if not validate_csrf(request.form.get("csrf_token")):
        return "Запит заблоковано!", 403

    with Session() as db:
        is_admin = current_user.nickname == ADMIN_NICKNAME
        order_query = db.query(Orders).filter(Orders.id == id)
        if not is_admin:
            order_query = order_query.filter(Orders.user_id == current_user.id)
        order = order_query.first()
        if order:
            owns_order = order.user_id == current_user.id
            db.delete(order)
            db.commit()
            flash("Замовлення скасовано.", "info")
    if is_admin and not order:
        flash("Замовлення не знайдено або не належить вам.", "warning")
    if is_admin and order and not owns_order:
        return redirect(url_for("orders_check"))
    return redirect(url_for("my_orders"))


@app.route("/invoice/<int:order_id>")
@login_required
def invoice(order_id: int):
    with Session() as db:
        order = db.query(Orders).filter(Orders.id == order_id).first()
        if not order:
            abort(404)
        is_admin = current_user.nickname == ADMIN_NICKNAME
        if not is_admin and order.user_id != current_user.id:
            abort(403)

        menu_items = db.query(Menu).filter(Menu.name.in_(order.order_list.keys())).all()
        price_lookup = {item.name: item.price for item in menu_items}

    html = build_order_invoice_html(order, price_lookup)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


# роути — бронювання

@app.route("/api/tables", methods=["GET"])
def api_tables():
    with Session() as db:
        tables = db.query(RestaurantTable).order_by(RestaurantTable.id).all()
        return jsonify([{
            "id": t.id, "label": t.label, "capacity": t.capacity,
            "zone": t.zone, "hasSofa": t.has_sofa,
            "x": t.x, "y": t.y, "bookable": t.bookable,
        } for t in tables])


@app.route("/api/tables/availability", methods=["GET"])
def api_tables_availability():
    date_str = request.args.get("date")
    time_str = request.args.get("time")
    if not date_str or not time_str:
        abort(400, description="Вкажіть дату та час")
    try:
        booking_start = datetime.fromisoformat(f"{date_str}T{time_str}")
        booking_end = booking_start + timedelta(hours=RESERVATION_DURATION_HOURS)
    except ValueError:
        abort(400, description="Невірний формат дати/часу")

    with Session() as db:
        booked_table_ids = (
            db.query(Reservation.table_id)
            .filter(
                Reservation.time_start < booking_end,
                Reservation.time_end > booking_start,
                Reservation.cancelled.is_(False),
            )
            .all()
        )
        booked_ids = {r[0] for r in booked_table_ids}
    return jsonify({"bookedTableIds": list(booked_ids)})


@app.route("/api/reservations", methods=["GET", "POST"])
def api_reservations():
    _ensure_authenticated()

    if request.method == "GET":
        with Session() as db:
            query = db.query(Reservation).options(joinedload(Reservation.table)).order_by(Reservation.time_start.desc())
            if current_user.nickname != ADMIN_NICKNAME:
                query = query.filter(Reservation.user_id == current_user.id)
            reservations = query.all()
        return jsonify([reservation_to_dict(res) for res in reservations])

    _ensure_csrf_header()
    payload = _require_json()

    table_id = payload.get("tableId")
    time_start_str = payload.get("timeStart")
    guest_name = payload.get("guestName", current_user.nickname).strip()
    guest_phone = payload.get("guestPhone", "").strip()

    if not (table_id and time_start_str and guest_name and guest_phone):
        abort(400, description="Заповніть усі необхідні поля")

    try:
        booking_start = datetime.fromisoformat(time_start_str)
        booking_end = booking_start + timedelta(hours=RESERVATION_DURATION_HOURS)
    except ValueError:
        abort(400, description="Невірний формат дати та часу")

    with Session() as db:
        table = db.query(RestaurantTable).filter(RestaurantTable.id == table_id).first()
        if not table or not table.bookable:
            abort(400, description="Цей столик не можна забронювати")

        conflict = db.query(Reservation).filter(
            Reservation.table_id == table_id,
            Reservation.time_start < booking_end,
            Reservation.time_end > booking_start,
            Reservation.cancelled.is_(False),
        ).first()
        if conflict:
            abort(409, description="Цей столик вже зайнятий на обраний час")

        reservation = Reservation(
            table_id=table_id,
            time_start=booking_start,
            time_end=booking_end,
            user_id=current_user.id,
            guest_name=guest_name,
            guest_phone=guest_phone,
            prepaid=RESERVATION_PREPAYMENT,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        reservation.table  # load relationship

        invoice_html = build_reservation_invoice_html(reservation)
        user_email = current_user.email
        user_nickname = current_user.nickname
        res_id = reservation.id
        table_label = table.label
        table_capacity = table.capacity
        time_start_fmt = booking_start.strftime("%d.%m.%Y %H:%M")
        time_end_fmt = booking_end.strftime("%H:%M")

        # Дані для email адміну
        admin_res_data = {
            "reservation_id": res_id,
            "guest_name": guest_name,
            "guest_phone": guest_phone,
            "user_email": user_email,
            "user_nickname": user_nickname,
            "table_label": table_label,
            "table_capacity": table_capacity,
            "time_start": time_start_fmt,
            "time_end": time_end_fmt,
            "prepaid": RESERVATION_PREPAYMENT,
        }

        def _send_res():
            send_invoice_email(
                to_email=user_email,
                subject=f"{APP_NAME} — Рахунок за бронювання #{res_id}",
                body_text=f"Дякуємо за бронювання!\nПередоплата: {RESERVATION_PREPAYMENT:.0f} грн.\nУ вкладенні — ваш розрахунковий рахунок.",
                filename=f"RES-{res_id}.html",
                attachment_html=invoice_html,
            )
            send_admin_new_reservation_email(**admin_res_data)
        threading.Thread(target=_send_res, daemon=True).start()

        result = reservation_to_dict(reservation)
        result["prepaid"] = RESERVATION_PREPAYMENT
        return jsonify(result), 201


@app.route("/api/reservations/<int:reservation_id>", methods=["DELETE"])
def api_reservation_cancel_delete(reservation_id: int):
    _ensure_authenticated()
    _ensure_csrf_header()

    with Session() as db:
        query = db.query(Reservation).filter(Reservation.id == reservation_id)
        if current_user.nickname != ADMIN_NICKNAME:
            query = query.filter(Reservation.user_id == current_user.id)
        reservation = query.first()

        if not reservation:
            abort(404, description="Бронювання не знайдено")

        db.delete(reservation)
        db.commit()
        return jsonify({"ok": True})


@app.route("/api/reservations/<int:reservation_id>/cancel", methods=["POST"])
@login_required
def api_reservation_cancel(reservation_id: int):
    _ensure_csrf_header()

    with Session() as db:
        reservation = (
            db.query(Reservation)
            .filter(Reservation.id == reservation_id, Reservation.user_id == current_user.id, Reservation.cancelled.is_(False))
            .first()
        )
        if not reservation:
            return jsonify({"error": "Бронювання не знайдено"}), 404

        now = datetime.now(timezone.utc)
        booking_start = reservation.time_start
        if booking_start.tzinfo is None:
            booking_start = booking_start.replace(tzinfo=timezone.utc)
        diff = booking_start - now
        free_cancel = diff.total_seconds() >= 86400  # 24 hours

        reservation.cancelled = True

        if free_cancel:
            pass
        else:
            user = db.query(Users).filter(Users.id == current_user.id).first()
            if user:
                user.balance = (user.balance or 0) - RESERVATION_PREPAYMENT
                db.add(user)

        db.add(reservation)
        db.commit()

        return jsonify({
            "ok": True,
            "refunded": free_cancel,
            "penalty": 0 if free_cancel else RESERVATION_PREPAYMENT,
        })


@app.route("/invoice/reservation/<int:res_id>")
@login_required
def invoice_reservation(res_id: int):
    with Session() as db:
        reservation = (
            db.query(Reservation)
            .options(joinedload(Reservation.table))
            .filter(Reservation.id == res_id)
            .first()
        )
        if not reservation:
            abort(404)
        is_admin = current_user.nickname == ADMIN_NICKNAME
        if not is_admin and reservation.user_id != current_user.id:
            abort(403)

    html = build_reservation_invoice_html(reservation)
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/reserved")
@login_required
def reserved():
    return render_template("reservations/reserved.html", duration_hours=RESERVATION_DURATION_HOURS)


@app.route("/my_reservations")
@login_required
def my_reservations():
    with Session() as db:
        reservations = (
            db.query(Reservation)
            .options(joinedload(Reservation.table))
            .filter(Reservation.user_id == current_user.id)
            .order_by(Reservation.time_start.desc())
            .all()
        )
    return render_template("reservations/my_reservations.html", reservations=reservations)


# роути — адмін

@app.route("/api/admin/menu", methods=["GET", "POST"])
def api_admin_menu():
    _ensure_admin()

    if request.method == "GET":
        with Session() as db:
            items = db.query(Menu).order_by(Menu.id.asc()).all()
            return jsonify([menu_item_to_dict(item) for item in items])

    _ensure_csrf_header()
    payload = _require_json()

    name = payload.get("name", "").strip()
    description = payload.get("description", "").strip()
    ingredients = payload.get("ingredients", "").strip()
    weight = payload.get("weight", "").strip()
    price_raw = payload.get("price")

    if not all([name, description, ingredients, weight]) or price_raw is None:
        abort(400, description="Укажіть усі поля")

    try:
        price = normalize_price(str(price_raw))
    except Exception:
        abort(400, description="Некоректна ціна")

    with Session() as db:
        duplicate = db.query(Menu).filter(Menu.name == name).first()
        if duplicate:
            abort(409, description="Страва з такою назвою вже існує")

        category = payload.get("category", "Бургери").strip()
        if category not in MENU_CATEGORIES:
            category = "Бургери"

        menu_item = Menu(
            name=name,
            description=description,
            ingredients=ingredients,
            weight=weight,
            price=price,
            active=True,
            file_name=None,
            category=category,
        )
        db.add(menu_item)
        db.commit()
        return jsonify(menu_item_to_dict(menu_item)), 201


@app.route("/api/admin/menu/<int:item_id>", methods=["PATCH", "DELETE"])
def api_admin_menu_item(item_id: int):
    _ensure_admin()

    with Session() as db:
        item = db.query(Menu).filter(Menu.id == item_id).first()
        if not item:
            abort(404, description="Позицію не знайдено")

        if request.method == "PATCH":
            _ensure_csrf_header()
            payload = _require_json()
            action = payload.get("action")

            if action == "toggle":
                item.active = not item.active
            elif action == "update":
                for field in ["name", "description", "ingredients", "weight"]:
                    if field in payload:
                        setattr(item, field, str(payload[field]).strip())
                if "category" in payload:
                    cat = str(payload["category"]).strip()
                    if cat in MENU_CATEGORIES:
                        item.category = cat
                if "price" in payload:
                    try:
                        item.price = normalize_price(str(payload["price"]))
                    except Exception:
                        abort(400, description="Некоректна ціна")
            else:
                abort(400, description="Невідома дія")

            db.commit()
            return jsonify(menu_item_to_dict(item))

        _ensure_csrf_header()
        if item.file_name:
            try:
                os.remove(os.path.join(app.config["UPLOAD_FOLDER"], item.file_name))
            except FileNotFoundError:
                pass
        db.delete(item)
        db.commit()
        return jsonify({"ok": True})


@app.route("/api/admin/users", methods=["GET"])
def api_admin_users():
    _ensure_admin()

    with Session() as db:
        users = (
            db.query(Users)
            .order_by(Users.id.asc())
            .all()
        )

    def user_to_dict(user: Users) -> Dict[str, Any]:
        return {
            "id": user.id,
            "nickname": user.nickname,
            "email": user.email,
            "reservations": len(user.reservations),
            "orders": len(user.orders),
            "isAdmin": user.nickname == ADMIN_NICKNAME,
        }

    return jsonify([user_to_dict(user) for user in users])


@app.route("/add_position", methods=["GET", "POST"])
@admin_required
def add_position():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        name = request.form.get("name", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        description = request.form.get("description", "").strip()
        price_raw = request.form.get("price", "0").strip()
        weight = request.form.get("weight", "").strip()
        category = request.form.get("category", "Бургери").strip()
        image = request.files.get("img")

        if category not in MENU_CATEGORIES:
            category = "Бургери"

        if not all([name, ingredients, description, price_raw, weight, image]):
            flash("Будь ласка, заповніть усі поля і додайте ілюстрацію.", "danger")
            return render_template("admin/add_position.html", categories=MENU_CATEGORIES)

        try:
            price = normalize_price(price_raw)
        except Exception:
            flash("Некоректне значення ціни.", "danger")
            return render_template("admin/add_position.html", categories=MENU_CATEGORIES)

        orig_name = secure_filename(image.filename)
        ext = orig_name.rsplit(".", 1)[-1].lower() if "." in orig_name else ""
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            flash("Дозволені формати: png, jpg, jpeg, gif, webp.", "danger")
            return render_template("admin/add_position.html", categories=MENU_CATEGORIES)

        filename = f"{uuid.uuid4()}.{ext}"
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image.save(image_path)

        with Session() as db:
            duplicate = db.query(Menu).filter(Menu.name == name).first()
            if duplicate:
                flash("Позиція з такою назвою вже існує.", "warning")
                return render_template("admin/add_position.html", categories=MENU_CATEGORIES)

            menu_item = Menu(
                name=name,
                ingredients=ingredients,
                description=description,
                price=price,
                weight=weight,
                file_name=filename,
                active=True,
                category=category,
            )
            db.add(menu_item)
            db.commit()
            flash("Страву додано!", "success")

    return render_template("admin/add_position.html", categories=MENU_CATEGORIES)


@app.route("/menu_check", methods=["GET", "POST"])
@admin_required
def menu_check():

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

    return render_template("admin/check_menu.html", all_positions=all_positions)


@app.route("/edit_position/<int:pos_id>", methods=["GET", "POST"])
@admin_required
def edit_position(pos_id: int):
    with Session() as db:
        item = db.query(Menu).filter(Menu.id == pos_id).first()
        if not item:
            flash("Позицію не знайдено.", "danger")
            return redirect(url_for("menu_check"))

        if request.method == "POST":
            if not validate_csrf(request.form.get("csrf_token")):
                return "Запит заблоковано!", 403

            name = request.form.get("name", "").strip()
            ingredients = request.form.get("ingredients", "").strip()
            description = request.form.get("description", "").strip()
            price_raw = request.form.get("price", "0").strip()
            weight = request.form.get("weight", "").strip()
            category = request.form.get("category", "Бургери").strip()
            image = request.files.get("img")

            if category not in MENU_CATEGORIES:
                category = "Бургери"

            if not all([name, ingredients, description, price_raw, weight]):
                flash("Будь ласка, заповніть усі обов'язкові поля.", "danger")
                return render_template("admin/edit_position.html", item=item, categories=MENU_CATEGORIES)

            try:
                price = normalize_price(price_raw)
            except Exception:
                flash("Некоректне значення ціни.", "danger")
                return render_template("admin/edit_position.html", item=item, categories=MENU_CATEGORIES)

            if name != item.name:
                duplicate = db.query(Menu).filter(Menu.name == name, Menu.id != pos_id).first()
                if duplicate:
                    flash("Позиція з такою назвою вже існує.", "warning")
                    return render_template("admin/edit_position.html", item=item, categories=MENU_CATEGORIES)

            item.name = name
            item.ingredients = ingredients
            item.description = description
            item.price = price
            item.weight = weight
            item.category = category

            if image and image.filename:
                orig_name = secure_filename(image.filename)
                ext = orig_name.rsplit(".", 1)[-1].lower() if "." in orig_name else ""
                if ext not in ALLOWED_IMAGE_EXTENSIONS:
                    flash("Дозволені формати: png, jpg, jpeg, gif, webp.", "danger")
                    return render_template("admin/edit_position.html", item=item, categories=MENU_CATEGORIES)

                if item.file_name:
                    try:
                        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], item.file_name))
                    except FileNotFoundError:
                        pass

                filename = f"{uuid.uuid4()}.{ext}"
                image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                item.file_name = filename

            db.commit()
            flash("Позицію оновлено!", "success")
            return redirect(url_for("menu_check"))

    return render_template("admin/edit_position.html", item=item, categories=MENU_CATEGORIES)


@app.route("/orders_check")
@admin_required
def orders_check():
    with Session() as db:
        all_orders = (
            db.query(Orders)
            .options(joinedload(Orders.user))
            .order_by(Orders.order_time.desc())
            .all()
        )

    return render_template("admin/orders_check.html", all_orders=all_orders)


@app.route("/all_users")
@admin_required
def all_users():
    with Session() as db:
        users = db.query(Users).order_by(Users.id.asc()).all()
    return render_template("admin/all_users.html", users=users)


@app.route("/reservations_check", methods=["GET", "POST"])
@admin_required
def reservations_check():
    if request.method == "POST":
        if not validate_csrf(request.form.get("csrf_token")):
            return "Запит заблоковано!", 403

        reserv_id = request.form.get("reserv_id")
        try:
            reserv_id_int = int(reserv_id)
        except (TypeError, ValueError):
            flash("Некоректний ідентифікатор.", "danger")
            return redirect(url_for("reservations_check"))
        with Session() as db:
            reservation = db.query(Reservation).filter(Reservation.id == reserv_id_int).first()
            if reservation:
                db.delete(reservation)
                db.commit()
                flash("Бронювання видалено.", "info")

    with Session() as db:
        all_reservations = (
            db.query(Reservation)
            .options(joinedload(Reservation.user), joinedload(Reservation.table))
            .order_by(Reservation.time_start.asc())
            .all()
        )

    return render_template("admin/reservations_check.html", all_reservations=all_reservations)


@app.route("/api/admin/menu/<int:item_id>/discount", methods=["POST"])
def api_admin_discount(item_id: int):
    _ensure_admin()
    _ensure_csrf_header()
    payload = _require_json()
    percent = payload.get("percent", 0)
    try:
        percent = int(percent)
    except (TypeError, ValueError):
        abort(400, description="Некоректний відсоток")
    if percent < 0 or percent > 99:
        abort(400, description="Відсоток має бути від 0 до 99")

    with Session() as db:
        item = db.query(Menu).filter(Menu.id == item_id).first()
        if not item:
            abort(404, description="Позицію не знайдено")

        if percent == 0:
            if item.original_price:
                item.price = item.original_price
            item.discount_percent = 0
            item.original_price = None
            db.commit()
            return jsonify(menu_item_to_dict(item))

        if not item.original_price:
            item.original_price = item.price

        new_price = round(item.original_price * (1 - percent / 100), 2)
        item.discount_percent = percent
        item.price = new_price
        db.commit()

        _pending_discounts_lock.acquire()
        try:
            _pending_discounts.append({
                "name": item.name,
                "original_price": item.original_price,
                "new_price": new_price,
                "percent": percent,
            })
        finally:
            _pending_discounts_lock.release()

        return jsonify(menu_item_to_dict(item))


@app.route("/api/admin/clear-trends-cache", methods=["POST"])
def api_clear_trends_cache():
    _ensure_admin()
    _ensure_csrf_header()
    cache.delete("order_trends")
    return jsonify({"ok": True})


# обробка помилок

@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(_):
    flash("Сталася помилка. Спробуйте ще раз.", "danger")
    return redirect(url_for("home"))


# jwt

JWT_SECRET = os.getenv("JWT_SECRET", app.config["SECRET_KEY"] + "_jwt")
JWT_ALGORITHM = "HS256"
JWT_EXP_HOURS = 24


def generate_jwt(user_id: int, nickname: str) -> str:
    payload = {
        "user_id": user_id,
        "nickname": nickname,
        "exp": datetime.now(timezone.utc).timestamp() + JWT_EXP_HOURS * 3600,
        "iat": datetime.now(timezone.utc).timestamp(),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None


@app.after_request
def attach_jwt_after_login(response):
    if current_user.is_authenticated:
        token = generate_jwt(current_user.id, current_user.nickname)
        response.set_cookie("jwt_token", token, httponly=True, samesite="Strict",
                            max_age=JWT_EXP_HOURS * 3600,
                            secure=os.getenv("FLASK_ENV") == "production")
    elif "jwt_token" in request.cookies:
        response.delete_cookie("jwt_token")
    return response


@app.context_processor
def inject_jwt():
    return {"jwt_token_value": ""}


def get_user_from_jwt() -> Optional[Users]:
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.cookies.get("jwt_token", "")
    if token:
        data = decode_jwt(token)
        if data:
            with Session() as db:
                user = db.query(Users).filter(Users.id == data["user_id"]).first()
                if user:
                    db.expunge(user)
                    return user
    # Fallback
    if current_user.is_authenticated:
        with Session() as db:
            user = db.query(Users).filter(Users.id == current_user.id).first()
            if user:
                db.expunge(user)
                return user
    return None


# роути чата

@app.route("/api/chat/unread", methods=["GET"])
def api_chat_unread():
    user = get_user_from_jwt()
    if not user:
        return jsonify({"count": 0})
    is_admin = user.nickname == ADMIN_NICKNAME
    with Session() as db:
        if is_admin:
            count = db.query(ChatMessage).filter(
                ChatMessage.is_admin.is_(False),
                ChatMessage.read.is_(False),
            ).count()
        else:
            count = db.query(ChatMessage).filter(
                ChatMessage.user_id == user.id,
                ChatMessage.is_admin.is_(True),
                ChatMessage.read.is_(False),
            ).count()
    return jsonify({"count": count})


@app.route("/api/chat/users", methods=["GET"])
def api_chat_users():
    user = get_user_from_jwt()
    if not user or user.nickname != ADMIN_NICKNAME:
        return jsonify({"error": "Forbidden"}), 403
    with Session() as db:
        from sqlalchemy import func, case, and_
        user_chats = (
            db.query(
                ChatMessage.user_id,
                Users.nickname,
                func.max(ChatMessage.created_at).label("last_msg"),
                func.sum(case((and_(ChatMessage.read.is_(False), ChatMessage.is_admin.is_(False)), 1), else_=0)).label("unread"),
            )
            .join(Users, Users.id == ChatMessage.user_id)
            .filter(ChatMessage.user_id != user.id)
            .group_by(ChatMessage.user_id, Users.nickname)
            .order_by(func.max(ChatMessage.created_at).desc())
            .all()
        )
        result = []
        for row in user_chats:
            result.append({
                "user_id": row.user_id,
                "nickname": row.nickname,
                "last_msg": row.last_msg.strftime("%d.%m %H:%M") if row.last_msg else "",
                "unread": int(row.unread or 0),
            })
    return jsonify(result)


@app.route("/api/chat/<int:target_user_id>", methods=["GET"])
def api_chat_get(target_user_id):
    user = get_user_from_jwt()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    is_admin = user.nickname == ADMIN_NICKNAME
    if not is_admin and target_user_id != user.id:
        return jsonify({"error": "Forbidden"}), 403
    with Session() as db:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.user_id == target_user_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(100)
            .all()
        )
        # Mark messages as read
        if is_admin:
            db.query(ChatMessage).filter(
                ChatMessage.user_id == target_user_id,
                ChatMessage.is_admin.is_(False),
                ChatMessage.read.is_(False),
            ).update({"read": True})
        else:
            db.query(ChatMessage).filter(
                ChatMessage.user_id == target_user_id,
                ChatMessage.is_admin.is_(True),
                ChatMessage.read.is_(False),
            ).update({"read": True})
        db.commit()
        result = []
        for m in messages:
            result.append({
                "id": m.id,
                "text": m.text,
                "is_admin": m.is_admin,
                "created_at": m.created_at.strftime("%d.%m %H:%M"),
            })
    return jsonify(result)


@app.route("/api/chat/<int:target_user_id>", methods=["POST"])
def api_chat_post(target_user_id):
    _ensure_csrf_header()
    user = get_user_from_jwt()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    is_admin = user.nickname == ADMIN_NICKNAME
    if not is_admin and target_user_id != user.id:
        return jsonify({"error": "Forbidden"}), 403
    if is_admin and target_user_id == user.id:
        return jsonify({"error": "Admin cannot message self"}), 400
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text or len(text) > 1000:
        return jsonify({"error": "Invalid message"}), 400
    with Session() as db:
        msg = ChatMessage(
            text=text,
            is_admin=is_admin,
            user_id=target_user_id,
            read=False,
        )
        db.add(msg)
        db.commit()
        return jsonify({
            "id": msg.id,
            "text": msg.text,
            "is_admin": msg.is_admin,
            "created_at": msg.created_at.strftime("%d.%m %H:%M"),
        }), 201


@app.route("/api/chat/<int:target_user_id>/close", methods=["POST"])
def api_chat_close(target_user_id):
    _ensure_csrf_header()
    user = get_user_from_jwt()
    if not user or user.nickname != ADMIN_NICKNAME:
        return jsonify({"error": "Forbidden"}), 403
    with Session() as db:
        db.query(ChatMessage).filter(ChatMessage.user_id == target_user_id).delete()
        db.commit()
    return jsonify({"ok": True})


# роути — відгуки

@app.route("/reviews")
def reviews_page():
    with Session() as db:
        all_reviews = (
            db.query(Review)
            .options(joinedload(Review.user))
            .order_by(Review.created_at.desc())
            .all()
        )
        avg_stars = 0
        if all_reviews:
            avg_stars = round(sum(r.stars for r in all_reviews) / len(all_reviews), 1)
    return render_template("reviews.html", reviews=all_reviews, avg_stars=avg_stars)


@app.route("/api/reviews", methods=["GET"])
def api_reviews_get():
    with Session() as db:
        all_reviews = (
            db.query(Review)
            .options(joinedload(Review.user))
            .order_by(Review.created_at.desc())
            .all()
        )
        result = []
        for r in all_reviews:
            result.append({
                "id": r.id,
                "text": r.text,
                "stars": r.stars,
                "created_at": r.created_at.strftime("%d.%m.%Y"),
                "user": r.user.nickname,
            })
    return jsonify(result)


@app.route("/api/reviews", methods=["POST"])
def api_reviews_post():
    _ensure_csrf_header()
    user = get_user_from_jwt()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.nickname == ADMIN_NICKNAME:
        return jsonify({"error": "Admin cannot post reviews"}), 403
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    stars = data.get("stars", 0)
    try:
        stars = int(stars)
    except (TypeError, ValueError):
        stars = 0
    if not text or len(text) > 2000 or stars < 1 or stars > 5:
        return jsonify({"error": "Invalid review data"}), 400
    with Session() as db:
        existing = db.query(Review).filter(Review.user_id == user.id).first()
        if existing:
            return jsonify({"error": "You already left a review"}), 409
        review = Review(text=text, stars=stars, user_id=user.id)
        db.add(review)
        db.commit()
        return jsonify({
            "id": review.id,
            "text": review.text,
            "stars": review.stars,
            "created_at": review.created_at.strftime("%d.%m.%Y"),
            "user": user.nickname,
        }), 201


@app.route("/api/reviews/<int:review_id>", methods=["PUT"])
def api_reviews_edit(review_id: int):
    _ensure_csrf_header()
    user = get_user_from_jwt()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    stars = data.get("stars", 0)
    try:
        stars = int(stars)
    except (TypeError, ValueError):
        stars = 0
    if not text or len(text) > 2000 or stars < 1 or stars > 5:
        return jsonify({"error": "Invalid review data"}), 400
    with Session() as db:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return jsonify({"error": "Not found"}), 404
        if review.user_id != user.id:
            return jsonify({"error": "Forbidden"}), 403
        review.text = text
        review.stars = stars
        db.commit()
        return jsonify({
            "id": review.id,
            "text": review.text,
            "stars": review.stars,
            "created_at": review.created_at.strftime("%d.%m.%Y"),
            "user": user.nickname,
        })


@app.route("/api/reviews/<int:review_id>", methods=["DELETE"])
def api_reviews_delete(review_id: int):
    _ensure_csrf_header()
    user = get_user_from_jwt()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    with Session() as db:
        review = db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return jsonify({"error": "Not found"}), 404
        if review.user_id != user.id and user.nickname != ADMIN_NICKNAME:
            return jsonify({"error": "Forbidden"}), 403
        db.delete(review)
        db.commit()
    return jsonify({"ok": True})


# роути — тренди

@app.route("/api/order-trends")
@cache.cached(timeout=86400, key_prefix="order_trends")
def api_order_trends():
    with Session() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_orders = db.query(Orders).filter(Orders.order_time >= cutoff).all()
        dish_counts: Dict[str, int] = {}
        for order in recent_orders:
            if order.order_list:
                for name, qty in order.order_list.items():
                    dish_counts[name] = dish_counts.get(name, 0) + int(qty)
        sorted_dishes = sorted(dish_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        result = []
        for name, count in sorted_dishes:
            item = db.query(Menu).filter(Menu.name == name, Menu.active.is_(True)).first()
            if item:
                result.append({
                    "name": item.name,
                    "count": count,
                    "price": item.price,
                    "category": item.category,
                    "discount_percent": item.discount_percent or 0,
                })
    return jsonify(result)


# роути — профіль та пароль

@app.route("/profile")
@login_required
def profile():
    if current_user.nickname == ADMIN_NICKNAME:
        return redirect(url_for("home"))
    with Session() as db:
        user = db.query(Users).filter(Users.id == current_user.id).first()
        orders = (
            db.query(Orders)
            .filter(Orders.user_id == current_user.id)
            .order_by(Orders.order_time.desc())
            .all()
        )
        reservations = (
            db.query(Reservation)
            .options(joinedload(Reservation.table))
            .filter(Reservation.user_id == current_user.id)
            .order_by(Reservation.time_start.desc())
            .all()
        )
        my_review = db.query(Review).filter(Review.user_id == current_user.id).first()
    today = datetime.now().date().isoformat()
    return render_template("profile.html", user=user, orders=orders, reservations=reservations, my_review=my_review, today=today)


@app.route("/api/profile/request-password-code", methods=["POST"])
@limiter.limit("3 per minute")
@login_required
def api_request_password_code():
    _ensure_csrf_header()
    code = str(secrets.randbelow(900000) + 100000)
    with Session() as db:
        user = db.query(Users).filter(Users.id == current_user.id).first()
        user.verification_code = code
        user.code_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
        db.commit()
    send_password_reset_email(current_user.email, code)
    return jsonify({"ok": True})


@app.route("/api/profile/change-password", methods=["POST"])
@limiter.limit("5 per minute")
@login_required
def api_change_password():
    _ensure_csrf_header()
    payload = _require_json()
    code = payload.get("code", "").strip()
    new_password = payload.get("new_password", "")

    if not code or len(code) != 6:
        return jsonify({"error": "Невірний код."}), 400
    if len(new_password) < 8:
        return jsonify({"error": "Пароль має містити щонайменше 8 символів."}), 400

    with Session() as db:
        user = db.query(Users).filter(Users.id == current_user.id).first()
        if user.verification_code != code:
            return jsonify({"error": "Невірний код."}), 400
        if user.code_expiry and user.code_expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return jsonify({"error": "Код прострочений."}), 400
        user.set_password(new_password)
        user.verification_code = None
        user.code_expiry = None
        db.commit()
    return jsonify({"ok": True})


@app.route("/api/profile/toggle-newsletter", methods=["POST"])
@login_required
def api_toggle_newsletter():
    _ensure_csrf_header()
    with Session() as db:
        user = db.query(Users).filter(Users.id == current_user.id).first()
        user.newsletter_opt_in = not user.newsletter_opt_in
        db.commit()
        return jsonify({"newsletter_opt_in": user.newsletter_opt_in})


@app.route("/api/profile/set-birthday", methods=["POST"])
@login_required
def api_set_birthday():
    _ensure_csrf_header()
    if current_user.nickname == ADMIN_NICKNAME:
        return jsonify({"ok": False, "error": "Адміністратор не може встановити дату народження"}), 403
    
    data = _require_json()
    date_of_birth_str = (data.get("date_of_birth") or "").strip()
    
    if not date_of_birth_str:
        return jsonify({"ok": False, "error": "Введіть дату народження"}), 400
    
    try:
        date_of_birth = datetime.strptime(date_of_birth_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"ok": False, "error": "Невірний формат дати"}), 400
    
    if date_of_birth > datetime.now().date():
        return jsonify({"ok": False, "error": "Дата народження не може бути в майбутньому"}), 400
    
    with Session() as db:
        user = db.query(Users).filter(Users.id == current_user.id).first()
        if not user:
            return jsonify({"ok": False, "error": "Користувача не знайдено"}), 404
        
        if user.date_of_birth is not None:
            return jsonify({"ok": False, "error": "Дату народження вже встановлено і не можна змінити"}), 400
        
        user.date_of_birth = date_of_birth
        db.commit()
    
    return jsonify({"ok": True, "date_of_birth": date_of_birth_str})


@app.route("/api/forgot-password", methods=["POST"])
@limiter.limit("3 per minute")
def api_forgot_password():
    data = request.get_json(silent=True) or {}
    csrf_tok = data.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not validate_csrf(csrf_tok):
        return jsonify({"error": "CSRF token invalid"}), 403

    email = (data.get("email") or "").strip().lower()
    if not email or not _validate_email(email):
        return jsonify({"error": "Введіть коректний email."}), 400

    with Session() as db:
        user = db.query(Users).filter(Users.email == email, Users.is_verified.is_(True)).first()
        if not user:
            return jsonify({"ok": True})

        code = str(secrets.randbelow(900000) + 100000)
        user.verification_code = code
        user.code_expiry = datetime.now(timezone.utc) + timedelta(minutes=1)
        db.commit()

    send_password_reset_email(email, code)
    return jsonify({"ok": True})


@app.route("/api/forgot-password/check-code", methods=["POST"])
@limiter.limit("5 per minute")
def api_forgot_password_check_code():
    data = request.get_json(silent=True) or {}
    csrf_tok = data.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not validate_csrf(csrf_tok):
        return jsonify({"error": "CSRF token invalid"}), 403

    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()

    if not code or len(code) != 6:
        return jsonify({"error": "Невірний код."}), 400

    with Session() as db:
        user = db.query(Users).filter(Users.email == email, Users.is_verified.is_(True)).first()
        if not user:
            return jsonify({"error": "Невірний код."}), 400
        if user.verification_code != code:
            return jsonify({"error": "Невірний код."}), 400
        if user.code_expiry and user.code_expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return jsonify({"error": "Код прострочений. Запросіть новий."}), 400
    return jsonify({"ok": True})


@app.route("/api/forgot-password/verify", methods=["POST"])
@limiter.limit("5 per minute")
def api_forgot_password_verify():
    data = request.get_json(silent=True) or {}
    csrf_tok = data.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not validate_csrf(csrf_tok):
        return jsonify({"error": "CSRF token invalid"}), 403

    email = (data.get("email") or "").strip().lower()
    code = (data.get("code") or "").strip()
    new_password = data.get("new_password") or ""

    if not code or len(code) != 6:
        return jsonify({"error": "Невірний код."}), 400
    if len(new_password) < 8:
        return jsonify({"error": "Пароль має містити щонайменше 8 символів."}), 400

    with Session() as db:
        user = db.query(Users).filter(Users.email == email, Users.is_verified.is_(True)).first()
        if not user:
            return jsonify({"error": "Користувача не знайдено."}), 404
        if user.verification_code != code:
            return jsonify({"error": "Невірний код."}), 400
        if user.code_expiry and user.code_expiry.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return jsonify({"error": "Код прострочений. Запросіть новий."}), 400
        user.set_password(new_password)
        user.verification_code = None
        user.code_expiry = None
        db.commit()
    return jsonify({"ok": True})
