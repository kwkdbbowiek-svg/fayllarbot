import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot token ──────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

# ── Bosh Super Admin ID ────────────────────────
_super_raw: str = os.getenv("SUPER_ADMIN_ID", "")
SUPER_ADMIN_ID: int = int(_super_raw.strip()) if _super_raw.strip().isdigit() else 0

# ── Ma'lumotlar bazasi fayli ───────────────────
# Railway da Volume /data papkasiga mount qilinadi.
# Lokal ishlatganda joriy papkada storage.db yaratiladi.
_data_dir: str = "/data" if os.path.isdir("/data") else "."
DB_PATH: str = os.path.join(_data_dir, "storage.db")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")

if not SUPER_ADMIN_ID:
    raise ValueError("SUPER_ADMIN_ID muhit o'zgaruvchisi o'rnatilmagan!")
