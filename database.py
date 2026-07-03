import aiosqlite
from datetime import datetime
from config import DB_PATH

# ══════════════════════════════════════════════
#  JADVALLARNI YARATISH
# ══════════════════════════════════════════════
async def create_tables() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        # Oddiy foydalanuvchilar
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id   INTEGER PRIMARY KEY,
                username  TEXT,
                full_name TEXT,
                join_date TEXT
            )
        """)
        # Kichik adminlar (kanal egalari)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sub_admins (
                user_id    INTEGER PRIMARY KEY,
                username   TEXT,
                full_name  TEXT,
                added_date TEXT
            )
        """)
        # Fayllar
        await db.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id      TEXT NOT NULL,
                file_type    TEXT NOT NULL,
                caption      TEXT,
                uploaded_by  INTEGER NOT NULL,
                upload_date  TEXT NOT NULL
            )
        """)
        # Global majburiy obuna kanallari (super admin qo'shadi)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id   INTEGER PRIMARY KEY,
                channel_name TEXT NOT NULL,
                invite_link  TEXT NOT NULL
            )
        """)
        # Sub-admin o'z kanallari (limitga bog'liq)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sub_admin_channels (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id     INTEGER NOT NULL,
                channel_id   INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                invite_link  TEXT NOT NULL,
                UNIQUE(channel_id)
            )
        """)
        # Sozlamalar (kalit-qiymat jadvali)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Default: sub-admin uchun max 4 kanal
        await db.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES ('max_sub_channels', '4')
        """)
        await db.commit()


# ══════════════════════════════════════════════
#  SOZLAMALAR
# ══════════════════════════════════════════════
async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def get_max_sub_channels() -> int:
    """Sub-admin uchun ruxsat etilgan maksimal kanal soni."""
    val = await get_setting("max_sub_channels")
    try:
        return int(val) if val else 4
    except ValueError:
        return 4


# ══════════════════════════════════════════════
#  USERS
# ══════════════════════════════════════════════
async def add_user(user_id: int, username: str | None, full_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?,?,?,?)",
            (user_id, username or "", full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        await db.commit()


async def get_all_user_ids() -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            rows = await cur.fetchall()
    return [r[0] for r in rows]


async def delete_user(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await db.commit()


async def count_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


# ══════════════════════════════════════════════
#  SUB-ADMINS
# ══════════════════════════════════════════════
async def add_sub_admin(user_id: int, username: str | None, full_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sub_admins (user_id, username, full_name, added_date) VALUES (?,?,?,?)",
            (user_id, username or "", full_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        await db.commit()


async def remove_sub_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM sub_admins WHERE user_id = ?", (user_id,))
        # Admin o'chirilganda uning kanallari ham o'chadi
        await db.execute("DELETE FROM sub_admin_channels WHERE admin_id = ?", (user_id,))
        await db.commit()
        return cur.rowcount > 0


async def get_all_sub_admins() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, username, full_name, added_date FROM sub_admins"
        ) as cur:
            rows = await cur.fetchall()
    return [
        {"user_id": r[0], "username": r[1], "full_name": r[2], "added_date": r[3]}
        for r in rows
    ]


async def is_sub_admin(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM sub_admins WHERE user_id = ?", (user_id,)
        ) as cur:
            return await cur.fetchone() is not None


# ══════════════════════════════════════════════
#  FILES
# ══════════════════════════════════════════════
async def save_file(
    file_id: str, file_type: str, caption: str | None, uploaded_by: int
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO files (file_id, file_type, caption, uploaded_by, upload_date) VALUES (?,?,?,?,?)",
            (file_id, file_type, caption or "", uploaded_by,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        await db.commit()
        return cur.lastrowid  # type: ignore


async def get_file(file_db_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, file_id, file_type, caption, uploaded_by FROM files WHERE id = ?",
            (file_db_id,),
        ) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "file_id": row[1], "file_type": row[2],
            "caption": row[3], "uploaded_by": row[4]}


async def count_files() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM files") as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def delete_file_by_id(file_db_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM files WHERE id = ?", (file_db_id,))
        await db.commit()
        return cur.rowcount > 0


# ══════════════════════════════════════════════
#  GLOBAL CHANNELS  (super admin boshqaradi)
# ══════════════════════════════════════════════
async def add_channel(channel_id: int, channel_name: str, invite_link: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO channels (channel_id, channel_name, invite_link) VALUES (?,?,?)",
            (channel_id, channel_name, invite_link),
        )
        await db.commit()


async def remove_channel(channel_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        await db.commit()
        return cur.rowcount > 0


async def get_all_channels() -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, channel_name, invite_link FROM channels"
        ) as cur:
            rows = await cur.fetchall()
    return [{"channel_id": r[0], "channel_name": r[1], "invite_link": r[2]} for r in rows]


# ══════════════════════════════════════════════
#  SUB-ADMIN CHANNELS  (har bir admin o'z kanallari)
# ══════════════════════════════════════════════
async def add_sub_admin_channel(
    admin_id: int, channel_id: int, channel_name: str, invite_link: str
) -> bool:
    """
    Kanal qo'shadi. Limit oshgan bo'lsa False qaytaradi.
    Kanal ID allaqachon boshqa adminda bo'lsa ham False.
    """
    max_limit = await get_max_sub_channels()
    async with aiosqlite.connect(DB_PATH) as db:
        # Bu adminda nechta kanal bor?
        async with db.execute(
            "SELECT COUNT(*) FROM sub_admin_channels WHERE admin_id = ?", (admin_id,)
        ) as cur:
            row = await cur.fetchone()
        current_count = row[0] if row else 0

        if current_count >= max_limit:
            return False  # limit to'ldi

        try:
            await db.execute(
                """INSERT INTO sub_admin_channels
                   (admin_id, channel_id, channel_name, invite_link)
                   VALUES (?, ?, ?, ?)""",
                (admin_id, channel_id, channel_name, invite_link),
            )
            await db.commit()
            return True
        except Exception:
            return False  # UNIQUE buzilishi (kanal boshqasida bor)


async def remove_sub_admin_channel(admin_id: int, channel_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM sub_admin_channels WHERE admin_id = ? AND channel_id = ?",
            (admin_id, channel_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_sub_admin_channels(admin_id: int) -> list[dict]:
    """Berilgan adminnig o'z kanallarini qaytaradi."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, channel_name, invite_link FROM sub_admin_channels WHERE admin_id = ?",
            (admin_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"channel_id": r[0], "channel_name": r[1], "invite_link": r[2]} for r in rows]


async def count_sub_admin_channels(admin_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM sub_admin_channels WHERE admin_id = ?", (admin_id,)
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def get_all_sub_admin_channels() -> list[dict]:
    """Barcha sub-adminlarning barcha kanallarini qaytaradi (global tekshirish uchun)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT channel_id, channel_name, invite_link FROM sub_admin_channels"
        ) as cur:
            rows = await cur.fetchall()
    return [{"channel_id": r[0], "channel_name": r[1], "invite_link": r[2]} for r in rows]
