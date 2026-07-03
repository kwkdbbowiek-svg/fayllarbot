# 📁 Fayllar Bot

Telegram uchun **File-Storage & Link Generator** bot.  
Fayllarni majburiy obuna orqali tarqatuvchi bot.

## ⚙️ Texnologiyalar

- Python 3.10+
- aiogram 3.x (async)
- SQLite + aiosqlite
- Railway deployment

## 🚀 Railway ga Deploy

1. GitHub reponi Railway ga ulang
2. **Variables** bo'limida quyidagilarni kiriting:

```
BOT_TOKEN=your_bot_token_here
SUPER_ADMIN_ID=your_telegram_id
```

3. Deploy — tayyor!

## 👥 Rollar

| Rol | Imkoniyatlar |
|-----|-------------|
| 👑 Super Admin | Hamma narsani boshqaradi |
| 🛡 Sub-Admin | Fayl yuklaydi, link oladi, o'z kanallarini boshqaradi |
| 👤 Foydalanuvchi | Havola orqali fayl yuklab oladi |

## 📌 Buyruqlar

- `/start` — Botni boshlash
- `/admin` — Super admin paneli
- `/panel` — Admin paneli
- `/myfiles` — Mening fayllarim
- `/help` — Qo'llanma
