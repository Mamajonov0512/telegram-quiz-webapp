import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    BASE_DIR, ADMIN_IDS, ADMIN_SECRET_KEY, 
    DEFAULT_TEST_QUESTIONS_COUNT, DEFAULT_TEST_DURATION_MINUTES
)
import database as db
from parser import parse_file

logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Web App Test Platform")

# CORS middleware for WebApp embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static and template directories
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
SAMPLES_DIR = BASE_DIR / "samples"

STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
SAMPLES_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# --- AUTH VERIFICATION ---
def verify_admin(x_admin_key: Optional[str] = Header(None), admin_id: Optional[int] = None) -> bool:
    if x_admin_key and x_admin_key == ADMIN_SECRET_KEY:
        return True
    if admin_id and admin_id in ADMIN_IDS:
        return True
    return False

# --- PYDANTIC SCHEMAS ---
class AuthCheckRequest(BaseModel):
    telegram_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    init_data: Optional[str] = None

class SubmitQuizRequest(BaseModel):
    telegram_id: int
    full_name: Optional[str] = ""
    username: Optional[str] = ""
    time_spent_seconds: int
    answers: Dict[str, str]  # question_id -> "A"|"B"|"C"|"D"

class AddUserRequest(BaseModel):
    telegram_id: int
    full_name: Optional[str] = ""
    username: Optional[str] = ""
    notes: Optional[str] = ""

class ToggleUserRequest(BaseModel):
    telegram_id: int
    is_active: bool

class DeleteUserRequest(BaseModel):
    telegram_id: int

class SettingsUpdateRequest(BaseModel):
    whitelist_enabled: Optional[bool] = None
    questions_per_test: Optional[int] = None
    duration_minutes: Optional[int] = None
    pass_percentage: Optional[int] = None

# --- HTML ROUTES ---

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h2>index.html topilmadi</h2>", status_code=404)
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    admin_file = TEMPLATES_DIR / "admin.html"
    if not admin_file.exists():
        return HTMLResponse("<h2>admin.html topilmadi</h2>", status_code=404)
    with open(admin_file, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/api/templates/{filename}")
async def download_template(filename: str):
    allowed_files = ["test_shablon.xlsx", "test_shablon.json", "test_shablon.txt"]
    if filename not in allowed_files:
        raise HTTPException(status_code=404, detail="Shablon fayl topilmadi")
    file_path = SAMPLES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fayl mavjud emas")
    return FileResponse(path=file_path, filename=filename)

# --- USER API ROUTES ---

@app.post("/api/auth/check")
async def check_user_access(data: AuthCheckRequest):
    telegram_id = data.telegram_id
    if not telegram_id:
        return {
            "authorized": False,
            "reason": "no_id",
            "message": "Telegram foydalanuvchi ma'lumotlari topilmadi."
        }

    is_admin = telegram_id in ADMIN_IDS
    is_allowed = db.is_user_allowed(telegram_id)
    
    total_q = db.get_questions_count()
    duration_mins = int(db.get_setting("duration_minutes", str(DEFAULT_TEST_DURATION_MINUTES)))
    per_test = int(db.get_setting("questions_per_test", str(DEFAULT_TEST_QUESTIONS_COUNT)))
    q_count = min(per_test, total_q) if total_q > 0 else per_test

    return {
        "authorized": is_allowed,
        "is_admin": is_admin,
        "telegram_id": telegram_id,
        "user_name": f"{data.first_name or ''} {data.last_name or ''}".strip() or "Foydalanuvchi",
        "settings": {
            "questions_per_test": q_count,
            "duration_minutes": duration_mins,
            "total_available_questions": total_q,
            "pass_percentage": int(db.get_setting("pass_percentage", "60"))
        }
    }

@app.get("/api/quiz/questions")
async def get_quiz_questions(telegram_id: Optional[int] = None):
    if not telegram_id or not db.is_user_allowed(telegram_id):
        raise HTTPException(status_code=403, detail="Sizga ruxsat berilmagan.")

    total_avail = db.get_questions_count()
    if total_avail == 0:
        return {"questions": [], "count": 0, "duration_minutes": 0}

    q_count = int(db.get_setting("questions_per_test", str(DEFAULT_TEST_QUESTIONS_COUNT)))
    duration = int(db.get_setting("duration_minutes", str(DEFAULT_TEST_DURATION_MINUTES)))
    shuffle = db.get_setting("shuffle_questions", "true").lower() == "true"

    raw_questions = db.get_test_questions(count=q_count, shuffle=shuffle)

    # Sanitize questions: DO NOT expose correct_option or explanation to avoid client-side cheating
    sanitized = []
    for idx, q in enumerate(raw_questions, start=1):
        sanitized.append({
            "id": q["id"],
            "index": idx,
            "question": q["question_text"],
            "options": {
                "A": q["option_a"],
                "B": q["option_b"],
                "C": q["option_c"],
                "D": q["option_d"]
            },
            "category": q.get("category", "Umumiy")
        })

    return {
        "questions": sanitized,
        "count": len(sanitized),
        "duration_minutes": duration
    }

@app.post("/api/quiz/submit")
async def submit_quiz(data: SubmitQuizRequest):
    if not db.is_user_allowed(data.telegram_id):
        raise HTTPException(status_code=403, detail="Sizga ruxsat berilmagan.")

    submitted_answers = data.answers
    total_questions = len(submitted_answers)
    
    if total_questions == 0:
        return {"error": "Hech qanday javob yuborilmadi."}

    # Fetch questions from DB by IDs
    conn = db.get_connection()
    cursor = conn.cursor()
    
    q_ids = [int(qid) for qid in submitted_answers.keys() if qid.isdigit()]
    if not q_ids:
        conn.close()
        raise HTTPException(status_code=400, detail="Savol identifikatorlari yaroqsiz.")

    placeholders = ",".join("?" * len(q_ids))
    cursor.execute(f"SELECT * FROM questions WHERE id IN ({placeholders})", q_ids)
    rows = cursor.fetchall()
    conn.close()

    db_map = {str(r["id"]): dict(r) for r in rows}

    correct_count = 0
    wrong_count = 0
    detailed_review = []

    for qid_str, user_ans in submitted_answers.items():
        q_data = db_map.get(qid_str)
        if not q_data:
            continue
            
        correct_ans = q_data["correct_option"].upper()
        user_ans = (user_ans or "").upper()
        is_correct = (user_ans == correct_ans)

        if is_correct:
            correct_count += 1
        else:
            wrong_count += 1

        detailed_review.append({
            "id": q_data["id"],
            "question": q_data["question_text"],
            "options": {
                "A": q_data["option_a"],
                "B": q_data["option_b"],
                "C": q_data["option_c"],
                "D": q_data["option_d"]
            },
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q_data.get("explanation", ""),
            "category": q_data.get("category", "")
        })

    score_percentage = round((correct_count / total_questions) * 100, 1) if total_questions > 0 else 0
    pass_percentage = int(db.get_setting("pass_percentage", "60"))
    passed = score_percentage >= pass_percentage

    # Save to test_results
    review_json = json.dumps(detailed_review, ensure_ascii=False)
    db.save_test_result(
        telegram_id=data.telegram_id,
        full_name=data.full_name or "",
        username=data.username or "",
        total_questions=total_questions,
        correct_answers=correct_count,
        wrong_answers=wrong_count,
        score_percentage=score_percentage,
        time_spent_seconds=data.time_spent_seconds,
        answers_json=review_json
    )

    return {
        "score": correct_count,
        "total": total_questions,
        "wrong": wrong_count,
        "percentage": score_percentage,
        "passed": passed,
        "pass_percentage": pass_percentage,
        "time_spent_seconds": data.time_spent_seconds,
        "review": detailed_review
    }

@app.get("/api/user/history")
async def get_user_history(telegram_id: int):
    results = db.get_user_results(telegram_id, limit=20)
    return {"results": results}

@app.get("/api/user/analytics")
async def get_user_analytics_api(telegram_id: int):
    analytics = db.get_user_analytics(telegram_id)
    return {"analytics": analytics}

# --- ADMIN API ROUTES ---

@app.get("/api/admin/stats")
async def api_admin_stats(x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    stats = db.get_stats()
    settings = db.get_all_settings()
    return {"stats": stats, "settings": settings}

@app.get("/api/admin/analytics")
async def api_admin_analytics(x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    analytics = db.get_detailed_analytics()
    return {"analytics": analytics}

@app.get("/api/admin/export/excel")
async def api_admin_export_excel(x_admin_key: Optional[str] = Header(None), key: Optional[str] = None):
    # Support both header and query param for direct browser download
    auth_key = x_admin_key or key
    if not verify_admin(auth_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    excel_bytes = db.generate_results_excel()
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test_natijalari_tahlil.xlsx"}
    )

@app.get("/api/admin/users")
async def api_admin_get_users(x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    users = db.get_allowed_users()
    return {"users": users}

@app.post("/api/admin/users/add")
async def api_admin_add_user(data: AddUserRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.add_allowed_user(
        telegram_id=data.telegram_id,
        full_name=data.full_name or "",
        username=data.username or "",
        notes=data.notes or "Veb panel orqali qo'shildi"
    )
    return {"success": success}

@app.post("/api/admin/users/remove")
async def api_admin_remove_user(data: DeleteUserRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.remove_allowed_user(data.telegram_id)
    return {"success": success}

@app.post("/api/admin/users/toggle")
async def api_admin_toggle_user(data: ToggleUserRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.toggle_user_active(data.telegram_id, data.is_active)
    return {"success": success}

@app.get("/api/admin/questions")
async def api_admin_get_questions(
    limit: int = 100, 
    offset: int = 0, 
    x_admin_key: Optional[str] = Header(None)
):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    questions = db.get_all_questions(limit=limit, offset=offset)
    total = db.get_questions_count()
    return {"questions": questions, "total": total}

@app.delete("/api/admin/questions/{qid}")
async def api_admin_delete_question(qid: int, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.delete_question(qid)
    return {"success": success}

@app.post("/api/admin/questions/clear")
async def api_admin_clear_questions(x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.clear_all_questions()
    return {"success": success}

@app.post("/api/admin/upload")
async def api_admin_upload_file(
    file: UploadFile = File(...), 
    x_admin_key: Optional[str] = Header(None)
):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    
    filename = file.filename or "unknown.xlsx"
    file_bytes = await file.read()
    
    questions, errors = parse_file(filename, file_bytes)
    if not questions:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "errors": errors or ["Fayldan birorta ham to'g'ri savol topilmadi."]
            }
        )

    saved_count = db.bulk_add_questions(questions)
    total = db.get_questions_count()

    return {
        "success": True,
        "parsed_count": len(questions),
        "saved_count": saved_count,
        "total_questions": total,
        "warnings": errors
    }

@app.get("/api/admin/results")
async def api_admin_get_results(limit: int = 50, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    results = db.get_all_results(limit=limit)
    return {"results": results}

@app.post("/api/admin/settings")
async def api_admin_update_settings(data: SettingsUpdateRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    
    if data.whitelist_enabled is not None:
        db.set_setting("whitelist_enabled", "true" if data.whitelist_enabled else "false")
    if data.questions_per_test is not None:
        db.set_setting("questions_per_test", str(data.questions_per_test))
    if data.duration_minutes is not None:
        db.set_setting("duration_minutes", str(data.duration_minutes))
    if data.pass_percentage is not None:
        db.set_setting("pass_percentage", str(data.pass_percentage))

    return {"success": True, "settings": db.get_all_settings()}
