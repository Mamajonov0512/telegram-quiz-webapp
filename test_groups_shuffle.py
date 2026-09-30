import sys
import sqlite3
import json
from fastapi.testclient import TestClient
from api import app
import database as db

def run_tests():
    print("[*] Guruhlar, aralashtirish va xavfsizlik testlari boshlanmoqda...")
    db.init_db()

    client = TestClient(app)
    test_id = 888777666
    db.add_allowed_user(test_id, "Test User", "testuser", notes="Groups & Shuffle Test")

    # 1. Test Categories endpoint
    res = client.get(f"/api/quiz/categories?telegram_id={test_id}")
    assert res.status_code == 200, f"Categories failed: {res.status_code}"
    cat_data = res.json()
    assert "categories" in cat_data
    assert "total_questions" in cat_data
    print(f"[+] 1. Kategoriya va guruhlar muvaffaqiyatli olindi: {len(cat_data['categories'])} ta guruh mavjud")

    # Make sure we have test questions across multiple categories
    with db.get_connection() as conn:
        cursor = conn.cursor()
        # Insert known questions for Matematika and Ona tili if needed
        cursor.execute("SELECT COUNT(*) FROM questions WHERE category = 'Matematika'")
        mat_count = cursor.fetchone()[0]
        if mat_count < 15:
            for i in range(15):
                cursor.execute("""
                    INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option, explanation, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (f"Matematika savol {i+1}?", f"A javob {i}", f"B javob {i}", f"C javob {i}", f"D javob {i}", "A", "Izoh", "Matematika"))
        
        cursor.execute("SELECT COUNT(*) FROM questions WHERE category = 'Ona tili'")
        ona_count = cursor.fetchone()[0]
        if ona_count < 10:
            for i in range(10):
                cursor.execute("""
                    INSERT INTO questions (question_text, option_a, option_b, option_c, option_d, correct_option, explanation, category)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (f"Ona tili savol {i+1}?", f"Variant A {i}", f"Variant B {i}", f"Variant C {i}", f"Variant D {i}", "B", "Izoh", "Ona tili"))
        conn.commit()

    # 2. Test Category Filtering: Only 'Matematika' questions returned
    res = client.post("/api/quiz/start", json={
        "telegram_id": test_id,
        "category": "Matematika",
        "count": 10
    })
    assert res.status_code == 200, f"Start quiz failed: {res.text}"
    quiz_data = res.json()
    assert quiz_data["session_id"] is not None
    assert len(quiz_data["questions"]) == 10, f"Expected 10 questions, got {len(quiz_data['questions'])}"
    for q in quiz_data["questions"]:
        assert q["category"] == "Matematika", f"Question category mismatch: {q['category']}"
        assert "correct_option" not in q, "Security leak: correct_option exposed!"
        assert "explanation" not in q, "Security leak: explanation exposed!"
    print("[+] 2. Guruh bo'yicha saralash muvaffaqiyatli: faqat tanlangan 'Matematika' savollari qaytdi")

    # 3. Test Question Count Limiting: count = 5 and max 500 cap
    res = client.post("/api/quiz/start", json={
        "telegram_id": test_id,
        "category": "Matematika",
        "count": 5
    })
    assert res.status_code == 200
    quiz_data_5 = res.json()
    assert len(quiz_data_5["questions"]) == 5, f"Expected 5 questions, got {len(quiz_data_5['questions'])}"
    
    # Test capping at 500 when requesting more (e.g. 999)
    res_cap = client.post("/api/quiz/start", json={
        "telegram_id": test_id,
        "category": "Barchasi",
        "count": 999
    })
    assert res_cap.status_code == 200
    quiz_data_cap = res_cap.json()
    assert len(quiz_data_cap["questions"]) <= 500, f"Expected <= 500 questions, got {len(quiz_data_cap['questions'])}"

    # Test admin settings cap at 500
    from config import ADMIN_SECRET_KEY
    set_res = client.post("/api/admin/settings", json={"questions_per_test": 850}, headers={"X-Admin-Key": ADMIN_SECRET_KEY})
    assert set_res.status_code == 200
    saved_per_test = int(db.get_setting("questions_per_test", "50"))
    assert saved_per_test == 500, f"Expected questions_per_test capped at 500, got {saved_per_test}"
    print("[+] 3. Savollar sonini cheklash muvaffaqiyatli: 5 ta berildi va maksimal 500 ta bilan cheklandi")

    # 4. Test Continuous Random Shuffling of Questions and Options
    # Start 10 test sessions for same questions, verify option letters and order vary
    found_shuffled_options = False
    first_session_q_orders = []
    for _ in range(5):
        s_res = client.post("/api/quiz/start", json={
            "telegram_id": test_id,
            "category": "Matematika",
            "count": 10
        })
        s_data = s_res.json()
        q_order = [q["id"] for q in s_data["questions"]]
        first_session_q_orders.append(q_order)

        # Check in DB session_data how options were mapped
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT session_data FROM test_sessions WHERE session_id = ?", (s_data["session_id"],))
            s_record = json.loads(c.fetchone()[0])
            for qid_str, q_info in s_record.items():
                # correct original option is 'A'. If shown letter is not 'A', options were shuffled!
                if q_info["correct_shown_letter"] != "A":
                    found_shuffled_options = True

    assert found_shuffled_options, "Expected options to be shuffled randomly across sessions"
    # Also verify question orders vary across multiple sessions
    unique_orders = len(set(tuple(o) for o in first_session_q_orders))
    assert unique_orders > 1, "Expected question orders to vary randomly across sessions"
    print("[+] 4. Savollar va javoblar o'rni tasodifiy aralashtirilishi (shuffle) muvaffaqiyatli tekshirildi")

    # 5. Test Session Evaluation Accuracy with Shuffled Options
    # Start fresh session
    s_res = client.post("/api/quiz/start", json={
        "telegram_id": test_id,
        "category": "Ona tili",
        "count": 5
    })
    s_data = s_res.json()
    sess_id = s_data["session_id"]
    
    # Read the correct shown letters from the database session_data
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT session_data FROM test_sessions WHERE session_id = ?", (sess_id,))
        s_record = json.loads(c.fetchone()[0])

    # Build 100% correct submission based on shown letters
    perfect_answers = {}
    for q in s_data["questions"]:
        qid_str = str(q["id"])
        perfect_answers[qid_str] = s_record[qid_str]["correct_shown_letter"]

    sub_res = client.post("/api/quiz/submit", json={
        "telegram_id": test_id,
        "full_name": "Test User",
        "time_spent_seconds": 120,
        "answers": perfect_answers,
        "session_id": sess_id
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert sub_data["score"] == 5, f"Expected 5/5, got {sub_data['score']}"
    assert sub_data["percentage"] == 100, f"Expected 100%, got {sub_data['percentage']}"
    assert sub_data["passed"] is True
    print(f"[+] 5. Aralashtirilgan javoblar bilan tekshirish 100% aniqlikda ishladi ({sub_data['score']}/{sub_data['total']})")

    # 6. Verify Anti-Copy & Anti-Screenshot protections in frontend files
    with open("templates/index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    assert "watermarkOverlay" in html_content
    assert "securityShield" in html_content
    assert "quizCategorySelect" in html_content
    assert "countPillsContainer" in html_content

    with open("static/css/style.css", "r", encoding="utf-8") as f:
        css_content = f.read()
    assert "user-select: none !important" in css_content
    assert "@media print" in css_content
    assert "security-shield" in css_content
    assert "watermark-overlay" in css_content

    with open("static/js/app.js", "r", encoding="utf-8") as f:
        js_content = f.read()
    assert "setupWatermark" in js_content
    assert "initSecurityShieldAndProtections" in js_content
    assert "PrintScreen" in js_content
    assert "dismissSecurityShield" in js_content
    print("[+] 6. Anti-kopiya va anti-skrinshot (himoya qalqoni, suv belgisi, matn himoyasi) to'liq mavjud va sozlandi")

    print("\n[SUCCESS] Barcha yangi imkoniyatlar (guruhlar, cheklov, shuffle va himoya) a'lo darajada ishladi!")

if __name__ == "__main__":
    run_tests()
