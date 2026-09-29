# 🚀 Telegram Web App Test Platformasi

Telegram messenjeri uchun yaratilgan zamonaviy, qulay va to'liq interaktiv **Telegram Web App (Mini App)** test topshirish tizimi.

---

## 🌟 Asosiy Imkoniyatlar

1. **📱 Telegram Web App (Mini App) Interfeysi**:
   - Telegram ilovasi ichida to'liq ekranli mobil interfeys.
   - Telegram mavzulari (qorong'i/yorug' rejim) bilan avtomatik moslashuv.
   - Haptic feedback (tugmalarni bosganda taktil tebranish sezgisi).

2. **⏱️ 50 ta Test va Jonli Taymer ("vaqt ketsin")**:
   - Standart 50 ta savol (admin panel orqali savollar sonini o'zgartirish mumkin).
   - Real vaqtli hisoblagich taymer (masalan, 50 daqiqa).
   - Vaqt tugashiga 5 daqiqa qolganda ogohlantiruvchi rang o'zgarishi, 2 daqiqa qolganda pulsatsiyalovchi qizil signal.
   - Vaqt 00:00 bo'lganda test avtomatik ravishda yakunlanadi va saqlanadi.

3. **📌 Qulay Test Ishlash Mexanizmi**:
   - 1 dan 50 gacha savollar jadvali (Question Palette drawer).
   - Rangli belgilar:
     - 🟢 Yashil: Javob berilgan
     - 🟡 Sariq (★): Keyinroq qaytish uchun belgilab qo'yilgan (Flagged)
     - ⚪ Kulrang: Hali javob berilmagan
     - 🔵 Moviy: Hozirgi ochiq savol
   - Istalgan savolga bir zumda sakrash imkoniyati.
   - Testni yakunlashdan oldin javobsiz qolgan savollar soni haqida ogohlantirish oynasi.

4. **📁 Fayl Orqali Testlarni Kiritish**:
   - **Excel (.xlsx)**: Savol, Variant A, B, C, D, To'g'ri javob, Izoh, Kategoriya ustunlari.
   - **Word (.docx)**: Savollar va variantlar matni.
   - **JSON (.json)**: Strukturalangan ma'lumotlar.
   - **Oddiy Matn (.txt)**: Qulay formatdagi matnli fayl.
   - *Yuklash usullari:*
     - Administrator botga faylni to'g'ridan-to'g'ri yuborishi mumkin.
     - Veb Admin panel orqali Drag & Drop usulida fayl yuklash.

5. **🔐 Telegram ID Orqali Ruxsat Berish (Whitelist Tizimi)**:
   - Cheklangan kirish: Faqat administrator tomonidan ruxsat berilgan Telegram ID egalari test topshira oladi.
   - Ruxsatsiz foydalanuvchi kirganda chiroyli blokirovka ekrani chiqadi:
     - Foydalanuvchining shaxsiy Telegram ID raqami ko'rsatiladi.
     - ID raqamini bir marta bosish bilan nusxalash tugmasi mavjud.
   - Admin ruxsatlarni boshqarishi mumkin:
     - Bot orqali: `/add <telegram_id> [Ism]`, `/del <telegram_id>`, `/users`
     - Veb Admin panel orqali: interaktiv jadval, faol/nofaol almashtirgich, qidiruv.
     - Rejimni almashtirish: "Faqat ruxsat berilganlar" yoki "Hammaga ochiq".

6. **📊 Natijalar Tahlili va Xatolar Ustida Ishlash**:
   - Test yakunlangach darhol ball, foiz, sarflangan vaqt va "O'tdi/O'tmadi" xulosasi.
   - Har bir savol bo'yicha batafsil tahlil:
     - Sizning javobingiz
     - To'g'ri javob
     - Tushuntirish / Izoh (agar mavjud bo'lsa)
   - Filtrlash: "Barchasi", "Faqat xatolar", "To'g'ri javoblar".

7. **📈 Chuqur Analitika va Excel Hisoboti (Yangi!)**:
   - **Admin uchun**:
     - Umumiy o'zlashtirish foizi, o'tish ko'rsatkichi (Pass Rate %), o'rtacha vaqt.
     - **Ballar taqsimoti grafikasi**: 80-100% (A'lo), 60-79% (Yaxshi), 40-59% (Past), 0-39% (Qoniqarsiz).
     - **Eng ko'p xato qilingan savollar (Qiyin savollar tahlili)**: qaysi savolda ishtirokchilar ko'proq adashganini foizlarda aniqlash.
     - **Fanlar/Kategoriyalar tahlili**: fanlar kesimida o'zlashtirish foizlari.
     - **Reyting (Leaderboard)**: eng yuqori ball to'plagan Top-10 qatnashchilar.
     - **📥 Excel hisoboti (.xlsx)**: 3 ta varaqdan iborat (Barcha natijalar, Reyting, Qiyin savollar tahlili) to'liq Excel faylini bir bosishda yuklab olish (Web paneldan yoki botdagi `/analytics` buyrug'i orqali).
   - **Foydalanuvchi uchun (Web App ichida)**:
     - Shaxsiy o'sish dinamikasi (eng yuqori ball, o'rtacha ball).
     - Fanlar bo'yicha kuchli va zaif mavzular tahlili (masalan: "Tarix: 90% A'lo", "Fizika: 40% Zaif - ko'proq takrorlang!").

---

## 📂 Loyiha Tuzilishi

```
├── .env.example            # Sozlamalar namunasi
├── .env                    # Maxfiy tokenlar va sozlamalar
├── config.py               # Loyiha konfiguratsiyasi
├── database.py             # SQLite ma'lumotlar bazasi boshqaruvi
├── parser.py               # Excel, Word, JSON, TXT fayl tahlilchisi
├── bot.py                  # Aiogram 3 Telegram boti
├── api.py                  # FastAPI veb-server va REST API
├── main.py                 # Bot va serverni bir vaqtda yurgizuvchi fayl
├── seed_data.py            # Bazaga namunaviy 50 ta savol yuklovchi skript
├── samples/                # Shablon namunaviy fayllar (.xlsx, .json, .txt)
├── static/
│   ├── css/
│   │   ├── style.css       # Web App dizayni
│   │   └── admin.css       # Admin panel dizayni
│   └── js/
│       ├── app.js          # Web App mijoz logikasi
│       └── admin.js        # Admin panel logikasi
└── templates/
    ├── index.html          # Web App asosiy sahifasi
    └── admin.html          # Admin panel sahifasi
```

---

## ⚡ O'rnatish va Ishga Tushirish

### 1. Talablar:
- Python 3.10 yoki undan yuqori versiya.

### 2. Kutubxonalarni o'rnatish:
Agar venv mavjud bo'lmasa:
```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 3. `.env` Faylini Sozlash:
`.env` faylini oching va ma'lumotlarni kiriting:
```ini
# Telegram Bot Token (@BotFather dan olinadi)
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRstuVWXyz

# Administratorlarning Telegram ID raqamlari (vergul bilan)
ADMIN_IDS=12345678

# Web App URL (Telegram Web App uchun HTTPS havola)
# Mahalliy tekshirish uchun: http://localhost:8000
WEB_APP_URL=https://sizning-domen-yoki-ngrok.com

# Server sozlamalari
HOST=0.0.0.0
PORT=8000

# Veb Admin panel paroli
ADMIN_SECRET_KEY=admin12345

# Standart sozlamalar
TEST_QUESTIONS_COUNT=50
TEST_DURATION_MINUTES=50
```

### 4. Dasturni Ishga Tushirish:
```powershell
.\venv\Scripts\python main.py
```
Dastur ishga tushgach:
- **Web App**: `http://localhost:8000`
- **Admin Panel**: `http://localhost:8000/admin`
- **Telegram Bot**: Polling rejimida xabarlarni qabul qiladi.

---

## 🤖 Telegram @BotFather Orqali Web App Ulash

1. Telegramda [@BotFather](https://t.me/BotFather) botini oching.
2. `/newbot` buyrug'i orqali yangi bot yarating va uning `token`ini `.env` dagi `BOT_TOKEN` ga qo'ying.
3. Web App menyu tugmasini ulash:
   - `/setmenubutton` buyrug'ini yuboring.
   - Botingizni tanlang.
   - Tugma matnini kiriting: `🚀 Test topshirish`
   - Web App URL manzilini kiriting: `https://sizning-domen.com` (yoki ngrok HTTPS havolasi).
4. Yoki inline Web App yaratish uchun:
   - `/newapp` buyrug'ini yuboring.
   - Ko'rsatmalarga asosan qisqa nom va havolani kiriting.

---

## 📁 Fayl Orqali Savollarni Tayyorlash Formatlari

### 1. Excel (.xlsx) Formati:
Ustunlar tartibi:
| Savol | Variant A | Variant B | Variant C | Variant D | To'g'ri javob | Izoh | Kategoriya |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| O'zbekiston poytaxti qaysi? | Samarqand | Toshkent | Buxoro | Xiva | B | Toshkent - poytaxt | Geografiya |

### 2. Oddiy Matn (.txt) yoki Word (.docx) Formati:
```txt
1. O'zbekiston davlat bayrog'i qachon qabul qilingan?
A) 1991-yil 18-noyabr
B) 1992-yil 8-dekabr
C) 1992-yil 2-iyul
D) 1993-yil 7-may
Javob: A
Izoh: Bayroq 1991-yil 18-noyabrda qabul qilingan.

2. Kompyuterning hisoblash markazi nima deb ataladi?
A) Operativ xotira
B) Protsessor (CPU)
C) Videokarta
D) Monitor
Javob: B
```

*Tayyor shablon namunalarini Admin paneldagi "Savollar va Fayllar" bo'limidan bir bosishda yuklab olishingiz mumkin!*

---

## 🛠️ Bot Buyruqlari

- `/start` — Bosh sahifa (Web App tugmasi va ma'lumotlar).
- `/id` — Foydalanuvchining shaxsiy Telegram ID raqamini ko'rsatish.
- `/admin` — Administrator menyusi (faqat adminlar uchun).
- `/add <id> [Ism]` — Foydalanuvchiga test topshirish uchun ruxsat berish (masalan: `/add 98765432 Jasur`).
- `/del <id>` — Foydalanuvchining ruxsatini bekor qilish.
- `/users` — Ruxsat berilganlar ro'yxatini ko'rish.
