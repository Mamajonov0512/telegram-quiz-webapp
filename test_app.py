import sys
from fastapi.testclient import TestClient
from api import app
from database import init_db, add_allowed_user, is_user_allowed, get_questions_count

def run_tests():
    print("[*] Testlar boshlanmoqda...")
    init_db()

    client = TestClient(app)

    # 1. Test index page
    res = client.get("/")
    assert res.status_code == 200, f"Index page failed: {res.status_code}"
    print("[+] 1. Index sahifasi (Web App) ishlayapti (200 OK)")

    # 2. Test admin page
    res = client.get("/admin")
    assert res.status_code == 200, f"Admin page failed: {res.status_code}"
    print("[+] 2. Admin panel sahifasi ishlayapti (200 OK)")

    # 3. Test Auth Check: allowed user
    test_id = 999888777
    add_allowed_user(test_id, "Testchi", "testchi", notes="Unit test")

    res = client.post("/api/auth/check", json={
        "telegram_id": test_id,
        "first_name": "Testchi"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["authorized"] is True, f"Expected authorized True, got {data}"
    print("[+] 3. Ruxsat berilgan ID tekshiruvi muvaffaqiyatli o'tdi (authorized: True)")

    # 4. Test Auth Check: unauthorized user
    res = client.post("/api/auth/check", json={
        "telegram_id": 111222333,
        "first_name": "Begona"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["authorized"] is False, f"Expected authorized False, got {data}"
    print("[+] 4. Ruxsat berilmagan ID tekshiruvi muvaffaqiyatli to'xtatildi (authorized: False)")

    # 5. Test Quiz Questions fetching
    res = client.get(f"/api/quiz/questions?telegram_id={test_id}")
    assert res.status_code == 200
    q_data = res.json()
    assert len(q_data["questions"]) > 0, "No questions returned"
    # Ensure correct_option is NOT leaked in client payload!
    first_q = q_data["questions"][0]
    assert "correct_option" not in first_q, "Security leak: correct_option exposed in payload!"
    assert "explanation" not in first_q, "Security leak: explanation exposed in payload!"
    print(f"[+] 5. Savollar muvaffaqiyatli va xavfsiz yuklandi ({len(q_data['questions'])} ta savol, to'g'ri javoblar yashirilgan)")

    # 6. Test Quiz Submission
    sample_q = q_data["questions"][:5]
    answers = {str(q["id"]): "A" for q in sample_q}
    sub_res = client.post("/api/quiz/submit", json={
        "telegram_id": test_id,
        "full_name": "Testchi",
        "time_spent_seconds": 120,
        "answers": answers
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert "score" in sub_data
    assert "percentage" in sub_data
    assert "review" in sub_data
    print(f"[+] 6. Test topshirish va natijalarni hisoblash muvaffaqiyatli (Ball: {sub_data['percentage']}%)")

    # 7. Test Admin API Stats
    admin_res = client.get("/api/admin/stats", headers={"X-Admin-Key": "admin12345"})
    assert admin_res.status_code == 200
    print("[+] 7. Admin statistika API muvaffaqiyatli ishladi")

    # 8. Test Template downloads
    t_res = client.get("/api/templates/test_shablon.xlsx")
    assert t_res.status_code == 200
    print("[+] 8. Shablon fayllarni yuklab olish muvaffaqiyatli ishladi (.xlsx)")

    print("BARCHA TESTLAR 100% MUVAFFAQIYATLI O'TDI! [OK]")
    print("="*50)

if __name__ == "__main__":
    run_tests()
