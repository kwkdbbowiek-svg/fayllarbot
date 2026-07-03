"""
Sub-Admin handlerlari (kanal egalari).
Imkoniyatlar:
  - /panel      — admin paneli
  - /myfiles    — o'z fayllarini ko'rish
  - /help       — qo'llanma
  - Fayl yuborish → link olish
  - O'z majburiy kanallarini qo'shish / o'chirish / ko'rish (limitga bog'liq)
"""

import logging
import aiosqlite

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db
from bot_config import SUPER_ADMIN_ID, DB_PATH
from keyboards import (
    sub_admin_main_kb,
    sub_admin_channels_kb,
    back_to_sub_admin_kb,
)

logger = logging.getLogger(__name__)
router = Router()


# ──────────────────────────────────────────────
# FSM holatlari
# ──────────────────────────────────────────────
class SubAdminFSM(StatesGroup):
    # Kanal qo'shish
    add_ch_id   = State()
    add_ch_name = State()
    add_ch_link = State()
    # Kanal o'chirish
    remove_ch_id = State()


# ──────────────────────────────────────────────
# Yordamchi
# ──────────────────────────────────────────────
async def _is_any_admin(user_id: int) -> bool:
    if user_id == SUPER_ADMIN_ID:
        return True
    return await db.is_sub_admin(user_id)


# ══════════════════════════════════════════════
#  /cancel
# ══════════════════════════════════════════════
@router.message(Command("cancel"))
async def subadmin_cancel(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not await _is_any_admin(message.from_user.id):
        return
    current = await state.get_state()
    if current is None:
        await message.answer("⚠️ Hozir aktiv jarayon yo'q.")
        return
    await state.clear()
    await message.answer("🚫 Bekor qilindi.", reply_markup=sub_admin_main_kb())


# ══════════════════════════════════════════════
#  /panel
# ══════════════════════════════════════════════
@router.message(Command("panel"))
async def subadmin_panel(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    if not await _is_any_admin(message.from_user.id):
        await message.answer(
            "⛔ Sizda bu buyruqdan foydalanish huquqi yo'q.\n\n"
            "Admin bo'lish uchun bot egasiga murojaat qiling."
        )
        return

    await state.clear()
    limit       = await db.get_max_sub_channels()
    my_ch_count = await db.count_sub_admin_channels(message.from_user.id)

    await message.answer(
        f"🛡 <b>Admin paneli</b>\n\n"
        f"👋 Salom, <b>{message.from_user.full_name}</b>!\n\n"
        f"📢 Sizning kanallaringiz: <b>{my_ch_count} / {limit}</b>\n\n"
        "📤 Menga <b>video, hujjat, audio yoki rasm</b> yuboring —\n"
        "men uni saqlab, tarqatish havolasini beraman.\n\n"
        "📌 /myfiles — fayllarim | /help — qo'llanma",
        reply_markup=sub_admin_main_kb(),
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════
#  /myfiles
# ══════════════════════════════════════════════
@router.message(Command("myfiles"))
async def subadmin_myfiles_cmd(message: Message, bot: Bot) -> None:
    if message.from_user is None or not await _is_any_admin(message.from_user.id):
        return

    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute(
            "SELECT id, file_type, caption, upload_date FROM files "
            "WHERE uploaded_by = ? ORDER BY id DESC LIMIT 20",
            (message.from_user.id,),
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await message.answer("📁 Siz hali hech qanday fayl yuklamagansiz.")
        return

    me    = await bot.get_me()
    lines = [f"📁 <b>Sizning so'nggi {len(rows)} ta faylingiz:</b>\n"]
    for row in rows:
        fid, ftype, cap, date = row
        link  = f"https://t.me/{me.username}?start={fid}"
        emoji = {"video": "🎬", "document": "📄", "audio": "🎵", "photo": "🖼"}.get(ftype, "📁")
        lines.append(
            f"{emoji} <b>#{fid}</b> | {ftype} | {date[:10]}\n"
            f"   📝 {cap or '—'}\n"
            f"   🔗 <code>{link}</code>"
        )

    await message.answer(
        "\n\n".join(lines),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ══════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════
@router.message(Command("help"))
async def subadmin_help_cmd(message: Message) -> None:
    if message.from_user is None or not await _is_any_admin(message.from_user.id):
        return

    limit = await db.get_max_sub_channels()
    await message.answer(
        "📖 <b>Admin qo'llanmasi</b>\n\n"
        "1️⃣ Menga fayl (video, hujjat, audio, rasm) yuboring\n"
        "2️⃣ Men faylni saqlab, tarqatish havolasini beraman\n"
        "3️⃣ Havolani kanalingizga yoki do'stlaringizga tarqating\n"
        "4️⃣ Foydalanuvchi havola orqali kirganda obuna tekshiriladi\n"
        "5️⃣ A'zo bo'lgach, fayl avtomatik yuboriladi\n\n"
        f"📢 <b>Majburiy obuna kanallari:</b>\n"
        f"Siz o'zingizning {limit} tagacha kanalingizni qo'sha olasiz.\n"
        "Panel → 📢 Mening kanallarim bo'limi orqali boshqaring.\n\n"
        "📌 <b>Buyruqlar:</b>\n"
        "• /panel — Admin paneli\n"
        "• /myfiles — Fayllarim\n"
        "• /help — Ushbu qo'llanma\n"
        "• /cancel — Jarayonni bekor qilish",
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════
#  Fayl yuklovchi handler
# ══════════════════════════════════════════════
@router.message(F.content_type.in_({"video", "document", "audio", "photo"}))
async def handle_file_upload(message: Message, bot: Bot) -> None:
    if message.from_user is None:
        return
    if not await _is_any_admin(message.from_user.id):
        return  # user.py ga o'tadi

    caption = message.caption or ""

    if message.video:
        file_id, file_type, emoji = message.video.file_id, "video", "🎬"
    elif message.document:
        file_id, file_type, emoji = message.document.file_id, "document", "📄"
    elif message.audio:
        file_id, file_type, emoji = message.audio.file_id, "audio", "🎵"
    elif message.photo:
        file_id, file_type, emoji = message.photo[-1].file_id, "photo", "🖼"
    else:
        return

    db_id = await db.save_file(file_id, file_type, caption, message.from_user.id)
    me    = await bot.get_me()
    link  = f"https://t.me/{me.username}?start={db_id}"

    await message.answer(
        f"{emoji} <b>Fayl saqlandi!</b>\n\n"
        f"🆔 Raqam: <code>{db_id}</code>\n"
        f"📁 Turi: <b>{file_type}</b>\n"
        f"📝 Izoh: {caption if caption else '<i>yo\'q</i>'}\n\n"
        f"🔗 <b>Tarqatish havolasi:</b>\n"
        f"<code>{link}</code>\n\n"
        f"💡 <i>Foydalanuvchilar havola orqali kirib, kanalingizga a'zo bo'lishadi.</i>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ══════════════════════════════════════════════
#  KANAL BOSHQARUVI — callback menyusi
# ══════════════════════════════════════════════
@router.callback_query(F.data == "subadmin_channels")
async def cb_channels_menu(call: CallbackQuery) -> None:
    if call.from_user is None or not await _is_any_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    limit       = await db.get_max_sub_channels()
    my_ch_count = await db.count_sub_admin_channels(call.from_user.id)

    await call.message.edit_text(  # type: ignore[union-attr]
        f"📢 <b>Mening majburiy obuna kanallarim</b>\n\n"
        f"📊 Holat: <b>{my_ch_count} / {limit}</b> kanal\n\n"
        "Bu kanallar foydalanuvchilar fayl olishdan oldin tekshiriladi.\n\n"
        "Amalni tanlang:",
        reply_markup=sub_admin_channels_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ── Kanallar ro'yxati ──────────────────────────
@router.callback_query(F.data == "sach_list")
async def cb_my_channels_list(call: CallbackQuery) -> None:
    if call.from_user is None or not await _is_any_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    channels    = await db.get_sub_admin_channels(call.from_user.id)
    limit       = await db.get_max_sub_channels()

    if not channels:
        text = (
            f"📋 Sizda hali majburiy obuna kanallari yo'q.\n\n"
            f"📊 Limit: <b>0 / {limit}</b>\n\n"
            "➕ Kanal qo'shish tugmasini bosing."
        )
    else:
        lines = [f"📋 <b>Sizning majburiy kanallaringiz ({len(channels)}/{limit}):</b>\n"]
        for i, ch in enumerate(channels, 1):
            lines.append(
                f"{i}. <b>{ch['channel_name']}</b>\n"
                f"   🆔 ID: <code>{ch['channel_id']}</code>\n"
                f"   🔗 {ch['invite_link']}"
            )
        text = "\n\n".join(lines)

    await call.message.edit_text(  # type: ignore[union-attr]
        text,
        reply_markup=sub_admin_channels_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await call.answer()


# ── Kanal qo'shish: boshlash ───────────────────
@router.callback_query(F.data == "sach_add")
async def cb_add_channel_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not await _is_any_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    limit       = await db.get_max_sub_channels()
    my_ch_count = await db.count_sub_admin_channels(call.from_user.id)

    if my_ch_count >= limit:
        await call.answer(
            f"⛔ Kanal limiti to'ldi! ({my_ch_count}/{limit})\n"
            "Yangi kanal qo'shish uchun eskisini o'chiring\n"
            "yoki bot egasidan limit oshirishni so'rang.",
            show_alert=True,
        )
        return

    await call.message.edit_text(  # type: ignore[union-attr]
        f"➕ <b>Yangi kanal qo'shish</b>\n\n"
        f"📊 Holat: <b>{my_ch_count} / {limit}</b>\n\n"
        "⚠️ <i>Bot o'sha kanalda admin bo'lishi shart!</i>\n\n"
        "Kanal <b>ID</b> sini yuboring\n"
        "(masalan: <code>-1001234567890</code>)\n\n"
        "Bekor qilish: /cancel",
        parse_mode="HTML",
        reply_markup=None,
    )
    await state.set_state(SubAdminFSM.add_ch_id)
    await call.answer()


@router.message(SubAdminFSM.add_ch_id)
async def fsm_add_ch_id(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not await _is_any_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        await message.answer("❌ Noto'g'ri format. Kanal ID raqam bo'lishi kerak:")
        return

    # Limitni qayta tekshirish
    limit       = await db.get_max_sub_channels()
    my_ch_count = await db.count_sub_admin_channels(message.from_user.id)
    if my_ch_count >= limit:
        await state.clear()
        await message.answer(
            f"⛔ Limit to'ldi ({my_ch_count}/{limit}). Bekor qilindi.",
            reply_markup=sub_admin_channels_kb(),
        )
        return

    await state.update_data(ch_id=int(text))
    await state.set_state(SubAdminFSM.add_ch_name)
    await message.answer(
        "✅ ID qabul qilindi.\n\n"
        "Kanal <b>nomini</b> yuboring (masalan: <b>Kino Kanal</b>):",
        parse_mode="HTML",
    )


@router.message(SubAdminFSM.add_ch_name)
async def fsm_add_ch_name(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not await _is_any_admin(message.from_user.id):
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Kanal nomi bo'sh bo'lmasin:")
        return

    await state.update_data(ch_name=name)
    await state.set_state(SubAdminFSM.add_ch_link)
    await message.answer(
        "✅ Nom qabul qilindi.\n\n"
        "Kanal <b>taklif havolasi</b>ni yuboring\n"
        "(masalan: <code>https://t.me/+xxxxxxxxxxxx</code>):",
        parse_mode="HTML",
    )


@router.message(SubAdminFSM.add_ch_link)
async def fsm_add_ch_link(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not await _is_any_admin(message.from_user.id):
        return

    link = (message.text or "").strip()
    if not link.startswith("http"):
        await message.answer("❌ Noto'g'ri havola. https:// bilan boshlangan havola yuboring:")
        return

    data    = await state.get_data()
    admin_id = message.from_user.id
    await state.clear()

    success = await db.add_sub_admin_channel(
        admin_id=admin_id,
        channel_id=data["ch_id"],
        channel_name=data["ch_name"],
        invite_link=link,
    )

    if success:
        limit       = await db.get_max_sub_channels()
        my_ch_count = await db.count_sub_admin_channels(admin_id)
        await message.answer(
            f"✅ <b>Kanal qo'shildi!</b>\n\n"
            f"📢 Nom: <b>{data['ch_name']}</b>\n"
            f"🆔 ID: <code>{data['ch_id']}</code>\n"
            f"🔗 {link}\n\n"
            f"📊 Holat: <b>{my_ch_count} / {limit}</b>",
            reply_markup=sub_admin_channels_kb(),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    else:
        limit       = await db.get_max_sub_channels()
        my_ch_count = await db.count_sub_admin_channels(admin_id)
        if my_ch_count >= limit:
            reason = f"limit to'ldi ({my_ch_count}/{limit})"
        else:
            reason = "bu kanal ID allaqachon ro'yxatda bor"
        await message.answer(
            f"❌ <b>Kanal qo'shilmadi:</b> {reason}.\n\n"
            "Boshqa kanal ID kiriting yoki eskisini o'chiring.",
            reply_markup=sub_admin_channels_kb(),
            parse_mode="HTML",
        )


# ── Kanal o'chirish: boshlash ──────────────────
@router.callback_query(F.data == "sach_remove")
async def cb_remove_channel_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not await _is_any_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    channels = await db.get_sub_admin_channels(call.from_user.id)
    if not channels:
        await call.answer("📋 O'chirish uchun kanallar yo'q.", show_alert=True)
        return

    lines = ["➖ <b>Kanal o'chirish</b>\n\nO'chirmoqchi bo'lgan kanal ID sini yuboring:\n"]
    for ch in channels:
        lines.append(f"• <b>{ch['channel_name']}</b> — <code>{ch['channel_id']}</code>")
    lines.append("\nBekor qilish: /cancel")

    await call.message.edit_text(  # type: ignore[union-attr]
        "\n".join(lines),
        reply_markup=None,
        parse_mode="HTML",
    )
    await state.set_state(SubAdminFSM.remove_ch_id)
    await call.answer()


@router.message(SubAdminFSM.remove_ch_id)
async def fsm_remove_ch_id(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not await _is_any_admin(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        await message.answer("❌ Noto'g'ri format. Kanal ID raqam bo'lishi kerak:")
        return

    ch_id    = int(text)
    admin_id = message.from_user.id
    await state.clear()

    removed = await db.remove_sub_admin_channel(admin_id, ch_id)
    if removed:
        limit       = await db.get_max_sub_channels()
        my_ch_count = await db.count_sub_admin_channels(admin_id)
        await message.answer(
            f"✅ Kanal (<code>{ch_id}</code>) o'chirildi.\n\n"
            f"📊 Holat: <b>{my_ch_count} / {limit}</b>",
            reply_markup=sub_admin_channels_kb(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"❌ <code>{ch_id}</code> ID li kanal topilmadi yoki siz qo'shmagansiz.",
            reply_markup=sub_admin_channels_kb(),
            parse_mode="HTML",
        )


# ══════════════════════════════════════════════
#  Panelga qaytish callback
# ══════════════════════════════════════════════
@router.callback_query(F.data == "subadmin_back")
async def cb_back_to_panel(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not await _is_any_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    await state.clear()
    limit       = await db.get_max_sub_channels()
    my_ch_count = await db.count_sub_admin_channels(call.from_user.id)

    await call.message.edit_text(  # type: ignore[union-attr]
        f"🛡 <b>Admin paneli</b>\n\n"
        f"📢 Kanallaringiz: <b>{my_ch_count} / {limit}</b>\n\n"
        "📤 Fayl yuboring — havola olasiz.\n"
        "📌 /myfiles — fayllarim | /help — qo'llanma",
        reply_markup=sub_admin_main_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ══════════════════════════════════════════════
#  Inline callback-lar (fayllar, yordam)
# ══════════════════════════════════════════════
@router.callback_query(F.data == "subadmin_myfiles")
async def cb_my_files(call: CallbackQuery, bot: Bot) -> None:
    if call.from_user is None or not await _is_any_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    async with aiosqlite.connect(DB_PATH) as db_conn:
        async with db_conn.execute(
            "SELECT id, file_type, caption, upload_date FROM files "
            "WHERE uploaded_by = ? ORDER BY id DESC LIMIT 20",
            (call.from_user.id,),
        ) as cur:
            rows = await cur.fetchall()

    if not rows:
        await call.answer("📁 Fayllar yo'q.", show_alert=True)
        return

    me    = await bot.get_me()
    lines = [f"📁 <b>Sizning so'nggi {len(rows)} ta faylingiz:</b>\n"]
    for row in rows:
        fid, ftype, cap, date = row
        link  = f"https://t.me/{me.username}?start={fid}"
        emoji = {"video": "🎬", "document": "📄", "audio": "🎵", "photo": "🖼"}.get(ftype, "📁")
        lines.append(
            f"{emoji} <b>#{fid}</b> | {ftype} | {date[:10]}\n"
            f"   📝 {cap or '—'}\n"
            f"   🔗 <code>{link}</code>"
        )

    await call.message.answer(  # type: ignore[union-attr]
        "\n\n".join(lines),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await call.answer()


@router.callback_query(F.data == "subadmin_help")
async def cb_help(call: CallbackQuery) -> None:
    if call.from_user is None or not await _is_any_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    limit = await db.get_max_sub_channels()
    await call.message.answer(  # type: ignore[union-attr]
        "📖 <b>Admin qo'llanmasi</b>\n\n"
        "1️⃣ Fayl yuboring → havola olasiz\n"
        "2️⃣ Havolani kanalga yoki do'stlarga tarqating\n"
        "3️⃣ Foydalanuvchi kirib, kanalingizga a'zo bo'ladi\n"
        "4️⃣ A'zo bo'lgach, fayl avtomatik yuboriladi\n\n"
        f"📢 Siz o'zingizning <b>{limit} tagacha</b> kanalingizni\n"
        "qo'sha olasiz → 📢 Mening kanallarim bo'limidan.\n\n"
        "📌 /myfiles — fayllarim\n"
        "📌 /cancel — jarayonni bekor qilish",
        parse_mode="HTML",
    )
    await call.answer()
