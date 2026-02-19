<div align="center">

#  СМАКОК

**Преміальний ресторанний досвід — онлайн**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-C6A75E?style=for-the-badge)](LICENSE)

<br>

> *Повноцінний веб-застосунок для ресторану з онлайн-замовленнями, бронюванням столиків, системою відгуків та адмін-панеллю.*

</div>

---

##  Можливості

| Функція | Опис |
|---------|------|
|  **Онлайн-замовлення** | Перегляд меню, кошик, оформлення замовлення з інвойсом на email |
|  **Бронювання столиків** | Інтерактивна карта залу, вибір дати/часу, автоматична перевірка доступності |
|  **Відгуки** | Одна рецензія на користувача з рейтингом 1–5 зірок, редагування та видалення |
|  **Чат підтримки** | Реальний час спілкування між користувачем та адміністратором |
|  **Email-сповіщення** | Підтвердження реєстрації, інвойси, знижки (батчева розсилка кожні 5 хв) |
|  **Безпека** | bcrypt-хешування паролів, CSRF-захист, JWT-токени, rate limiting |
|  **Адмін-панель** | Управління меню, замовленнями, бронюваннями, користувачами та відгуками |
|  **Знижки** | Адмін встановлює знижки — підписники отримують зведений email |
|  **Розсилка** | Підписка на новини з профілю, toggle on/off |

---

##  Архітектура

```
PythonProject12/
├── online_restaurant.py      # Точка входу
├── online_restaurant_db.py   # SQLAlchemy моделі (Users, Menu, Orders, ...)
├── requirements.txt
├── alembic/                  # Міграції БД
├── app/
│   ├── __init__.py           # Flask app, 34 REST API ендпоінти + HTML роути
│   ├── config.py             # Конфігурація
│   ├── utils.py              # Валідація, хелпери
│   ├── seed.py               # Початкові дані (меню, столики, адмін)
│   └── services/
│       ├── emails.py         # SMTP email-відправка
│       └── invoices.py       # HTML-інвойси
├── templates/                # 23 Jinja2 шаблони
└── static/
    ├── css/style.css         # Dark premium UI (чорний + золотий)
    ├── menu/                 # Зображення страв
    └── favicon.svg           # Лого
```

---

## Технології

- **Backend:** Flask 3, SQLAlchemy 2, Flask-Login, Flask-Limiter, PyJWT
- **Database:** PostgreSQL 16 + Alembic міграції
- **Frontend:** Jinja2, vanilla JS (fetch API), CSS3 (dark premium theme)
- **Security:** bcrypt, CSRF tokens, JWT, rate limiting, input validation
- **Email:** SMTP (Gmail) — верифікація, інвойси, знижки
- **Background:** Threading — батчева розсилка знижок

---

##  Швидкий старт

### 1. Клонування та залежності

```bash
git clone <repo-url>
cd PythonProject12
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Змінні середовища

Створіть `.env` файл:

```env
SECRET_KEY=your-secret-key-here
PGUSER=postgres
PGPASSWORD=your-db-password
PGHOST=127.0.0.1
PGPORT=5432
PGDATABASE=online_restaurant
ADMIN_NICKNAME=Admin
ADMIN_PASSWORD=your-admin-password
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
```

### 3. База даних

```bash
# Створіть БД PostgreSQL
createdb online_restaurant

# Застосуйте міграції
alembic upgrade head
```

### 4. Запуск

```bash
python online_restaurant.py
```

Відкрийте **http://127.0.0.1:5000** 

---

##  REST API

**REST API** (Representational State Transfer) — це архітектурний підхід, де сервер повертає **чисті дані (JSON)**, а не готові HTML-сторінки. Клієнт (браузер, мобільний додаток) сам вирішує, як їх відобразити.

**Без REST API (класичний підхід):**
```
Користувач натиснув "Видалити" → форма POST → сервер видаляє + рендерить нову HTML-сторінку → перезавантаження 
```

**З REST API (як у цьому проєкті):**
```
Користувач натиснув "Видалити" → JavaScript fetch() → сервер повертає {"ok": true} → JS прибирає картку без перезавантаження 
```

**HTTP-методи:**

| Метод | Призначення | Приклад |
|-------|-------------|---------|
| `GET` | Отримати дані | `GET /api/menu` → список страв |
| `POST` | Створити | `POST /api/orders` → нове замовлення |
| `PUT` | Оновити повністю | `PUT /api/reviews/5` → редагувати відгук |
| `PATCH` | Оновити частково | `PATCH /api/admin/menu/3` → змінити ціну |
| `DELETE` | Видалити | `DELETE /api/reviews/5` → видалити відгук |

> HTML-форми підтримують лише `GET` і `POST`. Решта методів доступні тільки через JavaScript (`fetch`).

Застосунок має **34 REST API ендпоінти** (`/api/...`), що повертають JSON:

<details>
<summary><b>Авторизація</b></summary>

| Метод | Ендпоінт | Опис |
|-------|----------|------|
| `GET` | `/api/session` | Поточна сесія |
| `GET` | `/api/csrf` | CSRF токен |
| `POST` | `/api/auth/login` | Вхід |
| `POST` | `/api/auth/register` | Реєстрація |
| `POST` | `/api/auth/logout` | Вихід |

</details>

<details>
<summary><b>Меню та замовлення</b></summary>

| Метод | Ендпоінт | Опис |
|-------|----------|------|
| `GET` | `/api/menu` | Список меню |
| `GET/POST` | `/api/orders` | Замовлення |
| `GET/DELETE` | `/api/orders/<id>` | Деталі / скасування |

</details>

<details>
<summary><b>Бронювання</b></summary>

| Метод | Ендпоінт | Опис |
|-------|----------|------|
| `GET` | `/api/tables` | Столики |
| `GET` | `/api/tables/availability` | Доступність |
| `GET/POST` | `/api/reservations` | Бронювання |
| `DELETE` | `/api/reservations/<id>` | Видалення |
| `POST` | `/api/reservations/<id>/cancel` | Скасування |

</details>

<details>
<summary><b>Відгуки</b></summary>

| Метод | Ендпоінт | Опис |
|-------|----------|------|
| `GET` | `/api/reviews` | Всі відгуки |
| `POST` | `/api/reviews` | Створити |
| `PUT` | `/api/reviews/<id>` | Редагувати |
| `DELETE` | `/api/reviews/<id>` | Видалити |

</details>

<details>
<summary><b>Чат, профіль, адмін</b></summary>

| Метод | Ендпоінт | Опис |
|-------|----------|------|
| `GET` | `/api/chat/unread` | Непрочитані |
| `GET` | `/api/chat/users` | Список чатів (адмін) |
| `GET/POST` | `/api/chat/<id>` | Повідомлення |
| `POST` | `/api/chat/<id>/close` | Закрити чат |
| `POST` | `/api/profile/change-password` | Зміна пароля |
| `POST` | `/api/profile/toggle-newsletter` | Розсилка |
| `POST` | `/api/forgot-password` | Відновлення |
| `GET/POST` | `/api/admin/menu` | Управління меню |
| `PATCH/DELETE` | `/api/admin/menu/<id>` | Редагування позиції |
| `POST` | `/api/admin/menu/<id>/discount` | Знижка |
| `GET` | `/api/order-trends` | Тренди замовлень |

</details>

---

## 🗃 Alembic (Міграції БД)

Alembic — інструмент для **версіонування схеми бази даних**. Замість ручного `ALTER TABLE` — автоматичні міграції.

**Як це працює:**

```
Модель (Python)  →  Alembic порівнює  →  Генерує SQL  →  Застосовує до БД
   Users.balance      зі схемою БД        ALTER TABLE      PostgreSQL
```

**Основні команди:**

```bash
# Створити нову міграцію (автоматично порівнює моделі з БД)
alembic revision --autogenerate -m "add balance column"

# Застосувати всі міграції
alembic upgrade head

# Відкотити останню міграцію
alembic downgrade -1

# Подивитися поточну версію БД
alembic current

# Історія міграцій
alembic history
```

**Структура:**

```
alembic/
├── env.py              # Конфігурація (підключення до БД, імпорт моделей)
├── versions/           # Файли міграцій (кожна — окрема версія)
│   ├── 001_initial.py
│   ├── 002_add_balance.py
│   └── ...
└── script.py.mako      # Шаблон для нових міграцій
```

**Навіщо це потрібно:**
- Не треба руками писати SQL для зміни таблиць
- Кожна зміна схеми — окремий файл з версією
- Можна відкотити назад якщо щось зламалось
- Вся команда працює з однаковою схемою БД

---

##  Цікаві технічні рішення

### `Decimal` — точні розрахунки цін

`Decimal` — це вбудований модуль Python для роботи з числами **без втрати точності**. Звичайний `float` зберігає числа у двійковій системі, що призводить до помилок округлення (`0.1 + 0.2 = 0.30000000000000004`). У ресторані це критично — клієнт побачить неправильну суму в чеку.

`Decimal` зберігає числа як десяткові дроби — так само, як людина пише на папері:

```python
from decimal import Decimal

# float (неточно):
0.1 + 0.2          # → 0.30000000000000004 

# Decimal (точно):
Decimal("0.1") + Decimal("0.2")  # → Decimal('0.3') 

# У проєкті — розрахунок знижки:
price = Decimal("149.90")
discount = price * Decimal("0.15")  # точно 22.485, не 22.48499999...
final = price - discount             # точно 127.415
```

Використовується при розрахунку цін, знижок, сум замовлень та інвойсів.

### `re` (regex) — валідація введених даних

`re` — вбудований модуль Python для роботи з **регулярними виразами** (Regular Expressions). Regex — це мова шаблонів для пошуку та перевірки тексту. Замість написання десятків `if`-перевірок — один рядок патерну.

```python
import re

# Нікнейм: 2–30 символів, літери (укр/лат), цифри, пробіл, _, -
_NICK_RE = re.compile(r"^[a-zA-Zа-яА-ЯіІїЇєЄґҐ0-9_\- ]{2,30}$")
#                      ^                                    ^  ^  ^
#                      |  дозволені символи                  | 2-30 символів
#                      початок рядка                         кінець рядка

# Email: стандартний формат user@domain.com
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

# Перевірка:
_NICK_RE.match("Іван_123")    #  підходить
_NICK_RE.match("@hacker!")    #  заборонені символи
_EMAIL_RE.match("user@gmail.com")  # ✅
_EMAIL_RE.match("not-an-email")    # ❌
```

Перевірка відбувається **до** збереження в БД — якщо введення не відповідає патерну, сервер одразу відхиляє запит. Це захищає від SQL-ін'єкцій та некоректних даних.

### `threading` — фонові задачі

`threading` — вбудований модуль Python для запуску **паралельних потоків**. Потік (thread) — це окрема задача, яка виконується одночасно з основним сервером. Без потоків сервер би "зависав" на кожній відправці email.

**Де використовується:**

1. **Батчева розсилка знижок** — фоновий потік кожні 5 хвилин перевіряє чергу нових знижок і відправляє зведений лист підписникам:

```python
def _discount_email_worker():
    while True:
        time.sleep(300)  # спить 5 хвилин
        with _pending_discounts_lock:  # thread-safe доступ до черги
            batch = list(_pending_discounts)
            _pending_discounts.clear()
        if batch:
            # відправити один лист з усіма знижками кожному підписнику

t = threading.Thread(target=_discount_email_worker, daemon=True)
t.start()  # daemon=True → потік завершиться разом з сервером
```

2. **Відправка email** — кожен лист відправляється в окремому потоці, щоб користувач не чекав 2–5 секунд відповіді SMTP-сервера.

`threading.Lock()` використовується для **thread-safe** доступу до спільної черги знижок — два потоки не можуть одночасно змінювати список.

### `smtplib` + `email.mime` — формування та відправка листів

`smtplib` — вбудований модуль Python для відправки email через протокол **SMTP** (Simple Mail Transfer Protocol). `email.mime` — модуль для побудови складних email-повідомлень.

**MIME** (Multipurpose Internet Mail Extensions) — стандарт, який дозволяє email містити не лише текст, а й HTML, зображення, вкладення. У проєкті кожен лист має **дві версії**:
- `text/plain` — простий текст (fallback для старих клієнтів)
- `text/html` — красивий HTML з градієнтами та стилями (основний)

Поштовий клієнт сам обирає кращу версію.

```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Створення листа з двома версіями
msg = MIMEMultipart("alternative")  # "alternative" = клієнт обирає одну з версій
msg["Subject"] = "СМАКОК — Код підтвердження"
msg["From"] = "restaurant@gmail.com"
msg["To"] = "user@gmail.com"
msg.attach(MIMEText("Ваш код: 4821", "plain", "utf-8"))      # для старих клієнтів
msg.attach(MIMEText("<div>...красивий HTML...</div>", "html", "utf-8"))  # для сучасних

# Відправка через Gmail з TLS-шифруванням
with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.ehlo()               # привітання з сервером
    server.starttls()           # перехід на шифроване з'єднання (TLS)
    server.ehlo()               # повторне привітання після шифрування
    server.login(user, app_password)  # авторизація (App Password, не основний пароль!)
    server.sendmail(from_addr, to_addr, msg.as_string())  # відправка
```

**Порт 587** — стандартний порт для SMTP з STARTTLS (шифрування після підключення). Порт 465 — для SSL (шифрування одразу).

### `Flask-Caching` — кешування важких запитів

`Flask-Caching` — бібліотека для **кешування** результатів функцій. Кеш — це тимчасове сховище, де зберігається результат важкого запиту. Замість повторного виконання запиту до БД — сервер миттєво віддає збережений результат.

**Проблема:** ендпоінт `/api/order-trends` аналізує всі замовлення за 7 днів, рахує популярність кожної страви та сортує. Це важкий запит до БД.

**Рішення:** результат кешується на **24 години** — запит до БД виконується лише раз на добу:

```python
from flask_caching import Cache
cache = Cache(app)

@app.route("/api/order-trends")
@cache.cached(timeout=86400, key_prefix="order_trends")  # 86400 сек = 24 год
def api_order_trends():
    # Перший запит: виконується код → результат зберігається в кеш
    # Наступні запити протягом 24 год: код НЕ виконується → відповідь з кешу миттєво
    with Session() as db:
        # ... важкий аналіз замовлень ...
```

**Без кешу:** 100 користувачів відкрили головну → 100 запитів до БД.
**З кешем:** 100 користувачів відкрили головну → 1 запит до БД + 99 з кешу.

Адмін може вручну очистити кеш через `POST /api/admin/clear-trends-cache` якщо меню змінилось.

---

##  Безпека

- **Паролі** — bcrypt з випадковою сіллю, мінімум 8 символів
- **CSRF** — токен у кожній формі та API-запиті через `X-CSRF-Token`
- **Rate Limiting** — обмеження запитів (5/хв логін, 3/хв зміна пароля)
- **Input Validation** — regex для нікнейму та email, санітизація всіх полів
- **Session** — `SameSite=Lax`, `HttpOnly`, `Secure` у production

---

##  JWT (JSON Web Token)

JWT використовується для аутентифікації API-запитів (чат, відгуки) без прив'язки до серверної сесії.

**Як це працює:**

1. Користувач логіниться → сервер генерує JWT токен з `user_id` та терміном дії
2. Токен підписується `SECRET_KEY` через алгоритм **HS256** (HMAC-SHA256)
3. Клієнт зберігає токен і передає його в заголовку `Authorization: Bearer <token>`
4. Сервер перевіряє підпис і витягує `user_id` — без звернення до БД

**Структура токена:**

```
eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo1LCJleHAiOjE3MDc4NDAwMDB9.abc123signature
│                      │                                                │
│  Header (algo)       │  Payload (user_id, exp)                        │  Signature
```

**Переваги:**
- Stateless — сервер не зберігає сесію для API-запитів
- Самодостатній — вся інформація всередині токена
- Безпечний — підпис гарантує, що токен не підроблений

---

## SMTP (Email-розсилка)

Застосунок відправляє email через **Gmail SMTP** з TLS-шифруванням.

**Типи листів:**

| Тип | Коли відправляється |
|-----|--------------------|
| Код верифікації (4 цифри) | При реєстрації — підтвердження email |
| Код зміни пароля (6 цифр) | При запиті на зміну/відновлення пароля |
| Інвойс (HTML inline) | Після оформлення замовлення або бронювання |
| Знижки (батч) | Кожні 5 хвилин — зведений лист з усіма новими знижками |

**Як працює SMTP-відправка:**

```
Клієнт → SMTP сервер (smtp.gmail.com:587)
  1. EHLO — привітання
  2. STARTTLS — перехід на шифроване з'єднання
  3. LOGIN — авторизація через App Password
  4. SENDMAIL — відправка MIME-повідомлення
```

**Батчева розсилка знижок:**

Коли адмін додає знижку — вона **не відправляється одразу**. Замість цього:
1. Знижка додається в чергу (`_pending_discounts`)
2. Фоновий потік (`threading`) кожні 5 хвилин перевіряє чергу
3. Якщо є нові знижки — формує **один лист** з таблицею всіх знижок
4. Відправляє кожному підписнику (`newsletter_opt_in=True`)

Це зменшує спам і групує знижки в один зручний лист.

**Безпека SMTP:**
- App Password замість основного пароля Gmail
- TLS-шифрування всіх з'єднань
- Відправка в окремому потоці (`threading`) — не блокує основний сервер

---

##  Автодоповнення адрес доставки

Застосунок використовує **Nominatim API** (OpenStreetMap) для автоматичного пошуку та підказок адрес.

### Як це працює

1. **Користувач вводить адресу** → після 3 символів запускається пошук
2. **Запит до Nominatim API** → `https://nominatim.openstreetmap.org/search`
3. **Отримання до 10 варіантів** з координатами (lat/lon)
4. **Форматування адреси** → вулиця, будинок, район, місто
5. **Вибір зі списку** → адреса підставляється, координати зберігаються
6. **Перевірка зони доставки** → натискання кнопки → розрахунок відстані від ресторану

### Приклад роботи

```
Введення: "Рубіжанський"

Результат (підказки):
├─ Рубіжанський провулок, Харків
├─ Рубіжанський провулок, Луганськ
├─ Рубіжанська вулиця, Київ
└─ ...
```

### Технічні деталі

**API endpoint:** `GET /api/address/suggest?q=<запит>`

**Параметри запиту до Nominatim:**
- `q` — пошуковий запит (мінімум 3 символи)
- `format=json` — формат відповіді
- `addressdetails=1` — деталізована інформація про адресу
- `limit=10` — максимум 10 результатів
- `countrycodes=ua` — тільки Україна

**Формат відповіді:**
```json
[
  {
    "displayName": "Французький бульвар, 24/26, Харків",
    "lat": 49.9903821,
    "lon": 36.2904062
  }
]
```

**Перевірка зони доставки:**
- Центр: Французький бульвар, Харків (49.9903821, 36.2904062)
- Радіус: 20 км
- Алгоритм: формула Haversine (точний розрахунок відстані на сфері)

### Переваги підходу

✅ **Автоматичний пошук** — не потрібно вручну додавати адреси  
✅ **Актуальні дані** — OpenStreetMap оновлюється волонтерами  
✅ **Розрізнення міст** — "Рубіжанський провулок, Харків" ≠ "Рубіжанський провулок, Луганськ"  
✅ **Координати** — точна перевірка відстані доставки  
✅ **Безкоштовно** — Nominatim API не потребує API ключа  

### UI/UX

- **Підказки з'являються** після введення 3+ символів
- **Прокручування** — до 10 варіантів у випадаючому списку
- **Кнопка перевірки** — "Перевірити адресу на зону досяжності"
- **Статус** — ✅ в зоні (X км) або ❌ поза зоною
- **Опціональна перевірка** — можна оформити замовлення без перевірки

---

##  Функціонал дня народження

Користувачі можуть вказати дату народження в профілі — у день народження автоматично:

-  **Привітальний email** з брендованим дизайном
-  **Знижка 10%** на всі страви в меню (діє весь день)

### Особливості

- Дату народження можна встановити **лише один раз** (не можна змінити)
- Адміністратор не може встановити дату народження
- Фоновий процес перевіряє дні народження **кожну годину**
- Перевірка запускається одразу при старті сервера

---

##  Ліцензія

Цей проєкт розповсюджується під ліцензією **MIT**.

```
MIT License

Copyright (c) 2025 СМАКОК

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
