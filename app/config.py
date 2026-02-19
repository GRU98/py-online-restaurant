from __future__ import annotations

import os
from typing import Dict

from dotenv import load_dotenv
load_dotenv()

APP_NAME = "СМАКОК"
ADMIN_NICKNAME = os.getenv("ADMIN_NICKNAME", "Admin")
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "menu")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TABLE_NUM: Dict[str, int] = {"1-2": 6, "3-4": 4, "4+": 2}
VENUE_COORDS = (49.9903821, 36.2904062)
VENUE_RADIUS_KM = 20.0

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
