import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot_config import BOT_TOKEN
import database as db
from handlers import super_admin, sub_admin, user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    # Ma'lumotlar bazasini yaratish
    await db.create_tables()
    logger.info("✅ Ma'lumotlar bazasi tayyor.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ── Router ulanish tartibi MUHIM ──────────────
    # 1. super_admin  — /start, /admin, sa_* callbacklar (super admin uchun)
    # 2. sub_admin    — fayl upload, /panel (sub-adminlar uchun)
    # 3. user         — /start (oddiy), check_sub callback
    dp.include_router(super_admin.router)
    dp.include_router(sub_admin.router)
    dp.include_router(user.router)

    logger.info("🤖 Bot ishga tushmoqda...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
