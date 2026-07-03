import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot token ──────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ── Bosh Super Admin ID (faqat bitta, .env dan) ─
_super_raw: str = os.getenv("SUPER_ADMIN_ID", "")
SUPER_ADMIN_ID: int = int(_super_raw.strip()) if _super_raw.strip().isdigit() else 0

# ── Ma'lumotlar bazasi fayli ───────────────────
DB_PATH: str = "storage.db"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")

if not SUPER_ADMIN_ID:
    raise ValueError("SUPER_ADMIN_ID muhit o'zgaruvchisi o'rnatilmagan!")
