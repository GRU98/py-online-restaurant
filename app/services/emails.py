from __future__ import annotations

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from dotenv import load_dotenv
load_dotenv()

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


def send_verification_email(to_email: str, code: str) -> bool:
    subject = "СМАКОК — Код підтвердження"
    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;'
        'background:#08080C;border-radius:20px;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);'
        'padding:36px 32px 28px;text-align:center;border-bottom:1px solid rgba(198,167,94,0.1);">'
        '<div style="font-size:32px;font-weight:800;color:#C6A75E;letter-spacing:4px;'
        'text-shadow:0 0 30px rgba(198,167,94,0.2);">СМАКОК</div>'
        '<div style="color:#5C5C55;font-size:11px;letter-spacing:3px;text-transform:uppercase;'
        'margin-top:6px;">Преміальний ресторанний досвід</div>'
        '</div>'
        '<div style="padding:36px 32px 40px;text-align:center;">'
        '<p style="font-size:15px;color:#9A9890;margin:0 0 8px;">Вітаємо! Ваш код підтвердження:</p>'
        '<div style="margin:24px 0 28px;">'
        '<span style="display:inline-block;font-size:40px;font-weight:800;letter-spacing:14px;'
        'color:#C6A75E;background:linear-gradient(135deg,rgba(198,167,94,0.06),rgba(192,57,43,0.04));'
        'padding:18px 36px;border-radius:14px;'
        f'border:1px solid rgba(198,167,94,0.15);">{code}</span>'
        '</div>'
        '<p style="font-size:13px;color:#5C5C55;margin:0 0 20px;line-height:1.6;">'
        'Код дійсний протягом <span style="color:#C0392B;font-weight:600;">1 хвилини</span>.<br>'
        'Якщо ви не реєструвалися — ігноруйте цей лист.</p>'
        '<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(198,167,94,0.15),'
        'rgba(192,57,43,0.1),transparent);margin:0 0 20px;"></div>'
        '<p style="font-size:11px;color:#3A3A35;margin:0;">'
        '© СМАКОК — Харків, Французький бульвар</p>'
        '</div></div>'
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(f"Ваш код підтвердження СМАКОК: {code}", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def send_discount_email(to_email: str, item_name: str, old_price: float, new_price: float, percent: int) -> bool:
    subject = f"СМАКОК — Знижка {percent}% на {item_name}!"
    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;'
        'background:#08080C;border-radius:20px;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);'
        'padding:36px 32px 28px;text-align:center;border-bottom:1px solid rgba(198,167,94,0.1);">'
        '<div style="font-size:32px;font-weight:800;color:#C6A75E;letter-spacing:4px;'
        'text-shadow:0 0 30px rgba(198,167,94,0.2);">СМАКОК</div>'
        '<div style="color:#5C5C55;font-size:11px;letter-spacing:3px;text-transform:uppercase;'
        'margin-top:6px;">Преміальний ресторанний досвід</div>'
        '</div>'
        '<div style="padding:36px 32px 40px;text-align:center;">'
        f'<p style="font-size:18px;color:#E74C3C;font-weight:700;margin:0 0 8px;">🔥 Знижка {percent}%!</p>'
        f'<p style="font-size:20px;color:#C6A75E;font-weight:700;margin:0 0 16px;">{item_name}</p>'
        '<div style="margin:0 0 24px;">'
        f'<span style="font-size:16px;color:#5C5C55;text-decoration:line-through;margin-right:12px;">{old_price:.0f} грн</span>'
        f'<span style="font-size:24px;color:#C6A75E;font-weight:800;">{new_price:.0f} грн</span>'
        '</div>'
        '<p style="font-size:13px;color:#5C5C55;margin:0 0 20px;line-height:1.6;">'
        'Поспішайте скористатися пропозицією!</p>'
        '<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(198,167,94,0.15),'
        'rgba(192,57,43,0.1),transparent);margin:0 0 20px;"></div>'
        '<p style="font-size:11px;color:#3A3A35;margin:0;">© СМАКОК — Харків, Французький бульвар</p>'
        '</div></div>'
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(f"Знижка {percent}% на {item_name}! Було {old_price:.0f} грн, тепер {new_price:.0f} грн.", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[DISCOUNT EMAIL ERROR] {e}")
        return False


def send_password_reset_email(to_email: str, code: str) -> bool:
    subject = "СМАКОК — Код зміни пароля"
    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:520px;margin:0 auto;'
        'background:#08080C;border-radius:20px;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);'
        'padding:36px 32px 28px;text-align:center;border-bottom:1px solid rgba(198,167,94,0.1);">'
        '<div style="font-size:32px;font-weight:800;color:#C6A75E;letter-spacing:4px;'
        'text-shadow:0 0 30px rgba(198,167,94,0.2);">СМАКОК</div>'
        '<div style="color:#5C5C55;font-size:11px;letter-spacing:3px;text-transform:uppercase;'
        'margin-top:6px;">Зміна пароля</div>'
        '</div>'
        '<div style="padding:36px 32px 40px;text-align:center;">'
        '<p style="font-size:15px;color:#9A9890;margin:0 0 8px;">Ваш код для зміни пароля:</p>'
        '<div style="margin:24px 0 28px;">'
        '<span style="display:inline-block;font-size:40px;font-weight:800;letter-spacing:14px;'
        'color:#C6A75E;background:linear-gradient(135deg,rgba(198,167,94,0.06),rgba(192,57,43,0.04));'
        'padding:18px 36px;border-radius:14px;'
        f'border:1px solid rgba(198,167,94,0.15);">{code}</span>'
        '</div>'
        '<p style="font-size:13px;color:#5C5C55;margin:0 0 20px;line-height:1.6;">'
        'Код дійсний протягом <span style="color:#C0392B;font-weight:600;">1 хвилини</span>.<br>'
        'Якщо ви не запитували зміну пароля — ігноруйте цей лист.</p>'
        '<div style="height:1px;background:linear-gradient(90deg,transparent,rgba(198,167,94,0.15),'
        'rgba(192,57,43,0.1),transparent);margin:0 0 20px;"></div>'
        '<p style="font-size:11px;color:#3A3A35;margin:0;">© СМАКОК — Харків, Французький бульвар</p>'
        '</div></div>'
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg.attach(MIMEText(f"Ваш код зміни пароля СМАКОК: {code}", "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[PASSWORD EMAIL ERROR] {e}")
        return False


ADMIN_EMAIL = "ivanbatulin192@gmail.com"


def send_admin_new_order_email(
    order_id: int,
    invoice_number: str,
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    customer_address: str,
    payment_method: str,
    total_cost: float,
    order_list: dict,
    delivery_notes: str | None = None,
) -> bool:
    """Відправляє адміну повідомлення про нове замовлення."""
    subject = f"СМАКОК — Нове замовлення #{order_id}"
    payment_label = "Карта" if payment_method == "card" else "Готівка"

    items_html = ""
    items_text = ""
    for name, qty in order_list.items():
        items_html += f'<tr><td style="padding:8px 14px;border-bottom:1px solid rgba(198,167,94,0.1);color:#e8e0d0;font-size:14px;">{name}</td><td style="padding:8px 14px;border-bottom:1px solid rgba(198,167,94,0.1);text-align:center;color:#C6A75E;font-weight:600;">{qty}</td></tr>'
        items_text += f"  • {name} x{qty}\n"

    notes_html = f'<tr><td style="padding:8px 14px;color:#9A9890;font-size:13px;">Коментар</td><td style="padding:8px 14px;color:#e8e0d0;font-size:14px;">{delivery_notes}</td></tr>' if delivery_notes else ""
    notes_text = f"Коментар: {delivery_notes}\n" if delivery_notes else ""

    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;'
        'background:#08080C;border-radius:20px;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);'
        'padding:36px 32px 28px;text-align:center;border-bottom:1px solid rgba(198,167,94,0.1);">'
        '<div style="font-size:32px;font-weight:800;color:#C6A75E;letter-spacing:4px;">СМАКОК</div>'
        '<div style="color:#5C5C55;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-top:6px;">Адмін-повідомлення</div>'
        '</div>'
        '<div style="padding:32px;">'
        f'<p style="font-size:20px;color:#2ECC71;font-weight:700;text-align:center;margin:0 0 24px;">🛒 Нове замовлення #{order_id}</p>'
        '<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">'
        f'<tr><td style="padding:8px 14px;color:#9A9890;font-size:13px;width:40%;">Номер рахунку</td><td style="padding:8px 14px;color:#C6A75E;font-size:14px;font-weight:600;">{invoice_number}</td></tr>'
        f'<tr><td style="padding:8px 14px;color:#9A9890;font-size:13px;">Клієнт</td><td style="padding:8px 14px;color:#e8e0d0;font-size:14px;font-weight:600;">{customer_name}</td></tr>'
        f'<tr><td style="padding:8px 14px;color:#9A9890;font-size:13px;">Email</td><td style="padding:8px 14px;color:#e8e0d0;font-size:14px;">{customer_email}</td></tr>'
        f'<tr><td style="padding:8px 14px;color:#9A9890;font-size:13px;">Телефон</td><td style="padding:8px 14px;color:#e8e0d0;font-size:14px;">{customer_phone}</td></tr>'
        f'<tr><td style="padding:8px 14px;color:#9A9890;font-size:13px;">Адреса</td><td style="padding:8px 14px;color:#e8e0d0;font-size:14px;">{customer_address}</td></tr>'
        f'<tr><td style="padding:8px 14px;color:#9A9890;font-size:13px;">Оплата</td><td style="padding:8px 14px;color:#e8e0d0;font-size:14px;">{payment_label}</td></tr>'
        f'{notes_html}'
        '</table>'
        '<p style="font-size:14px;color:#C6A75E;font-weight:600;margin:16px 0 8px;text-transform:uppercase;letter-spacing:1px;">Позиції замовлення:</p>'
        '<table style="width:100%;border-collapse:collapse;margin-bottom:16px;">'
        '<thead><tr><th style="padding:8px 14px;text-align:left;color:#C6A75E;font-size:12px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid rgba(198,167,94,0.2);">Страва</th>'
        '<th style="padding:8px 14px;text-align:center;color:#C6A75E;font-size:12px;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid rgba(198,167,94,0.2);">К-сть</th></tr></thead>'
        f'<tbody>{items_html}</tbody>'
        '</table>'
        f'<div style="background:rgba(198,167,94,0.08);border-radius:12px;padding:16px;text-align:center;margin-top:16px;">'
        f'<span style="font-size:14px;color:#9A9890;">Сума замовлення:</span> '
        f'<span style="font-size:22px;color:#C6A75E;font-weight:800;margin-left:8px;">{total_cost:.0f} грн</span>'
        '</div>'
        '</div>'
        '<div style="padding:16px 32px;text-align:center;border-top:1px solid rgba(198,167,94,0.08);">'
        '<p style="font-size:11px;color:#3A3A35;margin:0;">© СМАКОК — Харків, Французький бульвар</p>'
        '</div></div>'
    )

    plain = (
        f"Нове замовлення #{order_id}\n"
        f"Рахунок: {invoice_number}\n"
        f"Клієнт: {customer_name}\n"
        f"Email: {customer_email}\n"
        f"Телефон: {customer_phone}\n"
        f"Адреса: {customer_address}\n"
        f"Оплата: {payment_label}\n"
        f"{notes_text}"
        f"Позиції:\n{items_text}"
        f"Сума: {total_cost:.0f} грн"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_EMAIL
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, ADMIN_EMAIL, msg.as_string())
        return True
    except Exception as e:
        print(f"[ADMIN ORDER EMAIL ERROR] {e}")
        return False


def send_admin_new_reservation_email(
    reservation_id: int,
    guest_name: str,
    guest_phone: str,
    user_email: str,
    user_nickname: str,
    table_label: str,
    table_capacity: int,
    time_start: str,
    time_end: str,
    prepaid: float,
) -> bool:
    """Відправляє адміну повідомлення про нове бронювання."""
    subject = f"СМАКОК — Нове бронювання #{reservation_id}"

    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;'
        'background:#08080C;border-radius:20px;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);'
        'padding:36px 32px 28px;text-align:center;border-bottom:1px solid rgba(198,167,94,0.1);">'
        '<div style="font-size:32px;font-weight:800;color:#C6A75E;letter-spacing:4px;">СМАКОК</div>'
        '<div style="color:#5C5C55;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-top:6px;">Адмін-повідомлення</div>'
        '</div>'
        '<div style="padding:32px;">'
        f'<p style="font-size:20px;color:#3498DB;font-weight:700;text-align:center;margin:0 0 24px;">📅 Нове бронювання #{reservation_id}</p>'
        '<table style="width:100%;border-collapse:collapse;">'
        f'<tr><td style="padding:10px 14px;color:#9A9890;font-size:13px;width:40%;">Гість</td><td style="padding:10px 14px;color:#e8e0d0;font-size:14px;font-weight:600;">{guest_name}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#9A9890;font-size:13px;">Телефон</td><td style="padding:10px 14px;color:#e8e0d0;font-size:14px;">{guest_phone}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#9A9890;font-size:13px;">Користувач</td><td style="padding:10px 14px;color:#e8e0d0;font-size:14px;">{user_nickname}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#9A9890;font-size:13px;">Email</td><td style="padding:10px 14px;color:#e8e0d0;font-size:14px;">{user_email}</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#9A9890;font-size:13px;">Столик</td><td style="padding:10px 14px;color:#C6A75E;font-size:14px;font-weight:600;">{table_label} ({table_capacity} місць)</td></tr>'
        f'<tr><td style="padding:10px 14px;color:#9A9890;font-size:13px;">Дата та час</td><td style="padding:10px 14px;color:#e8e0d0;font-size:14px;font-weight:600;">{time_start} — {time_end}</td></tr>'
        '</table>'
        f'<div style="background:rgba(198,167,94,0.08);border-radius:12px;padding:16px;text-align:center;margin-top:20px;">'
        f'<span style="font-size:14px;color:#9A9890;">Передоплата:</span> '
        f'<span style="font-size:22px;color:#C6A75E;font-weight:800;margin-left:8px;">{prepaid:.0f} грн</span>'
        '</div>'
        '</div>'
        '<div style="padding:16px 32px;text-align:center;border-top:1px solid rgba(198,167,94,0.08);">'
        '<p style="font-size:11px;color:#3A3A35;margin:0;">© СМАКОК — Харків, Французький бульвар</p>'
        '</div></div>'
    )

    plain = (
        f"Нове бронювання #{reservation_id}\n"
        f"Гість: {guest_name}\n"
        f"Телефон: {guest_phone}\n"
        f"Користувач: {user_nickname}\n"
        f"Email: {user_email}\n"
        f"Столик: {table_label} ({table_capacity} місць)\n"
        f"Час: {time_start} — {time_end}\n"
        f"Передоплата: {prepaid:.0f} грн"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ADMIN_EMAIL
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, ADMIN_EMAIL, msg.as_string())
        return True
    except Exception as e:
        print(f"[ADMIN RESERVATION EMAIL ERROR] {e}")
        return False


def send_birthday_email(user_email: str, user_nickname: str) -> bool:
    """Відправляє привітальний email користувачу на день народження."""
    subject = "🎉 З Днем народження від СМАКОК!"

    html_body = (
        '<div style="font-family:Segoe UI,Arial,sans-serif;max-width:560px;margin:0 auto;'
        'background:#08080C;border-radius:20px;overflow:hidden;">'
        '<div style="background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);'
        'padding:40px 32px;text-align:center;border-bottom:1px solid rgba(198,167,94,0.1);">'
        '<div style="font-size:48px;margin-bottom:12px;">🎂</div>'
        '<div style="font-size:32px;font-weight:800;color:#C6A75E;letter-spacing:4px;">СМАКОК</div>'
        '<div style="color:#5C5C55;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-top:6px;">Вітаємо з Днем народження!</div>'
        '</div>'
        '<div style="padding:36px 32px;">'
        f'<p style="font-size:22px;color:#e8e0d0;font-weight:700;text-align:center;margin:0 0 16px;">Вітаємо, {user_nickname}! 🎉</p>'
        '<p style="font-size:15px;color:#9A9890;line-height:1.6;text-align:center;margin:0 0 24px;">'
        'Команда СМАКОК щиро вітає вас з Днем народження! Бажаємо здоров\'я, щастя, успіхів та незабутніх моментів!'
        '</p>'
        '<div style="background:linear-gradient(135deg,rgba(198,167,94,0.15) 0%,rgba(198,167,94,0.05) 100%);'
        'border:2px solid rgba(198,167,94,0.3);border-radius:16px;padding:24px;text-align:center;margin:24px 0;">'
        '<div style="font-size:48px;margin-bottom:12px;">🎁</div>'
        '<p style="font-size:18px;color:#C6A75E;font-weight:700;margin:0 0 8px;">Ваш святковий подарунок!</p>'
        '<p style="font-size:32px;color:#e8e0d0;font-weight:800;margin:0 0 8px;">ЗНИЖКА 10%</p>'
        '<p style="font-size:13px;color:#9A9890;margin:0;">на всі страви при оплаті в день народження</p>'
        '</div>'
        '<p style="font-size:14px;color:#9A9890;line-height:1.6;text-align:center;margin:24px 0 0;">'
        'Оформлюйте замовлення сьогодні та отримайте знижку 10% при оплаті. Насолоджуйтесь святом разом з СМАКОК!'
        '</p>'
        '</div>'
        '<div style="padding:20px 32px;text-align:center;border-top:1px solid rgba(198,167,94,0.08);">'
        '<p style="font-size:11px;color:#3A3A35;margin:0;">© СМАКОК — Харків, Французький бульвар</p>'
        '</div></div>'
    )

    plain = (
        f"З Днем народження, {user_nickname}!\n\n"
        "Команда СМАКОК щиро вітає вас з Днем народження!\n"
        "Бажаємо здоров'я, щастя, успіхів та незабутніх моментів!\n\n"
        "🎁 Ваш святковий подарунок: ЗНИЖКА 10% на всі страви при оплаті в день народження!\n\n"
        "Оформлюйте замовлення сьогодні та отримайте знижку 10% при оплаті.\n"
        "Насолоджуйтесь святом разом з СМАКОК!\n\n"
        "© СМАКОК — Харків, Французький бульвар"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = user_email
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, user_email, msg.as_string())
        print(f"[BIRTHDAY EMAIL] Sent to {user_email}")
        return True
    except Exception as e:
        print(f"[BIRTHDAY EMAIL ERROR] {e}")
        return False


def send_invoice_email(to_email: str, subject: str, body_text: str, filename: str, attachment_html: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(attachment_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.ehlo(); server.starttls(); server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"[INVOICE EMAIL ERROR] {e}")
        return False
