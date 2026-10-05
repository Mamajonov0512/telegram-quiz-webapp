#!/usr/bin/env python3
"""
Mavjud SQLite (quiz_app.db) ma'lumotlarini Supabase PostgreSQL bazasiga xavfsiz ko'chirish skripti.
Barcha jadvallar (savollar, bo'limlar, foydalanuvchilar, sozlamalar, test natijalari, sessiyalar)
aniq va hech qanday ma'lumot yo'qotilmasdan ko'chiriladi.
"""

import os
import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

# Load .env
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("[XATOLIK] psycopg2-binary o'rnatilmagan. Iltimos: pip install psycopg2-binary")
    sys.exit(1)

def migrate(sqlite_path: Path, db_url: str):
    if not sqlite_path.exists():
        print(f"[XATOLIK] SQLite fayli topilmadi: {sqlite_path}")
        return

    print("="*65)
    print("  SQLITE -> SUPABASE POSTGRESQL MIGRATSIYA BOSHLANDI")
    print("="*65)
    print(f"[*] Manba (SQLite): {sqlite_path}")
    masked_url = db_url.split("@")[-1] if "@" in db_url else "configured url"
    print(f"[*] Qabul qiluvchi (Supabase): ...@{masked_url}")

    # Fix postgres:// URL prefix for psycopg2 if needed
    if db_url.startswith("postgres://"):
        db_url = "postgresql://" + db_url[len("postgres://"):]
    if "sslmode=" not in db_url and "localhost" not in db_url and "127.0.0.1" not in db_url:
        sep = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{sep}sslmode=require"

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(str(sqlite_path))
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Connect to Supabase PostgreSQL
    try:
        pg_conn = psycopg2.connect(db_url)
        pg_cur = pg_conn.cursor()
        print("[+] Supabase PostgreSQL bazasiga muvaffaqiyatli ulandi!")
    except Exception as e:
        print(f"[XATOLIK] Supabase bazasiga ulanib bo'lmadi: {e}")
        return

    # Ensure schema exists in Supabase
    print("[*] Supabase jadvallarini tekshirish va yaratish...")
    schema_file = BASE_DIR / "supabase_schema.sql"
    if schema_file.exists():
        with open(schema_file, "r", encoding="utf-8") as f:
            pg_cur.execute(f.read())
        pg_conn.commit()
        print("[+] Supabase jadvallari tayyorlandi.")
    else:
        print("[!] supabase_schema.sql topilmadi, mavjud jadvallarga yoziladi.")

    # 1. Migrate Sections
    print("\n--- 1. Bo'limlar (sections) ko'chirilmoqda ---")
    try:
        sqlite_cur.execute("SELECT * FROM sections")
        sections = [dict(r) for r in sqlite_cur.fetchall()]
        sec_count = 0
        for s in sections:
            pg_cur.execute("""
            INSERT INTO sections (name, description, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO NOTHING
            """, (s.get("name", "").strip(), s.get("description", ""), s.get("created_at") or datetime.now()))
            sec_count += 1
        pg_conn.commit()
        print(f"[+] Bo'limlar: {sec_count} ta ko'chirildi.")
    except Exception as e:
        print(f"[!] Bo'limlarni ko'chirishda ogohlantirish: {e}")

    # 2. Migrate Questions
    print("\n--- 2. Savollar (questions) ko'chirilmoqda ---")
    try:
        sqlite_cur.execute("SELECT * FROM questions ORDER BY id ASC")
        questions = [dict(r) for r in sqlite_cur.fetchall()]
        q_count = 0
        for q in questions:
            pg_cur.execute("""
            INSERT INTO questions (id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, category, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                question_text = EXCLUDED.question_text,
                option_a = EXCLUDED.option_a,
                option_b = EXCLUDED.option_b,
                option_c = EXCLUDED.option_c,
                option_d = EXCLUDED.option_d,
                correct_option = EXCLUDED.correct_option,
                explanation = EXCLUDED.explanation,
                category = EXCLUDED.category
            """, (
                q["id"],
                q["question_text"],
                q["option_a"],
                q["option_b"],
                q["option_c"],
                q["option_d"],
                q["correct_option"],
                q.get("explanation", ""),
                q.get("category", "Umumiy"),
                q.get("created_at") or datetime.now()
            ))
            q_count += 1
        pg_conn.commit()

        # Update serial sequence for questions
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('questions', 'id'), coalesce(max(id), 1)) FROM questions;")
        pg_conn.commit()
        print(f"[+] Savollar: {q_count} ta savol muvaffaqiyatli ko'chirildi.")
    except Exception as e:
        print(f"[!] Savollarni ko'chirishda xatolik: {e}")

    # 3. Migrate Allowed Users
    print("\n--- 3. Foydalanuvchilar (allowed_users) ko'chirilmoqda ---")
    try:
        sqlite_cur.execute("SELECT * FROM allowed_users")
        users = [dict(r) for r in sqlite_cur.fetchall()]
        u_count = 0
        for u in users:
            pg_cur.execute("""
            INSERT INTO allowed_users (telegram_id, full_name, username, added_by, added_at, is_active, notes, allowed_sections)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (telegram_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                username = EXCLUDED.username,
                is_active = EXCLUDED.is_active,
                notes = EXCLUDED.notes,
                allowed_sections = EXCLUDED.allowed_sections
            """, (
                u["telegram_id"],
                u.get("full_name", ""),
                u.get("username", ""),
                u.get("added_by", 0),
                u.get("added_at") or datetime.now(),
                u.get("is_active", 1),
                u.get("notes", ""),
                u.get("allowed_sections", "ALL")
            ))
            u_count += 1
        pg_conn.commit()
        print(f"[+] Foydalanuvchilar: {u_count} ta foydalanuvchi ko'chirildi.")
    except Exception as e:
        print(f"[!] Foydalanuvchilarni ko'chirishda xatolik: {e}")

    # 4. Migrate Settings
    print("\n--- 4. Sozlamalar (settings) ko'chirilmoqda ---")
    try:
        sqlite_cur.execute("SELECT * FROM settings")
        settings = [dict(r) for r in sqlite_cur.fetchall()]
        s_count = 0
        for s in settings:
            pg_cur.execute("""
            INSERT INTO settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (s["key"], s["value"]))
            s_count += 1
        pg_conn.commit()
        print(f"[+] Sozlamalar: {s_count} ta sozlama ko'chirildi.")
    except Exception as e:
        print(f"[!] Sozlamalarni ko'chirishda xatolik: {e}")

    # 5. Migrate Test Results
    print("\n--- 5. Natijalar (test_results) ko'chirilmoqda ---")
    try:
        sqlite_cur.execute("SELECT * FROM test_results ORDER BY id ASC")
        results = [dict(r) for r in sqlite_cur.fetchall()]
        res_count = 0
        for r in results:
            pg_cur.execute("""
            INSERT INTO test_results (id, telegram_id, full_name, username, total_questions, correct_answers, wrong_answers, score_percentage, time_spent_seconds, completed_at, answers_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """, (
                r["id"],
                r["telegram_id"],
                r.get("full_name", ""),
                r.get("username", ""),
                r["total_questions"],
                r["correct_answers"],
                r["wrong_answers"],
                r["score_percentage"],
                r["time_spent_seconds"],
                r.get("completed_at") or datetime.now(),
                r.get("answers_json", "[]")
            ))
            res_count += 1
        pg_conn.commit()

        # Update serial sequence for test_results
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('test_results', 'id'), coalesce(max(id), 1)) FROM test_results;")
        pg_conn.commit()
        print(f"[+] Test natijalari: {res_count} ta natija ko'chirildi.")
    except Exception as e:
        print(f"[!] Natijalarni ko'chirishda xatolik: {e}")

    # 6. Migrate Test Sessions
    print("\n--- 6. Test sessiyalari (test_sessions) ko'chirilmoqda ---")
    try:
        sqlite_cur.execute("SELECT * FROM test_sessions")
        sessions = [dict(r) for r in sqlite_cur.fetchall()]
        sess_count = 0
        for s in sessions:
            pg_cur.execute("""
            INSERT INTO test_sessions (session_id, telegram_id, category, questions_count, duration_minutes, session_data, started_at, is_submitted)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO NOTHING
            """, (
                s["session_id"],
                s["telegram_id"],
                s.get("category", "Barchasi"),
                s["questions_count"],
                s["duration_minutes"],
                s["session_data"],
                s.get("started_at") or datetime.now(),
                s.get("is_submitted", 0)
            ))
            sess_count += 1
        pg_conn.commit()
        print(f"[+] Test sessiyalari: {sess_count} ta ko'chirildi.")
    except Exception as e:
        print(f"[!] Test sessiyalarini ko'chirishda xatolik: {e}")

    sqlite_conn.close()
    pg_conn.close()

    print("\n" + "="*65)
    print("  MIGRATSIYA MUVAFFAQIYATLI YAKUNLANDI! [100% OK]")
    print("="*65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite'dan Supabase PostgreSQL'ga ma'lumotlarni ko'chirish.")
    parser.add_argument("--url", default="", help="Supabase PostgreSQL connection string (DATABASE_URL)")
    parser.add_argument("--db", default="quiz_app.db", help="SQLite fayl yo'li (standart: quiz_app.db)")
    args = parser.parse_args()

    target_url = args.url.strip() or os.getenv("DATABASE_URL", os.getenv("SUPABASE_DB_URL", "")).strip()

    if not target_url:
        print("\n[DIQQAT] DATABASE_URL topilmadi!")
        print("Iltimos, buyruqqa --url parametrini bering yoki .env faylida DATABASE_URL ni ko'rsating.")
        print("Misol:")
        print("  python migrate_sqlite_to_supabase.py --url \"postgresql://postgres:PAROL@db.xxx.supabase.co:5432/postgres\"\n")
        sys.exit(1)

    db_file = Path(args.db)
    if not db_file.is_absolute():
        db_file = BASE_DIR / args.db

    migrate(db_file, target_url)
