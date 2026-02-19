from __future__ import annotations

APP_NAME = "СМАКОК"

_INVOICE_CSS = """
body{margin:0;padding:40px 20px;background:#f5f5f0;font-family:'Segoe UI',Arial,sans-serif;color:#1a1a1a}
.invoice{max-width:680px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.08)}
.header{background:linear-gradient(135deg,#3D1525 0%,#1A0A15 50%,#14141C 100%);padding:36px 40px;text-align:center}
.header h1{margin:0;font-size:36px;font-weight:800;color:#C6A75E;letter-spacing:4px}
.header .sub{color:#8a8a7e;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-top:6px}
.header .doc-title{color:#e8e0d0;font-size:18px;margin-top:18px;font-weight:600}
.body{padding:32px 40px}
.info-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px 32px;margin-bottom:24px}
.info-grid .label{font-size:12px;color:#888;text-transform:uppercase;letter-spacing:1px}
.info-grid .value{font-size:15px;font-weight:500;margin-bottom:8px}
table{width:100%;border-collapse:collapse;margin:20px 0}
thead th{background:#14141C;color:#C6A75E;padding:10px 14px;font-size:12px;text-transform:uppercase;letter-spacing:1px;text-align:left}
thead th:last-child,thead th:nth-child(3),thead th:nth-child(2){text-align:right}
tbody td{padding:10px 14px;border-bottom:1px solid #eee;font-size:14px}
tbody td:last-child,tbody td:nth-child(3),tbody td:nth-child(2){text-align:right}
.total-row{background:#f9f7f2}
.total-row td{font-weight:700;font-size:16px;color:#14141C;border-bottom:none;padding:14px}
.total-row .amount{color:#C6A75E;font-size:20px}
.footer{background:#f9f7f2;padding:24px 40px;text-align:center;border-top:1px solid #eee}
.footer p{margin:4px 0;font-size:13px;color:#888}
.footer .brand{color:#C6A75E;font-weight:700;font-size:14px}
.badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600}
.badge-gold{background:rgba(198,167,94,0.12);color:#C6A75E}
.badge-green{background:rgba(46,160,67,0.1);color:#2ea043}
.badge-red{background:rgba(192,57,43,0.1);color:#c0392b}
@media print{body{padding:0;background:#fff}.invoice{box-shadow:none;border-radius:0}}
"""


def build_order_invoice_html(order, price_lookup: dict) -> str:
    inv_num = order.invoice_number or f"INV-{order.id}"
    order_dt = order.order_time.strftime("%d.%m.%Y %H:%M")
    payment = "Карта" if order.payment_method == "card" else "Готівка"

    rows = ""
    items_total = 0.0
    for name, qty in order.order_list.items():
        price = price_lookup.get(name, 0)
        subtotal = price * qty
        items_total += subtotal
        rows += f"<tr><td>{name}</td><td>{qty}</td><td>{price:.0f} грн</td><td>{subtotal:.0f} грн</td></tr>\n"

    notes_row = f'<div class="label">Коментар</div><div class="value">{order.delivery_notes}</div>' if order.delivery_notes else ""

    penalty = round(max((order.total_cost or 0) - items_total, 0), 2)
    penalty_row = ""
    if penalty >= 0.01:
        penalty_row = (
            f"<tr class=\"penalty-row\"><td colspan=\"3\" style=\"text-align:right;color:#c0392b;font-weight:600;\">"
            f"⚡ Штраф за прострочене скасування</td><td class=\"amount\" style=\"color:#c0392b;\">{penalty:.0f} грн</td></tr>\n"
        )

    grand_total = items_total + penalty

    return f"""<!DOCTYPE html>
<html lang="uk">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Рахунок {inv_num}</title>
<style>{_INVOICE_CSS}</style></head>
<body>
<div class="invoice">
  <div class="header">
    <h1>{APP_NAME}</h1>
    <div class="sub">Преміальний ресторанний досвід</div>
    <div class="doc-title">Розрахунковий рахунок</div>
  </div>
  <div class="body">
    <div class="info-grid">
      <div><div class="label">Номер рахунку</div><div class="value">{inv_num}</div></div>
      <div><div class="label">Дата</div><div class="value">{order_dt}</div></div>
      <div><div class="label">Клієнт</div><div class="value">{order.customer_name}</div></div>
      <div><div class="label">Телефон</div><div class="value">{order.customer_phone}</div></div>
      <div><div class="label">Адреса доставки</div><div class="value">{order.customer_address}</div></div>
      <div><div class="label">Спосіб оплати</div><div class="value"><span class="badge badge-gold">{payment}</span></div></div>
      {notes_row}
    </div>
    <table>
      <thead><tr><th>Позиція</th><th>К-сть</th><th>Ціна</th><th>Сума</th></tr></thead>
      <tbody>
        {rows}
        {penalty_row}
        <tr class="total-row"><td colspan="3" style="text-align:right;">Разом до сплати:</td><td class="amount">{grand_total:.0f} грн</td></tr>
      </tbody>
    </table>
  </div>
  <div class="footer">
    <p class="brand">{APP_NAME}</p>
    <p>Дякуємо за ваше замовлення!</p>
    <p>Цей документ є розрахунковим рахунком та підтвердженням замовлення #{order.id}</p>
  </div>
</div>
</body></html>"""


def build_reservation_invoice_html(reservation) -> str:
    res_dt = reservation.time_start.strftime("%d.%m.%Y %H:%M")
    res_end = reservation.time_end.strftime("%H:%M")
    table_label = reservation.table.label if reservation.table else "—"
    table_cap = reservation.table.capacity if reservation.table else "—"
    status_badge = '<span class="badge badge-red">Скасовано</span>' if reservation.cancelled else '<span class="badge badge-green">Активне</span>'

    return f"""<!DOCTYPE html>
<html lang="uk">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Бронювання #{reservation.id}</title>
<style>{_INVOICE_CSS}</style></head>
<body>
<div class="invoice">
  <div class="header">
    <h1>{APP_NAME}</h1>
    <div class="sub">Преміальний ресторанний досвід</div>
    <div class="doc-title">Рахунок за бронювання</div>
  </div>
  <div class="body">
    <div class="info-grid">
      <div><div class="label">Номер бронювання</div><div class="value">#{reservation.id}</div></div>
      <div><div class="label">Статус</div><div class="value">{status_badge}</div></div>
      <div><div class="label">Дата та час</div><div class="value">{res_dt} — {res_end}</div></div>
      <div><div class="label">Столик</div><div class="value">{table_label} ({table_cap} місць)</div></div>
      <div><div class="label">Гість</div><div class="value">{reservation.guest_name}</div></div>
      <div><div class="label">Телефон</div><div class="value">{reservation.guest_phone}</div></div>
    </div>
    <table>
      <thead><tr><th>Опис</th><th></th><th></th><th>Сума</th></tr></thead>
      <tbody>
        <tr><td>Передоплата за бронювання столика</td><td></td><td></td><td>{reservation.prepaid:.0f} грн</td></tr>
        <tr class="total-row"><td colspan="3" style="text-align:right;">Разом:</td><td class="amount">{reservation.prepaid:.0f} грн</td></tr>
      </tbody>
    </table>
    <p style="font-size:13px;color:#888;margin-top:16px;">
      Безкоштовне скасування за 24+ години до бронювання.<br>
      При пізньому скасуванні передоплата не повертається.
    </p>
  </div>
  <div class="footer">
    <p class="brand">{APP_NAME}</p>
    <p>Дякуємо за бронювання!</p>
    <p>Цей документ є підтвердженням бронювання та розрахунковим рахунком</p>
  </div>
</div>
</body></html>"""
