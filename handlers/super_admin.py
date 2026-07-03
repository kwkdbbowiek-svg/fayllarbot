"""
Super Admin handlerlari.
Faqat .env dagi SUPER_ADMIN_ID ruxsat beriladi.
Imkoniyatlar:
  - Statistika
  - Sub-adminlarni qo'shish / o'chirish / ko'rish
  - Majburiy obuna kanallarini qo'shish / o'chirish / ko'rish
  - Barcha foydalanuvchilarga reklama yuborish
"""

import asyncio
import logging

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

import database as db
from config import SUPER_ADMIN_ID
from keyboards import (
    super_admin_main_kb,
    admins_manage_kb,
    channels_manage_kb,
    back_to_super_admin_kb,
)

logger = logging.getLogger(__name__)
router = Router()


# ──────────────────────────────────────────────
# FSM holatlari
# ──────────────────────────────────────────────
class SuperAdminFSM(StatesGroup):
    # Admin qo'shish
    add_admin_id = State()
    # Admin o'chirish
    remove_admin_id = State()
    # Global kanal qo'shish
    add_ch_id = State()
    add_ch_name = State()
    add_ch_link = State()
    # Global kanal o'chirish
    remove_ch_id = State()
    # Kanal limit o'zgartirish
    set_limit = State()
    # Reklama
    broadcast_msg = State()


# ──────────────────────────────────────────────
# Yordamchi
# ──────────────────────────────────────────────
def _is_super(user_id: int) -> bool:
    return user_id == SUPER_ADMIN_ID


# ══════════════════════════════════════════════
#  /cancel — FSM ni istalgan joyda bekor qilish
# ══════════════════════════════════════════════
@router.message(Command("cancel"))
async def sa_cancel(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    current = await state.get_state()
    if current is None:
        await message.answer("⚠️ Hozir aktiv jarayon yo'q.")
        return
    await state.clear()
    await message.answer(
        "🚫 Bekor qilindi.",
        reply_markup=back_to_super_admin_kb(),
    )


# ══════════════════════════════════════════════
#  /admin — bosh panel
# ══════════════════════════════════════════════
@router.message(Command("admin"))
async def sa_cmd_admin(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        await message.answer("⛔ Sizda bu buyruqdan foydalanish huquqi yo'q.")
        return

    await state.clear()
    await message.answer(
        "👑 <b>Super Admin — Bosh boshqaruv paneli</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=super_admin_main_kb(),
        parse_mode="HTML",
    )


# ══════════════════════════════════════════════
#  Statistika
# ══════════════════════════════════════════════
@router.callback_query(F.data == "sa_stats")
async def sa_stats(call: CallbackQuery) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    users_count    = await db.count_users()
    files_count    = await db.count_files()
    sub_admins     = await db.get_all_sub_admins()
    channels       = await db.get_all_channels()
    max_limit      = await db.get_max_sub_channels()

    await call.message.edit_text(  # type: ignore[union-attr]
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👤 Jami foydalanuvchilar: <b>{users_count}</b>\n"
        f"📁 Jami saqlangan fayllar: <b>{files_count}</b>\n"
        f"🛡 Faol sub-adminlar: <b>{len(sub_admins)}</b>\n"
        f"📢 Global majburiy kanallar: <b>{len(channels)}</b>\n"
        f"⚙️ Sub-admin kanal limiti: <b>{max_limit} ta</b>",
        reply_markup=back_to_super_admin_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ══════════════════════════════════════════════
#  ADMINLAR BOSHQARUVI
# ══════════════════════════════════════════════
@router.callback_query(F.data == "sa_admins")
async def sa_admins_menu(call: CallbackQuery) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    await call.message.edit_text(  # type: ignore[union-attr]
        "👤 <b>Adminlarni boshqarish</b>\n\nAmalni tanlang:",
        reply_markup=admins_manage_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ── Adminlar ro'yxati ──────────────────────────
@router.callback_query(F.data == "admin_list")
async def sa_admin_list(call: CallbackQuery) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    admins = await db.get_all_sub_admins()
    if not admins:
        text = "👤 Hozircha sub-adminlar yo'q."
    else:
        lines = ["👤 <b>Sub-adminlar ro'yxati:</b>\n"]
        for i, a in enumerate(admins, 1):
            uname = f"@{a['username']}" if a["username"] else "—"
            lines.append(
                f"{i}. <b>{a['full_name']}</b> ({uname})\n"
                f"   🆔 ID: <code>{a['user_id']}</code>\n"
                f"   📅 Qo'shilgan: {a['added_date']}"
            )
        text = "\n\n".join(lines)

    await call.message.edit_text(  # type: ignore[union-attr]
        text,
        reply_markup=back_to_super_admin_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ── Admin qo'shish ──────────────────────────────
@router.callback_query(F.data == "admin_add")
async def sa_admin_add_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    await call.message.edit_text(  # type: ignore[union-attr]
        "➕ <b>Yangi admin qo'shish</b>\n\n"
        "Admin qilmoqchi bo'lgan foydalanuvchining <b>Telegram ID</b> sini yuboring.\n\n"
        "💡 <i>Foydalanuvchi avval botga /start bosgan bo'lishi kerak.</i>\n\n"
        "Bekor qilish: /cancel",
        parse_mode="HTML",
        reply_markup=None,
    )
    await state.set_state(SuperAdminFSM.add_admin_id)
    await call.answer()


@router.message(SuperAdminFSM.add_admin_id)
async def sa_admin_add_id(message: Message, bot: Bot, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=back_to_super_admin_kb())
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❌ Faqat raqam kiriting (Telegram ID):")
        return

    new_admin_id = int(text)

    # Allaqachon super admin bo'lsa
    if new_admin_id == SUPER_ADMIN_ID:
        await message.answer("⚠️ Bu — siz (Super Admin). Qayta kiritish shart emas.")
        await state.clear()
        return

    # Allaqachon sub-admin bo'lsa
    if await db.is_sub_admin(new_admin_id):
        await message.answer(
            f"⚠️ <code>{new_admin_id}</code> allaqachon admin.",
            parse_mode="HTML",
            reply_markup=back_to_super_admin_kb(),
        )
        await state.clear()
        return

    # Foydalanuvchi ma'lumotlarini Telegram dan olish
    try:
        chat = await bot.get_chat(new_admin_id)
        full_name = chat.full_name or str(new_admin_id)
        username  = chat.username or ""
    except Exception:
        full_name = str(new_admin_id)
        username  = ""

    await db.add_sub_admin(new_admin_id, username, full_name)
    await state.clear()

    # Yangi adminga xabar yuborish
    try:
        await bot.send_message(
            new_admin_id,
            "🎉 <b>Tabriklaymiz!</b>\n\n"
            "Siz ushbu botga <b>Admin</b> sifatida qo'shildingiz!\n\n"
            "Endi siz menga fayl (video, hujjat, audio, rasm) yuborsangiz,\n"
            "men uni saqlab, sizga <b>tarqatish havolasi</b> beraman.\n\n"
            "▶️ Boshlash uchun /panel buyrug'ini yuboring.",
            parse_mode="HTML",
        )
    except Exception:
        pass  # Foydalanuvchi botni bloklagan bo'lishi mumkin

    await message.answer(
        f"✅ <b>{full_name}</b> (<code>{new_admin_id}</code>) admin qilib tayinlandi!",
        reply_markup=back_to_super_admin_kb(),
        parse_mode="HTML",
    )


# ── Admin o'chirish ────────────────────────────
@router.callback_query(F.data == "admin_remove")
async def sa_admin_remove_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    admins = await db.get_all_sub_admins()
    if not admins:
        await call.message.edit_text(  # type: ignore[union-attr]
            "👤 O'chirish uchun adminlar yo'q.",
            reply_markup=back_to_super_admin_kb(),
        )
        await call.answer()
        return

    lines = ["➖ <b>Admin o'chirish</b>\n\nO'chirmoqchi bo'lgan admin ID sini yuboring:\n"]
    for a in admins:
        uname = f"@{a['username']}" if a["username"] else "—"
        lines.append(f"• <b>{a['full_name']}</b> ({uname}) — <code>{a['user_id']}</code>")
    lines.append("\nBekor qilish: /cancel")

    await call.message.edit_text(  # type: ignore[union-attr]
        "\n".join(lines),
        reply_markup=None,
        parse_mode="HTML",
    )
    await state.set_state(SuperAdminFSM.remove_admin_id)
    await call.answer()


@router.message(SuperAdminFSM.remove_admin_id)
async def sa_admin_remove_id(message: Message, bot: Bot, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=back_to_super_admin_kb())
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❌ Faqat raqam kiriting:")
        return

    admin_id = int(text)
    await state.clear()

    removed = await db.remove_sub_admin(admin_id)
    if removed:
        # Adminlikdan olingan odamga xabar
        try:
            await bot.send_message(
                admin_id,
                "ℹ️ Sizning admin huquqingiz bekor qilindi."
            )
        except Exception:
            pass
        await message.answer(
            f"✅ <code>{admin_id}</code> admin ro'yxatidan o'chirildi.",
            reply_markup=back_to_super_admin_kb(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"❌ <code>{admin_id}</code> ID li admin topilmadi.",
            reply_markup=back_to_super_admin_kb(),
            parse_mode="HTML",
        )


# ══════════════════════════════════════════════
#  KANALLAR BOSHQARUVI
# ══════════════════════════════════════════════
@router.callback_query(F.data == "sa_channels")
async def sa_channels_menu(call: CallbackQuery) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    await call.message.edit_text(  # type: ignore[union-attr]
        "📢 <b>Global majburiy obuna kanallari</b>\n\n"
        "Bu kanallar <b>barcha</b> foydalanuvchilar uchun majburiy.\n"
        "Sub-adminlarning o'z kanallari alohida boshqariladi.\n\n"
        "Amalni tanlang:",
        reply_markup=channels_manage_kb(),
        parse_mode="HTML",
    )
    await call.answer()


# ══════════════════════════════════════════════
#  KANAL LIMIT BOSHQARUVI
# ══════════════════════════════════════════════
@router.callback_query(F.data == "sa_limit")
async def sa_limit_menu(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    current_limit = await db.get_max_sub_channels()
    await call.message.edit_text(  # type: ignore[union-attr]
        f"⚙️ <b>Sub-admin kanal limiti</b>\n\n"
        f"Hozirgi limit: <b>{current_limit} ta</b>\n\n"
        f"Har bir sub-admin o'zining majburiy obuna kanallarini\n"
        f"maksimum <b>{current_limit} ta</b> gacha qo'sha oladi.\n\n"
        f"Yangi limitni yuboring (1 dan 20 gacha):\n\n"
        f"Bekor qilish: /cancel",
        reply_markup=None,
        parse_mode="HTML",
    )
    await state.set_state(SuperAdminFSM.set_limit)
    await call.answer()


@router.message(SuperAdminFSM.set_limit)
async def sa_set_limit(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return

    text = (message.text or "").strip()
    if not text.isdigit():
        await message.answer("❌ Faqat musbat raqam kiriting (1-20):")
        return

    new_limit = int(text)
    if not (1 <= new_limit <= 20):
        await message.answer("❌ Limit 1 dan 20 gacha bo'lishi kerak:")
        return

    await db.set_setting("max_sub_channels", str(new_limit))
    await state.clear()

    await message.answer(
        f"✅ <b>Limit yangilandi!</b>\n\n"
        f"Endi har bir sub-admin o'zining majburiy kanallarini\n"
        f"maksimum <b>{new_limit} ta</b> gacha qo'sha oladi.",
        reply_markup=back_to_super_admin_kb(),
        parse_mode="HTML",
    )


# ── Kanallar ro'yxati ──────────────────────────
@router.callback_query(F.data == "channel_list")
async def sa_channel_list(call: CallbackQuery) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    channels = await db.get_all_channels()
    if not channels:
        text = "📋 Hozircha majburiy obuna kanallari yo'q."
    else:
        lines = ["📋 <b>Majburiy obuna kanallari:</b>\n"]
        for i, ch in enumerate(channels, 1):
            lines.append(
                f"{i}. <b>{ch['channel_name']}</b>\n"
                f"   🆔 ID: <code>{ch['channel_id']}</code>\n"
                f"   🔗 {ch['invite_link']}"
            )
        text = "\n\n".join(lines)

    await call.message.edit_text(  # type: ignore[union-attr]
        text,
        reply_markup=back_to_super_admin_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await call.answer()


# ── Kanal qo'shish ─────────────────────────────
@router.callback_query(F.data == "channel_add")
async def sa_channel_add_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    await call.message.edit_text(  # type: ignore[union-attr]
        "➕ <b>Yangi majburiy obuna kanali qo'shish</b>\n\n"
        "⚠️ <i>Bot o'sha kanalda admin bo'lishi shart!</i>\n\n"
        "Kanal <b>ID</b> sini yuboring\n"
        "(masalan: <code>-1001234567890</code>)\n\n"
        "Bekor qilish: /cancel",
        parse_mode="HTML",
        reply_markup=None,
    )
    await state.set_state(SuperAdminFSM.add_ch_id)
    await call.answer()


@router.message(SuperAdminFSM.add_ch_id)
async def sa_ch_id(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=back_to_super_admin_kb())
        return

    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        await message.answer("❌ Noto'g'ri format. Raqam kiriting:")
        return

    await state.update_data(ch_id=int(text))
    await state.set_state(SuperAdminFSM.add_ch_name)
    await message.answer(
        "✅ ID qabul qilindi.\n\nKanal <b>nomini</b> yuboring (masalan: <b>Kino Kanal</b>):",
        parse_mode="HTML",
    )


@router.message(SuperAdminFSM.add_ch_name)
async def sa_ch_name(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=back_to_super_admin_kb())
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("❌ Nom bo'sh bo'lmasin:")
        return

    await state.update_data(ch_name=name)
    await state.set_state(SuperAdminFSM.add_ch_link)
    await message.answer(
        "✅ Nom qabul qilindi.\n\nKanal <b>taklif havolasi</b>ni yuboring\n"
        "(masalan: <code>https://t.me/+xxxxxxxxxxxx</code>):",
        parse_mode="HTML",
    )


@router.message(SuperAdminFSM.add_ch_link)
async def sa_ch_link(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=back_to_super_admin_kb())
        return

    link = (message.text or "").strip()
    if not link.startswith("http"):
        await message.answer("❌ Noto'g'ri havola. https:// bilan boshlangan havola yuboring:")
        return

    data = await state.get_data()
    await state.clear()
    await db.add_channel(data["ch_id"], data["ch_name"], link)

    await message.answer(
        f"✅ <b>Kanal qo'shildi!</b>\n\n"
        f"📢 Nom: <b>{data['ch_name']}</b>\n"
        f"🆔 ID: <code>{data['ch_id']}</code>\n"
        f"🔗 {link}",
        reply_markup=back_to_super_admin_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


# ── Kanal o'chirish ────────────────────────────
@router.callback_query(F.data == "channel_remove")
async def sa_channel_remove_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    channels = await db.get_all_channels()
    if not channels:
        await call.message.edit_text(  # type: ignore[union-attr]
            "📋 O'chirish uchun kanallar yo'q.",
            reply_markup=back_to_super_admin_kb(),
        )
        await call.answer()
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
    await state.set_state(SuperAdminFSM.remove_ch_id)
    await call.answer()


@router.message(SuperAdminFSM.remove_ch_id)
async def sa_ch_remove_id(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=back_to_super_admin_kb())
        return

    text = (message.text or "").strip()
    if not text.lstrip("-").isdigit():
        await message.answer("❌ Noto'g'ri format. Raqam kiriting:")
        return

    ch_id = int(text)
    await state.clear()
    removed = await db.remove_channel(ch_id)

    if removed:
        await message.answer(
            f"✅ <code>{ch_id}</code> kanali o'chirildi.",
            reply_markup=back_to_super_admin_kb(),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            f"❌ <code>{ch_id}</code> ID li kanal topilmadi.",
            reply_markup=back_to_super_admin_kb(),
            parse_mode="HTML",
        )


# ══════════════════════════════════════════════
#  REKLAMA (BROADCAST)
# ══════════════════════════════════════════════
@router.callback_query(F.data == "sa_broadcast")
async def sa_broadcast_start(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    await call.message.edit_text(  # type: ignore[union-attr]
        "📣 <b>Reklama yuborish</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabarni yuboring.\n"
        "<i>(Matn, rasm, video yoki audio bo'lishi mumkin)</i>\n\n"
        "Bekor qilish: /cancel",
        parse_mode="HTML",
        reply_markup=None,
    )
    await state.set_state(SuperAdminFSM.broadcast_msg)
    await call.answer()


@router.message(SuperAdminFSM.broadcast_msg)
async def sa_broadcast_send(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not _is_super(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("🚫 Bekor qilindi.", reply_markup=back_to_super_admin_kb())
        return

    await state.clear()
    user_ids = await db.get_all_user_ids()
    total = len(user_ids)

    progress = await message.answer(
        f"📤 Yuborilmoqda... 0 / {total}",
        parse_mode="HTML",
    )

    sent = failed = blocked = 0

    for i, uid in enumerate(user_ids):
        try:
            await message.copy_to(uid)
            sent += 1
        except TelegramForbiddenError:
            await db.delete_user(uid)
            blocked += 1
        except TelegramBadRequest as e:
            logger.warning(f"Broadcast TelegramBadRequest ({uid}): {e}")
            failed += 1
        except Exception as e:
            logger.error(f"Broadcast xato ({uid}): {e}")
            failed += 1

        # Har 20 ta xabardan keyin 1 soniya pauza (spam blokidan himoya)
        if (i + 1) % 20 == 0:
            await asyncio.sleep(1)

        # Har 50 ta xabardan keyin progress yangilash
        if (i + 1) % 50 == 0:
            try:
                await progress.edit_text(f"📤 Yuborilmoqda... {i+1} / {total}")
            except Exception:
                pass

    await progress.edit_text(
        f"✅ <b>Reklama yakunlandi!</b>\n\n"
        f"📤 Muvaffaqiyatli: <b>{sent}</b>\n"
        f"🚫 Bot bloklagan (bazadan o'chirildi): <b>{blocked}</b>\n"
        f"❌ Xatolik: <b>{failed}</b>",
        parse_mode="HTML",
        reply_markup=back_to_super_admin_kb(),
    )


# ══════════════════════════════════════════════
#  Bosh panelga qaytish
# ══════════════════════════════════════════════
@router.callback_query(F.data == "sa_back")
async def sa_back(call: CallbackQuery, state: FSMContext) -> None:
    if call.from_user is None or not _is_super(call.from_user.id):
        await call.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    await state.clear()
    await call.message.edit_text(  # type: ignore[union-attr]
        "👑 <b>Super Admin — Bosh boshqaruv paneli</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=super_admin_main_kb(),
        parse_mode="HTML",
    )
    await call.answer()
