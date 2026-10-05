import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends, Header, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import httpx

from config import (
    BASE_DIR, ADMIN_IDS, ADMIN_SECRET_KEY, 
    DEFAULT_TEST_QUESTIONS_COUNT, DEFAULT_TEST_DURATION_MINUTES,
    WEB_APP_URL, WEBHOOK_URL, BOT_TOKEN
)
import database as db
from parser import parse_file, parse_text
from aiogram.types import Update
from bot import get_bot, dp

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
    session_id: Optional[str] = None
    full_name: Optional[str] = ""
    username: Optional[str] = ""
    time_spent_seconds: int
    answers: Dict[str, str]  # question_id -> "A"|"B"|"C"|"D"

class StartQuizRequest(BaseModel):
    telegram_id: int
    category: Optional[str] = "Barchasi"
    count: Optional[int] = None

class AddUserRequest(BaseModel):
    telegram_id: int
    full_name: Optional[str] = ""
    username: Optional[str] = ""
    notes: Optional[str] = ""
    allowed_sections: Optional[Any] = "ALL"

class ToggleUserRequest(BaseModel):
    telegram_id: int
    is_active: bool

class DeleteUserRequest(BaseModel):
    telegram_id: int

class SetUserSectionsRequest(BaseModel):
    telegram_id: int
    sections: Any

class ActivateAllUsersRequest(BaseModel):
    is_active: bool = True

class SetAllUsersSectionsRequest(BaseModel):
    sections: Any = "ALL"

class AddSectionRequest(BaseModel):
    name: str
    description: Optional[str] = ""

class RenameSectionRequest(BaseModel):
    old_name: str
    new_name: str

class DeleteSectionRequest(BaseModel):
    name: str

class SettingsUpdateRequest(BaseModel):
    whitelist_enabled: Optional[bool] = None
    questions_per_test: Optional[int] = None
    duration_minutes: Optional[int] = None
    pass_percentage: Optional[int] = None
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    anti_cheat_enabled: Optional[bool] = None
    category_filter_enabled: Optional[bool] = None
    max_questions_limit: Optional[int] = None

class UpdateCategoryRequest(BaseModel):
    category: str

class RenameAllCategoryRequest(BaseModel):
    new_category: str
    old_category: Optional[str] = None

class ImportQuestionsTextRequest(BaseModel):
    text: str

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

    # Record user as pending if new or update their name
    user_name = f"{data.first_name or ''} {data.last_name or ''}".strip()
    db.record_pending_user(telegram_id, user_name, data.username or "", "Web App")

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
            "pass_percentage": int(db.get_setting("pass_percentage", "60")),
            "shuffle_questions": db.get_setting("shuffle_questions", "true").lower() == "true",
            "shuffle_options": db.get_setting("shuffle_options", "true").lower() == "true",
            "anti_cheat_enabled": db.get_setting("anti_cheat_enabled", "true").lower() == "true",
            "category_filter_enabled": db.get_setting("category_filter_enabled", "true").lower() == "true",
            "max_questions_limit": int(db.get_setting("max_questions_limit", "500"))
        }
    }

@app.get("/api/quiz/categories")
async def get_quiz_categories(telegram_id: Optional[int] = None):
    cats = db.get_categories(telegram_id=telegram_id)
    total_q = sum(c["count"] for c in cats) if telegram_id else db.get_questions_count()
    default_count = int(db.get_setting("questions_per_test", str(DEFAULT_TEST_QUESTIONS_COUNT)))
    return {
        "categories": cats,
        "total_questions": total_q,
        "default_count": default_count
    }

@app.post("/api/quiz/start")
async def start_quiz_session(data: StartQuizRequest):
    if not db.is_user_allowed(data.telegram_id):
        raise HTTPException(status_code=403, detail="Sizga ruxsat berilmagan.")
    
    count = data.count
    if count is not None:
        count = min(max(1, count), 500)

    session = db.create_test_session(
        telegram_id=data.telegram_id,
        category=data.category,
        count=count
    )
    if "error" in session and session.get("error"):
        raise HTTPException(status_code=400, detail=session["error"])
    return session

@app.get("/api/quiz/questions")
async def get_quiz_questions(telegram_id: Optional[int] = None, category: Optional[str] = None, count: Optional[int] = None):
    if not telegram_id or not db.is_user_allowed(telegram_id):
        raise HTTPException(status_code=403, detail="Sizga ruxsat berilmagan.")

    if count is not None:
        count = min(max(1, count), 500)

    # Using session generator for randomized questions and options
    session = db.create_test_session(telegram_id=telegram_id, category=category, count=count)
    if "error" in session and session.get("error"):
        raise HTTPException(status_code=400, detail=session["error"])
    return session

@app.post("/api/quiz/submit")
async def submit_quiz(data: SubmitQuizRequest):
    if not db.is_user_allowed(data.telegram_id):
        raise HTTPException(status_code=403, detail="Sizga ruxsat berilmagan.")

    # 1. If session_id is provided, evaluate against shuffled options session
    if data.session_id:
        result = db.evaluate_session_submission(
            session_id=data.session_id,
            submitted_answers=data.answers,
            time_spent_seconds=data.time_spent_seconds,
            full_name=data.full_name or "",
            username=data.username or ""
        )
        if result:
            return result

    # 2. Fallback legacy evaluation
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
        notes=data.notes or "Veb panel orqali qo'shildi",
        allowed_sections=data.allowed_sections if data.allowed_sections is not None else "ALL"
    )
    return {"success": success}

@app.post("/api/admin/users/sections")
async def api_admin_set_user_sections(data: SetUserSectionsRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.set_user_allowed_sections(data.telegram_id, data.sections)
    return {"success": success}

@app.get("/api/admin/sections")
async def api_admin_get_sections(x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    sections = db.get_all_sections()
    return {"sections": sections}

@app.post("/api/admin/sections/add")
async def api_admin_add_section(data: AddSectionRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.add_section(name=data.name, description=data.description or "")
    if not success:
        raise HTTPException(status_code=400, detail="Bo'lim yaratilmadi. Bu bo'lim allaqachon mavjud bo'lishi mumkin.")
    return {"success": True, "sections": db.get_all_sections()}

@app.post("/api/admin/sections/rename")
async def api_admin_rename_section(data: RenameSectionRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.rename_section(old_name=data.old_name, new_name=data.new_name)
    if not success:
        raise HTTPException(status_code=400, detail="Bo'lim nomini o'zgartirib bo'lmadi.")
    return {"success": True, "sections": db.get_all_sections()}

@app.post("/api/admin/sections/delete")
async def api_admin_delete_section(data: DeleteSectionRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.delete_section(name=data.name)
    return {"success": success, "sections": db.get_all_sections()}

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

@app.post("/api/admin/users/activate-all")
async def api_admin_activate_all_users(data: ActivateAllUsersRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    count = db.activate_all_users(data.is_active)
    return {"success": True, "count": count}

@app.post("/api/admin/users/sections-all")
async def api_admin_set_all_users_sections(data: SetAllUsersSectionsRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    count = db.set_all_users_allowed_sections(data.sections)
    return {"success": True, "count": count}

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

@app.post("/api/admin/questions/{qid}/category")
async def api_admin_update_question_category(qid: int, data: UpdateCategoryRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    success = db.update_question_category(qid, data.category)
    return {"success": success}

@app.post("/api/admin/questions/rename-category")
async def api_admin_rename_category(data: RenameAllCategoryRequest, x_admin_key: Optional[str] = Header(None)):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    count = db.update_all_questions_category(new_category=data.new_category, old_category=data.old_category)
    return {"success": True, "updated_count": count}

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

@app.post("/api/admin/questions/import-text")
async def api_admin_import_questions_text(
    data: ImportQuestionsTextRequest, 
    x_admin_key: Optional[str] = Header(None)
):
    if not verify_admin(x_admin_key):
        raise HTTPException(status_code=401, detail="Administrator kaliti noto'g'ri.")
    
    questions, errors = parse_text(data.text)
    if not questions:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "errors": errors or ["Matndan birorta ham to'g'ri savol aniqlanmadi."]
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
        q_count = min(max(1, data.questions_per_test), 500)
        db.set_setting("questions_per_test", str(q_count))
    if data.duration_minutes is not None:
        db.set_setting("duration_minutes", str(data.duration_minutes))
    if data.pass_percentage is not None:
        db.set_setting("pass_percentage", str(data.pass_percentage))
    if data.shuffle_questions is not None:
        db.set_setting("shuffle_questions", "true" if data.shuffle_questions else "false")
    if data.shuffle_options is not None:
        db.set_setting("shuffle_options", "true" if data.shuffle_options else "false")
    if data.anti_cheat_enabled is not None:
        db.set_setting("anti_cheat_enabled", "true" if data.anti_cheat_enabled else "false")
    if data.category_filter_enabled is not None:
        db.set_setting("category_filter_enabled", "true" if data.category_filter_enabled else "false")
    if data.max_questions_limit is not None:
        capped_max = min(max(1, data.max_questions_limit), 500)
        db.set_setting("max_questions_limit", str(capped_max))

    return {"success": True, "settings": db.get_all_settings()}
 
# --- STARTUP EVENT (DB INITIALIZATION) ---
@app.on_event("startup")
async def startup_event():
    try:
        db.init_db()
        logger.info("Baza ma'lumotlari tekshirildi va ishga tushirildi.")
    except Exception as e:
        logger.error(f"Baza ishga tushirishda xatolik: {e}")

def build_webhook_url(raw: str) -> str:
    """Telegram webhook URL'ni xavfsiz va aniq formatda shakllantiradi."""
    target = (raw or "").strip().rstrip("/")
    if not target:
        return ""
    if not target.startswith("http://") and not target.startswith("https://"):
        target = f"https://{target}"
    if target.startswith("http://") and "localhost" not in target and "127.0.0.1" not in target:
        target = "https://" + target[len("http://"):]
    if target.endswith("/api/webhook"):
        return target
    if target.endswith("/webhook"):
        return target[:-8] + "/api/webhook"
    return f"{target}/api/webhook"

# --- TELEGRAM WEBHOOK ROUTES (VERCEL / SERVERLESS COMPATIBILITY) ---
@app.get("/api/webhook")
@app.get("/webhook")
async def webhook_health():
    return {"ok": True, "status": "Telegram webhook endpoint faol"}

@app.post("/api/webhook")
@app.post("/webhook")
async def telegram_webhook(request: Request):
    bot_instance = get_bot()
    if not bot_instance:
        return JSONResponse({"ok": False, "error": "BOT_TOKEN ko'rsatilmagan"}, status_code=400)
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot_instance})
        await dp.feed_update(bot_instance, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook update xatosi: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.get("/api/bot/webhook-info")
@app.get("/bot/webhook-info")
async def get_webhook_info():
    if not BOT_TOKEN:
        return {"ok": False, "error": "BOT_TOKEN ko'rsatilmagan"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as http_client:
            resp = await http_client.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo")
            return resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/api/bot/set-webhook")
@app.get("/api/bot/set-webhook")
@app.post("/bot/set-webhook")
@app.get("/bot/set-webhook")
async def set_telegram_webhook(request: Request, url: Optional[str] = Query(None)):
    if not BOT_TOKEN:
        raise HTTPException(status_code=400, detail="BOT_TOKEN ko'rsatilmagan")
    
    # 1. Query parameter orqali berilgan URL
    chosen_url = url or ""

    # 2. POST body JSON da yuborilgan url (agar mavjud bo'lsa)
    if not chosen_url and request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                chosen_url = body.get("url", "")
        except Exception:
            pass

    # 3. Environment variables (WEBHOOK_URL yoki WEB_APP_URL)
    if not chosen_url:
        chosen_url = WEBHOOK_URL or WEB_APP_URL

    # 4. Request headerlari orqali aniqlangan domen (x-forwarded-host)
    if not chosen_url:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        if host:
            chosen_url = f"https://{host}"

    webhook_url = build_webhook_url(chosen_url)
    if not webhook_url:
        raise HTTPException(status_code=400, detail="Webhook URL yoki WEB_APP_URL aniqlanmadi")

    try:
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            resp = await http_client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                json={"url": webhook_url}
            )
            tg_data = resp.json()

        success = bool(tg_data.get("ok"))
        return {
            "ok": success,
            "webhook_url": webhook_url,
            "telegram_response": tg_data,
            "message": "Telegram webhook muvaffaqiyatli o'rnatildi!" if success else tg_data.get("description", "Xatolik")
        }
    except Exception as e:
        logger.error(f"Webhook o'rnatishda xatolik: {e}")
        raise HTTPException(status_code=500, detail=str(e))


