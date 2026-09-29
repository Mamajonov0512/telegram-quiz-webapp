import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH, ADMIN_IDS, DEFAULT_TEST_QUESTIONS_COUNT, DEFAULT_TEST_DURATION_MINUTES

logger = logging.getLogger(__name__)

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Allowed Users / Whitelist table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS allowed_users (
        telegram_id INTEGER PRIMARY KEY,
        full_name TEXT DEFAULT '',
        username TEXT DEFAULT '',
        added_by INTEGER DEFAULT 0,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        notes TEXT DEFAULT ''
    )
    """)

    # 2. Questions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,  -- 'A', 'B', 'C', or 'D'
        explanation TEXT DEFAULT '',
        category TEXT DEFAULT 'Umumiy',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Test Results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        full_name TEXT DEFAULT '',
        username TEXT DEFAULT '',
        total_questions INTEGER NOT NULL,
        correct_answers INTEGER NOT NULL,
        wrong_answers INTEGER NOT NULL,
        score_percentage REAL NOT NULL,
        time_spent_seconds INTEGER NOT NULL,
        completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        answers_json TEXT DEFAULT '[]'
    )
    """)

    # 4. Settings table (key-value)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Set default settings if not exists
    defaults = {
        "whitelist_enabled": "true",  # Only allowed IDs can test
        "questions_per_test": str(DEFAULT_TEST_QUESTIONS_COUNT),
        "duration_minutes": str(DEFAULT_TEST_DURATION_MINUTES),
        "pass_percentage": "60",
        "shuffle_questions": "true",
        "shuffle_options": "false"
    }

    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Add admin IDs to whitelist automatically
    for admin_id in ADMIN_IDS:
        cursor.execute("""
        INSERT OR IGNORE INTO allowed_users (telegram_id, full_name, username, added_by, notes)
        VALUES (?, 'Administrator', 'admin', 0, 'Asosiy admin')
        """, (admin_id,))

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

# --- SETTINGS HELPERS ---
def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}

# --- ACCESS CONTROL / WHITELIST HELPERS ---
def is_user_allowed(telegram_id: int) -> bool:
    # If admin, always allowed
    if telegram_id in ADMIN_IDS:
        return True
    
    # If whitelist mode is disabled, anyone is allowed
    whitelist_mode = get_setting("whitelist_enabled", "true").lower() == "true"
    if not whitelist_mode:
        return True

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM allowed_users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row and row["is_active"] == 1)

def add_allowed_user(telegram_id: int, full_name: str = "", username: str = "", added_by: int = 0, notes: str = "") -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO allowed_users (telegram_id, full_name, username, added_by, added_at, is_active, notes)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            full_name = excluded.full_name,
            username = excluded.username,
            is_active = 1,
            notes = excluded.notes
        """, (telegram_id, full_name, username, added_by, datetime.now().isoformat(), notes))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding allowed user: {e}")
        return False
    finally:
        conn.close()

def remove_allowed_user(telegram_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM allowed_users WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error removing user: {e}")
        return False
    finally:
        conn.close()

def toggle_user_active(telegram_id: int, is_active: bool) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE allowed_users SET is_active = ? WHERE telegram_id = ?", (1 if is_active else 0, telegram_id))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error toggling user: {e}")
        return False
    finally:
        conn.close()

def get_allowed_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM allowed_users ORDER BY added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- QUESTIONS HELPERS ---
def add_question(question_text: str, option_a: str, option_b: str, option_c: str, option_d: str, 
                 correct_option: str, explanation: str = "", category: str = "Umumiy") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option, explanation, category)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (question_text.strip(), option_a.strip(), option_b.strip(), option_c.strip(), option_d.strip(), 
          correct_option.strip().upper(), explanation.strip(), category.strip()))
    conn.commit()
    q_id = cursor.lastrowid
    conn.close()
    return q_id

def bulk_add_questions(questions_list: List[Dict[str, Any]]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    count = 0
    for q in questions_list:
        try:
            cursor.execute("""
            INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option, explanation, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q.get("question_text", "").strip(),
                q.get("option_a", "").strip(),
                q.get("option_b", "").strip(),
                q.get("option_c", "").strip(),
                q.get("option_d", "").strip(),
                q.get("correct_option", "A").strip().upper(),
                q.get("explanation", "").strip(),
                q.get("category", "Umumiy").strip()
            ))
            count += 1
        except Exception as e:
            logger.error(f"Error inserting question: {e}")
    conn.commit()
    conn.close()
    return count

def get_all_questions(limit: int = 500, offset: int = 0) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_questions_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM questions")
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0

def clear_all_questions() -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions")
    conn.commit()
    conn.close()
    return True

def delete_question(question_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()
    return True

def update_question_category(question_id: int, new_category: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE questions SET category = ? WHERE id = ?", (new_category.strip(), question_id))
    conn.commit()
    conn.close()
    return True

def update_all_questions_category(new_category: str, old_category: Optional[str] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    if old_category:
        cursor.execute("UPDATE questions SET category = ? WHERE category = ?", (new_category.strip(), old_category.strip()))
    else:
        cursor.execute("UPDATE questions SET category = ?", (new_category.strip(),))
    updated_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return updated_rows

def get_test_questions(count: int = 50, shuffle: bool = True) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if shuffle:
        cursor.execute("SELECT * FROM questions ORDER BY RANDOM() LIMIT ?", (count,))
    else:
        cursor.execute("SELECT * FROM questions ORDER BY id ASC LIMIT ?", (count,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# --- TEST RESULTS HELPERS ---
def save_test_result(telegram_id: int, full_name: str, username: str, total_questions: int,
                     correct_answers: int, wrong_answers: int, score_percentage: float,
                     time_spent_seconds: int, answers_json: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO test_results 
    (telegram_id, full_name, username, total_questions, correct_answers, wrong_answers, score_percentage, time_spent_seconds, completed_at, answers_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (telegram_id, full_name, username, total_questions, correct_answers, wrong_answers,
          score_percentage, time_spent_seconds, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), answers_json))
    conn.commit()
    res_id = cursor.lastrowid
    conn.close()
    return res_id

def get_user_results(telegram_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_results WHERE telegram_id = ? ORDER BY id DESC LIMIT ?", (telegram_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_all_results(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM test_results ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total_users FROM allowed_users")
    total_users = cursor.fetchone()["total_users"]

    cursor.execute("SELECT COUNT(*) as total_questions FROM questions")
    total_questions = cursor.fetchone()["total_questions"]

    cursor.execute("SELECT COUNT(*) as total_tests_taken FROM test_results")
    total_tests_taken = cursor.fetchone()["total_tests_taken"]

    cursor.execute("SELECT AVG(score_percentage) as avg_score FROM test_results")
    avg_row = cursor.fetchone()
    avg_score = round(avg_row["avg_score"] or 0, 1)

    conn.close()
    return {
        "total_users": total_users,
        "total_questions": total_questions,
        "total_tests_taken": total_tests_taken,
        "avg_score": avg_score
    }

# --- ADVANCED ANALYTICS FUNCTIONS ---

def get_detailed_analytics() -> Dict[str, Any]:
    """
    Computes comprehensive analytics across all test attempts:
    - Overall summary (participants, tests, avg score, pass rate, avg time)
    - Score distribution (0-39%, 40-59%, 60-79%, 80-100%)
    - Top participants leaderboard
    - Hardest questions (highest error rates)
    - Category accuracy analysis
    - Daily tests trend
    """
    conn = get_connection()
    cursor = conn.cursor()

    pass_percentage = int(get_setting("pass_percentage", "60"))

    # 1. Summary stats
    cursor.execute("""
    SELECT 
        COUNT(*) as total_tests,
        COUNT(DISTINCT telegram_id) as unique_users,
        AVG(score_percentage) as avg_score,
        MAX(score_percentage) as max_score,
        MIN(score_percentage) as min_score,
        AVG(time_spent_seconds) as avg_time_sec
    FROM test_results
    """)
    sum_row = cursor.fetchone()

    total_tests = sum_row["total_tests"] or 0
    unique_users = sum_row["unique_users"] or 0
    avg_score = round(sum_row["avg_score"] or 0, 1)
    max_score = round(sum_row["max_score"] or 0, 1)
    min_score = round(sum_row["min_score"] or 0, 1)
    avg_time_sec = int(sum_row["avg_time_sec"] or 0)

    if total_tests == 0:
        conn.close()
        return {
            "total_tests": 0,
            "unique_users": 0,
            "avg_score": 0,
            "max_score": 0,
            "min_score": 0,
            "avg_time_min": 0,
            "pass_count": 0,
            "fail_count": 0,
            "pass_rate": 0,
            "score_distribution": {"0-39": 0, "40-59": 0, "60-79": 0, "80-100": 0},
            "leaderboard": [],
            "hardest_questions": [],
            "category_performance": [],
            "daily_trend": []
        }

    # Pass vs Fail
    cursor.execute("SELECT COUNT(*) as passed FROM test_results WHERE score_percentage >= ?", (pass_percentage,))
    pass_count = cursor.fetchone()["passed"]
    fail_count = total_tests - pass_count
    pass_rate = round((pass_count / total_tests) * 100, 1)

    # 2. Score distribution
    cursor.execute("""
    SELECT 
        SUM(CASE WHEN score_percentage < 40 THEN 1 ELSE 0 END) as b1,
        SUM(CASE WHEN score_percentage >= 40 AND score_percentage < 60 THEN 1 ELSE 0 END) as b2,
        SUM(CASE WHEN score_percentage >= 60 AND score_percentage < 80 THEN 1 ELSE 0 END) as b3,
        SUM(CASE WHEN score_percentage >= 80 THEN 1 ELSE 0 END) as b4
    FROM test_results
    """)
    dist_row = cursor.fetchone()
    score_distribution = {
        "0-39": dist_row["b1"] or 0,
        "40-59": dist_row["b2"] or 0,
        "60-79": dist_row["b3"] or 0,
        "80-100": dist_row["b4"] or 0
    }

    # 3. Leaderboard (Top 10 users)
    cursor.execute("""
    SELECT 
        telegram_id,
        MAX(full_name) as full_name,
        MAX(username) as username,
        COUNT(*) as attempts_count,
        MAX(score_percentage) as best_score,
        ROUND(AVG(score_percentage), 1) as avg_score,
        ROUND(AVG(time_spent_seconds), 0) as avg_time
    FROM test_results
    GROUP BY telegram_id
    ORDER BY best_score DESC, avg_score DESC
    LIMIT 10
    """)
    leaderboard = [dict(row) for row in cursor.fetchall()]

    # 4. Daily trend (last 7 days)
    cursor.execute("""
    SELECT 
        SUBSTR(completed_at, 1, 10) as test_date,
        COUNT(*) as count,
        ROUND(AVG(score_percentage), 1) as day_avg
    FROM test_results
    GROUP BY test_date
    ORDER BY test_date DESC
    LIMIT 7
    """)
    daily_trend = [dict(row) for row in cursor.fetchall()]
    daily_trend.reverse()

    # 5. In-depth Question & Category Analysis from answers_json
    cursor.execute("SELECT answers_json FROM test_results")
    all_answers_rows = cursor.fetchall()
    conn.close()

    question_stats = {}  # q_id -> { "question": str, "category": str, "total": int, "wrong": int }
    category_stats = {}  # category -> { "total": int, "correct": int }

    for r in all_answers_rows:
        raw_json = r["answers_json"]
        if not raw_json:
            continue
        try:
            items = json.loads(raw_json)
            for item in items:
                qid = item.get("id")
                q_text = item.get("question", "")
                cat = item.get("category") or "Umumiy"
                is_correct = bool(item.get("is_correct"))

                # Question stats
                if qid not in question_stats:
                    question_stats[qid] = {
                        "id": qid,
                        "question": q_text,
                        "category": cat,
                        "total": 0,
                        "wrong": 0
                    }
                question_stats[qid]["total"] += 1
                if not is_correct:
                    question_stats[qid]["wrong"] += 1

                # Category stats
                if cat not in category_stats:
                    category_stats[cat] = {"category": cat, "total": 0, "correct": 0}
                category_stats[cat]["total"] += 1
                if is_correct:
                    category_stats[cat]["correct"] += 1
        except Exception:
            continue

    # Format hardest questions
    hardest_questions = []
    for q_data in question_stats.values():
        if q_data["total"] > 0:
            err_rate = round((q_data["wrong"] / q_data["total"]) * 100, 1)
            hardest_questions.append({
                "id": q_data["id"],
                "question": q_data["question"],
                "category": q_data["category"],
                "total_answered": q_data["total"],
                "wrong_count": q_data["wrong"],
                "error_rate": err_rate
            })

    # Sort hardest by error rate descending
    hardest_questions.sort(key=lambda x: (x["error_rate"], x["wrong_count"]), reverse=True)
    hardest_questions = hardest_questions[:10]

    # Format category performance
    category_performance = []
    for cat_data in category_stats.values():
        tot = cat_data["total"]
        cor = cat_data["correct"]
        acc = round((cor / tot) * 100, 1) if tot > 0 else 0
        category_performance.append({
            "category": cat_data["category"],
            "total_questions": tot,
            "correct_answers": cor,
            "accuracy_percentage": acc
        })
    category_performance.sort(key=lambda x: x["accuracy_percentage"])

    return {
        "total_tests": total_tests,
        "unique_users": unique_users,
        "avg_score": avg_score,
        "max_score": max_score,
        "min_score": min_score,
        "avg_time_min": round(avg_time_sec / 60, 1),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "pass_rate": pass_rate,
        "score_distribution": score_distribution,
        "leaderboard": leaderboard,
        "hardest_questions": hardest_questions,
        "category_performance": category_performance,
        "daily_trend": daily_trend
    }

def get_user_analytics(telegram_id: int) -> Dict[str, Any]:
    """
    Computes personalized analytics for a single participant:
    - Attempt count, best score, average score
    - Category accuracy (strong & weak areas)
    - Trend of all tests taken
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        COUNT(*) as total_attempts,
        MAX(score_percentage) as best_score,
        MIN(score_percentage) as min_score,
        ROUND(AVG(score_percentage), 1) as avg_score,
        ROUND(AVG(time_spent_seconds), 0) as avg_time_sec
    FROM test_results
    WHERE telegram_id = ?
    """, (telegram_id,))
    row = cursor.fetchone()

    total_attempts = row["total_attempts"] or 0
    if total_attempts == 0:
        conn.close()
        return {
            "total_attempts": 0,
            "best_score": 0,
            "avg_score": 0,
            "min_score": 0,
            "avg_time_min": 0,
            "category_performance": [],
            "history": []
        }

    # History
    cursor.execute("""
    SELECT id, score_percentage, correct_answers, total_questions, time_spent_seconds, completed_at, answers_json
    FROM test_results
    WHERE telegram_id = ?
    ORDER BY id ASC
    """, (telegram_id,))
    history_rows = cursor.fetchall()
    conn.close()

    # Category performance for this user
    category_stats = {}
    history_list = []

    for r in history_rows:
        history_list.append({
            "id": r["id"],
            "score": r["score_percentage"],
            "correct": r["correct_answers"],
            "total": r["total_questions"],
            "time_sec": r["time_spent_seconds"],
            "date": r["completed_at"]
        })

        raw_json = r["answers_json"]
        if raw_json:
            try:
                items = json.loads(raw_json)
                for item in items:
                    cat = item.get("category") or "Umumiy"
                    is_correct = bool(item.get("is_correct"))
                    if cat not in category_stats:
                        category_stats[cat] = {"category": cat, "total": 0, "correct": 0}
                    category_stats[cat]["total"] += 1
                    if is_correct:
                        category_stats[cat]["correct"] += 1
            except Exception:
                pass

    cat_list = []
    for c in category_stats.values():
        tot = c["total"]
        cor = c["correct"]
        acc = round((cor / tot) * 100, 1) if tot > 0 else 0
        status = "A'lo" if acc >= 80 else ("Yaxshi" if acc >= 60 else "Qayta takrorlang")
        cat_list.append({
            "category": c["category"],
            "total": tot,
            "correct": cor,
            "accuracy": acc,
            "status": status
        })
    cat_list.sort(key=lambda x: x["accuracy"])

    return {
        "total_attempts": total_attempts,
        "best_score": row["best_score"] or 0,
        "avg_score": row["avg_score"] or 0,
        "min_score": row["min_score"] or 0,
        "avg_time_min": round((row["avg_time_sec"] or 0) / 60, 1),
        "category_performance": cat_list,
        "history": history_list
    }

def generate_results_excel() -> bytes:
    """
    Generates a beautifully formatted Excel report (.xlsx) containing:
    1. Barcha Natijalar (All test results)
    2. Foydalanuvchilar Reytingi (Leaderboard)
    3. Qiyin Savollar Tahlili (Hardest questions)
    """
    from io import BytesIO
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    
    # Header styles
    header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='E2E8F0'),
        right=Side(style='thin', color='E2E8F0'),
        top=Side(style='thin', color='E2E8F0'),
        bottom=Side(style='thin', color='E2E8F0')
    )

    # --- SHEET 1: TEST NATIJALARI ---
    ws1 = wb.active
    ws1.title = "Barcha Natijalar"

    headers1 = ["№", "Foydalanuvchi", "Telegram ID", "To'g'ri", "Noto'g'ri", "Jami", "Ball (%)", "Holat", "Vaqt (daq)", "Sana"]
    ws1.append(headers1)

    for col_idx, _ in enumerate(headers1, 1):
        cell = ws1.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align

    results = get_all_results(limit=1000)
    for idx, r in enumerate(results, 1):
        mins = round(r["time_spent_seconds"] / 60, 1)
        passed = "O'tdi" if r["score_percentage"] >= 60 else "O'tmadi"
        row_data = [
            idx,
            r["full_name"] or "Foydalanuvchi",
            r["telegram_id"],
            r["correct_answers"],
            r["wrong_answers"],
            r["total_questions"],
            f"{r['score_percentage']}%",
            passed,
            mins,
            r["completed_at"]
        ]
        ws1.append(row_data)
        current_row = ws1.max_row
        for col_idx in range(1, len(row_data) + 1):
            c = ws1.cell(row=current_row, column=col_idx)
            c.border = thin_border
            if col_idx in [1, 3, 4, 5, 6, 7, 8, 9, 10]:
                c.alignment = center_align

    # --- SHEET 2: REYTING (LEADERBOARD) ---
    ws2 = wb.create_sheet(title="Foydalanuvchilar Reytingi")
    headers2 = ["O'rin", "Ism Familiya", "Telegram ID", "Username", "Urinishlar soni", "Eng yuqori ball (%)", "O'rtacha ball (%)"]
    ws2.append(headers2)

    for col_idx, _ in enumerate(headers2, 1):
        cell = ws2.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align

    analytics = get_detailed_analytics()
    for idx, u in enumerate(analytics["leaderboard"], 1):
        row_data = [
            idx,
            u["full_name"] or "—",
            u["telegram_id"],
            f"@{u['username']}" if u.get("username") else "—",
            u["attempts_count"],
            f"{u['best_score']}%",
            f"{u['avg_score']}%"
        ]
        ws2.append(row_data)
        current_row = ws2.max_row
        for col_idx in range(1, len(row_data) + 1):
            c = ws2.cell(row=current_row, column=col_idx)
            c.border = thin_border
            if col_idx != 2:
                c.alignment = center_align

    # --- SHEET 3: QIYIN SAVOLLAR TAHLILI ---
    ws3 = wb.create_sheet(title="Qiyin Savollar Tahlili")
    headers3 = ["№", "Savol matni", "Kategoriya", "Javob berilgan", "Xato javoblar", "Xato foizi (%)"]
    ws3.append(headers3)

    for col_idx, _ in enumerate(headers3, 1):
        cell = ws3.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align

    for idx, q in enumerate(analytics["hardest_questions"], 1):
        row_data = [
            idx,
            q["question"],
            q["category"],
            q["total_answered"],
            q["wrong_count"],
            f"{q['error_rate']}%"
        ]
        ws3.append(row_data)
        current_row = ws3.max_row
        for col_idx in range(1, len(row_data) + 1):
            c = ws3.cell(row=current_row, column=col_idx)
            c.border = thin_border
            if col_idx in [1, 3, 4, 5, 6]:
                c.alignment = center_align

    # Auto-adjust column widths for all sheets
    for sheet in [ws1, ws2, ws3]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()

