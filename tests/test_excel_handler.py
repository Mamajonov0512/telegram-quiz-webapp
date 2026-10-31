# Dars Jadvali Telegram Boti

Ushbu loyiha Telegram bot orqali o‘qituvchi va guruh bo‘yicha dars jadvalini ko‘rsatish va administrator uchun Excel importini boshqarish uchun yaratilgan.

## Asosiy xususiyatlar

- `/start` bosh menyu
- O‘qituvchi bo‘yicha qidirish
- Guruh bo‘yicha qidirish
- Bugungi, haftalik va oylik dars jadvallari
- Administrator uchun Excel faylni tekshirish va import qilish
- Supabase uchun SQL schema va row-level security
- Vercel webhook endpointi

## O‘rnatish

1. Virtual muhit yarating:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Kutubxonalarni o‘rnating:
   ```bash
   pip install -r requirements.txt
   ```
3. `.env` faylini `.env.example` dan nusxalab yarating va qiymatlarni to‘ldiring.
4. Botni ishga tushiring:
   ```bash
   python main.py
   ```

## Supabase schema

`supabase_schema.sql` faylida `users`, `schedule_periods`, `schedule_imports`, `schedules` jadvallari va indekslar mavjud.

## Vercel

- `WEBHOOK_URL` va `WEBHOOK_SECRET` o‘rnatiladi.
- `api/index.py` Telegram webhook endpointi sifatida ishlatiladi.
- Doimiy polling serverless muhitda ishlatilmaydi; polling uchun alohida worker yoki lokal server kerak bo‘lishi mumkin.

## Testlar

```bash
pytest -q
```

## Eslatma

Bu repo mavjud quiz appdan yangilanib, schedule bot strukturasi bilan mustahkamlandi. Real token va Supabase secrets ishlatmasdan oldin `.env` faylini to‘ldiring.
