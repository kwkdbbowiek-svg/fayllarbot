from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


# ══════════════════════════════════════════════
#  SUPER ADMIN — bosh panel
# ══════════════════════════════════════════════
def super_admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Statistika",            callback_data="sa_stats"))
    builder.row(InlineKeyboardButton(text="👤 Adminlarni boshqarish",  callback_data="sa_admins"))
    builder.row(InlineKeyboardButton(text="📢 Global kanallar",        callback_data="sa_channels"))
    builder.row(InlineKeyboardButton(text="⚙️ Kanal limit sozlamasi",  callback_data="sa_limit"))
    builder.row(InlineKeyboardButton(text="📣 Reklama yuborish",       callback_data="sa_broadcast"))
    return builder.as_markup()


# ── Adminlar boshqaruvi ──
def admins_manage_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Admin qo'shish",    callback_data="admin_add"))
    builder.row(InlineKeyboardButton(text="➖ Admin o'chirish",   callback_data="admin_remove"))
    builder.row(InlineKeyboardButton(text="📋 Adminlar ro'yxati", callback_data="admin_list"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga",            callback_data="sa_back"))
    return builder.as_markup()


# ── Global kanallar boshqaruvi ──
def channels_manage_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish",    callback_data="channel_add"))
    builder.row(InlineKeyboardButton(text="➖ Kanal o'chirish",   callback_data="channel_remove"))
    builder.row(InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data="channel_list"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga",            callback_data="sa_back"))
    return builder.as_markup()


# ── Universal orqaga tugma ──
def back_to_super_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Bosh panel", callback_data="sa_back"))
    return builder.as_markup()


# ══════════════════════════════════════════════
#  SUB-ADMIN panel
# ══════════════════════════════════════════════
def sub_admin_main_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📢 Mening kanallarim",  callback_data="subadmin_channels"))
    builder.row(InlineKeyboardButton(text="📁 Mening fayllarim",   callback_data="subadmin_myfiles"))
    builder.row(InlineKeyboardButton(text="ℹ️ Qo'llanma",          callback_data="subadmin_help"))
    return builder.as_markup()


# ── Sub-admin: kanal boshqaruvi menyusi ──
def sub_admin_channels_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Kanal qo'shish",    callback_data="sach_add"))
    builder.row(InlineKeyboardButton(text="➖ Kanal o'chirish",   callback_data="sach_remove"))
    builder.row(InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data="sach_list"))
    builder.row(InlineKeyboardButton(text="🔙 Orqaga",            callback_data="subadmin_back"))
    return builder.as_markup()


# ── Sub-admin: orqaga panel ──
def back_to_sub_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Panel", callback_data="subadmin_back"))
    return builder.as_markup()


# ══════════════════════════════════════════════
#  MAJBURIY OBUNA tugmalari (foydalanuvchi)
# ══════════════════════════════════════════════
def subscribe_kb(channels: list[dict], file_db_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(
            InlineKeyboardButton(
                text=f"📢 {ch['channel_name']}",
                url=ch["invite_link"],
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="🔄 A'zolikni tekshirish",
            callback_data=f"check_sub:{file_db_id}",
        )
    )
    return builder.as_markup()
