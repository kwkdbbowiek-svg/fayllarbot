"""
Oddiy foydalanuvchi handlerlari.
- /start        — xush kelibsiz xabari
- /start <id>   — deep-link orqali fayl olish (hamma uchun, admin ham)
- check_sub     — a'zolikni tekshirish callback
"""

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject

import database as db
from config import SUPER_ADMIN_ID
from keyboards import subscribe_kb

router = Router()


# ──────────────────────────────────────────────
# Yordamchi: a'zo bo'lmagan kanallarni qaytaradi
# ──────────────────────────────────────────────
async def check_subscriptions(bot: Bot, user_id: int) -> list[dict]:
    """
    Foydalanuvchi a'zo bo'lmagan kanallarni qaytaradi.
    Global kanallar + faylni yuklagan adminnig o'z kanallari tekshiriladi.
    Bo'sh ro'yxat = barcha kanallarga a'zo.
    """
    channels = await db.get_all_channels()
    not_subscribed: list[dict] = []
    for ch in channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked"):
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)
    return not_subscribed


async def check_subscriptions_for_file(
    bot: Bot, user_id: int, file_data: dict
) -> list[dict]:
    """
    Fayl uchun maxsus tekshiruv:
    Global kanallar + faylni yuklagan adminnig o'z kanallari.
    """
    # Global kanallar
    global_channels = await db.get_all_channels()
    # Faylni yuklagan adminnig o'z kanallari
    uploader_id     = file_data.get("uploaded_by", 0)
    admin_channels  = await db.get_sub_admin_channels(uploader_id)

    # Ikkalasini birlashtirish (takrorlanmaslik uchun channel_id bo'yicha)
    seen: set[int] = set()
    all_channels: list[dict] = []
    for ch in global_channels + admin_channels:
        if ch["channel_id"] not in seen:
            seen.add(ch["channel_id"])
            all_channels.append(ch)

    not_subscribed: list[dict] = []
    for ch in all_channels:
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked"):
                not_subscribed.append(ch)
        except Exception:
            not_subscribed.append(ch)
    return not_subscribed


# ──────────────────────────────────────────────
# Yordamchi: faylni foydalanuvchiga yuborish
# ──────────────────────────────────────────────
async def send_file_to_user(bot: Bot, chat_id: int, file_data: dict) -> None:
    ftype   = file_data["file_type"]
    fid     = file_data["file_id"]
    caption = file_data["caption"] or None

    if ftype == "video":
        await bot.send_video(chat_id, fid, caption=caption, parse_mode="HTML")
    elif ftype == "document":
        await bot.send_document(chat_id, fid, caption=caption, parse_mode="HTML")
    elif ftype == "audio":
        await bot.send_audio(chat_id, fid, caption=caption, parse_mode="HTML")
    elif ftype == "photo":
        await bot.send_photo(chat_id, fid, caption=caption, parse_mode="HTML")
    else:
        await bot.send_document(chat_id, fid, caption=caption, parse_mode="HTML")


# ══════════════════════════════════════════════
#  /start — HAMMAGA (user, sub-admin, super-admin)
# ══════════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot, command: CommandObject) -> None:
    user = message.from_user
    if user is None:
        return

    is_super    = user.id == SUPER_ADMIN_ID
    is_subadmin = await db.is_sub_admin(user.id)

    deep_arg = command.args  # /start 5  yoki bo'sh

    # ── Deep-link orqali fayl so'rovi ──────────────────────────────────────
    if deep_arg and deep_arg.isdigit():
        file_db_id = int(deep_arg)
        file_data  = await db.get_file(file_db_id)

        if file_data is None:
            await message.answer(
                "❌ Kechirasiz, bu fayl topilmadi yoki o'chirilgan."
            )
            return

        # Oddiy foydalanuvchini bazaga qo'shish (admin/subadmin uchun shart emas)
        if not is_super and not is_subadmin:
            await db.add_user(user.id, user.username, user.full_name)

        # Majburiy obuna tekshiruvi (admin va super-admin uchun o'tkazib yuboriladi)
        if not is_super and not is_subadmin:
            not_subbed = await check_subscriptions_for_file(bot, user.id, file_data)
            if not_subbed:
                await message.answer(
                    "⚠️ <b>Faylni olish uchun quyidagi kanallarga a'zo bo'ling:</b>\n\n"
                    "✅ Barcha kanallarga a'zo bo'lgach,\n"
                    "<b>🔄 A'zolikni tekshirish</b> tugmasini bosing.",
                    reply_markup=subscribe_kb(not_subbed, file_db_id),
                    parse_mode="HTML",
                )
                return

        # Fayl yuborish
        await message.answer("✅ <b>Mana sizning faylingiz!</b>", parse_mode="HTML")
        await send_file_to_user(bot, message.chat.id, file_data)
        return

    # ── Oddiy /start (deep-link yo'q) ──────────────────────────────────────
    if is_super:
        # Super admin — /admin ga yo'llash
        await message.answer(
            "👑 Xush kelibsiz, <b>Super Admin</b>!\n\n"
            "🛠 Botni boshqarish uchun: /admin\n"
            "📁 Fayl yuklash paneli: /panel",
            parse_mode="HTML",
        )
        return

    if is_subadmin:
        # Sub-admin — /panel ga yo'llash
        await message.answer(
            f"🛡 Xush kelibsiz, <b>Admin</b>!\n\n"
            "📤 Fayl yuklash va link olish uchun: /panel",
            parse_mode="HTML",
        )
        return

    # Oddiy foydalanuvchi
    await db.add_user(user.id, user.username, user.full_name)
    channels  = await db.get_all_channels()
    ch_count  = len(channels)

    await message.answer(
        f"👋 Salom, <b>{user.full_name}</b>!\n\n"
        "🤖 Bu bot orqali maxsus havola yordamida\n"
        "video, audio va hujjatlarni yuklab olishingiz mumkin.\n\n"
        f"📢 Majburiy obuna kanallari: <b>{ch_count} ta</b>\n\n"
        "💡 <i>Fayl olish uchun sizga yuborilgan havolani bosing.</i>",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════
#  "🔄 A'zolikni tekshirish" callback
# ══════════════════════════════════════════════
@router.callback_query(F.data.startswith("check_sub:"))
async def callback_check_sub(call: CallbackQuery, bot: Bot) -> None:
    if call.from_user is None or call.message is None:
        return

    file_db_id = int(call.data.split(":")[1])  # type: ignore[union-attr]
    user_id    = call.from_user.id

    # Fayl ma'lumotini olish (admin kanallarini bilish uchun)
    file_data = await db.get_file(file_db_id)
    if file_data is None:
        await call.answer("❌ Fayl topilmadi yoki o'chirilgan!", show_alert=True)
        return

    not_subbed = await check_subscriptions_for_file(bot, user_id, file_data)

    if not_subbed:
        await call.answer(
            "⚠️ Siz hali barcha kanallarga a'zo emassiz!\n"
            "Iltimos, kanallarga a'zo bo'lib, qayta tekshiring.",
            show_alert=True,
        )
        try:
            await call.message.edit_reply_markup(
                reply_markup=subscribe_kb(not_subbed, file_db_id)
            )
        except Exception:
            pass
        return

    # Barcha kanallarga a'zo — faylni yuborish
    await call.answer("✅ Tabrik! Fayl yuborilmoqda...", show_alert=False)
    try:
        await call.message.delete()
    except Exception:
        pass
    await bot.send_message(
        call.message.chat.id,
        "✅ <b>Mana sizning faylingiz!</b>",
        parse_mode="HTML",
    )
    await send_file_to_user(bot, call.message.chat.id, file_data)
