import sys
from fastapi.testclient import TestClient
from api import app
from config import ADMIN_SECRET_KEY
import database as db

def run_tests():
    print("[*] Bo'limlar, ruxsatlar va 'undefined' xatoligi bartaraf etilganligini tekshirish boshlanmoqda...")
    db.init_db()
    client = TestClient(app)
    headers = {"X-Admin-Key": ADMIN_SECRET_KEY}

    # 1. Test Section creation by Admin
    test_sec_name = "Biologiya_Yangi_Test"
    db.delete_section(test_sec_name)
    db.delete_section("Biologiya_Yangi_Tahrir")
    res = client.post("/api/admin/sections/add", json={"name": test_sec_name, "description": "Test bo'limi"}, headers=headers)
    assert res.status_code == 200, f"Add section failed: {res.text}"
    print(f"[+] 1. Admin tomonidan yangi bo'lim yaratish muvaffaqiyatli o'tdi: '{test_sec_name}'")

    # 2. Test Get Sections list
    res = client.get("/api/admin/sections", headers=headers)
    assert res.status_code == 200
    sec_names = [s["name"] for s in res.json()["sections"]]
    assert test_sec_name in sec_names, f"{test_sec_name} not found in sections: {sec_names}"
    print(f"[+] 2. Admin bo'limlar ro'yxatini olish muvaffaqiyatli o'tdi ({len(sec_names)} ta bo'lim)")

    # 3. Add questions to this section
    db.add_question(
        question_text="Biologiya savol 1?",
        option_a="Javob A", option_b="Javob B", option_c="Javob C", option_d="Javob D",
        correct_option="A", category=test_sec_name
    )

    # 4. Check that /api/quiz/categories provides both 'name' and 'category' (no 'undefined' bug!)
    res = client.get("/api/quiz/categories")
    assert res.status_code == 200
    cats = res.json()["categories"]
    for c in cats:
        assert "name" in c and c["name"], f"Missing 'name' in category item: {c}"
        assert "category" in c and c["category"], f"Missing 'category' in category item: {c}"
        assert c["name"] != "undefined" and c["category"] != "undefined", "Found 'undefined' string in category payload!"
    print("[+] 3. Dropdown ma'lumotlarida 'name' va 'category' to'liq mavjud, 'undefined' bugi 100% bartaraf etilgan")

    # 5. User Permissions Test
    user_single = 777111001
    user_multi = 777111002
    user_all = 777111003

    # Add users
    db.add_allowed_user(user_single, "Faqat Biologiya Foydalanuvchi", "bio_user", allowed_sections=[test_sec_name])
    db.add_allowed_user(user_multi, "Ko'p Bo'limli Foydalanuvchi", "multi_user", allowed_sections=[test_sec_name, "Matematika"])
    db.add_allowed_user(user_all, "Barcha Bo'limli Foydalanuvchi", "all_user", allowed_sections="ALL")

    # Verify user_single only sees test_sec_name in categories
    res = client.get(f"/api/quiz/categories?telegram_id={user_single}")
    assert res.status_code == 200
    single_cats = [c["name"] for c in res.json()["categories"]]
    assert single_cats == [test_sec_name], f"Expected only {[test_sec_name]}, got {single_cats}"
    print(f"[+] 4. Faqat bitta bo'limga ruxsati bor foydalanuvchiga faqat o'sha bo'lim ko'rinmoqda: {single_cats}")

    # Verify user_multi only sees test_sec_name and Matematika
    res = client.get(f"/api/quiz/categories?telegram_id={user_multi}")
    assert res.status_code == 200
    multi_cats = sorted([c["name"] for c in res.json()["categories"]])
    assert multi_cats == sorted([test_sec_name, "Matematika"]), f"Expected {[test_sec_name, 'Matematika']}, got {multi_cats}"
    print(f"[+] 5. Bir nechta bo'limga ruxsati bor foydalanuvchiga faqat ruxsat berilgan bo'limlar ko'rinmoqda: {multi_cats}")

    # 6. Test Security: user_single tries to access Matematika (not allowed!)
    res = client.post("/api/quiz/start", json={
        "telegram_id": user_single,
        "category": "Matematika",
        "count": 5
    })
    assert res.status_code in [400, 403], f"Expected rejection, got {res.status_code}: {res.text}"
    print("[+] 6. Ruxsat berilmagan bo'limdan test ishlash server darajasida qat'iy to'xtatildi (400/403)")

    # 7. Test user_single starts quiz in their allowed section
    res = client.post("/api/quiz/start", json={
        "telegram_id": user_single,
        "category": test_sec_name,
        "count": 1
    })
    assert res.status_code == 200, f"Failed starting allowed quiz: {res.text}"
    q_data = res.json()
    assert len(q_data["questions"]) == 1
    assert q_data["questions"][0]["category"] == test_sec_name
    print(f"[+] 7. Ruxsat berilgan bo'limdan test boshlash 100% muvaffaqiyatli ishlamoqda")

    # 8. Test user_single starts 'Barchasi' -> only gets questions from allowed section!
    res = client.post("/api/quiz/start", json={
        "telegram_id": user_single,
        "category": "Barchasi",
        "count": 5
    })
    assert res.status_code == 200
    barchasi_data = res.json()
    for q in barchasi_data["questions"]:
        assert q["category"] == test_sec_name, f"Leaked unpermitted category question: {q['category']}"
    print("[+] 8. 'Barchasi' tanlanganda ham foydalanuvchiga faqat ruxsat etilgan bo'lim savollari tushadi")

    # 9. Test changing user sections via Admin API
    res = client.post("/api/admin/users/sections", json={
        "telegram_id": user_single,
        "sections": ["Matematika"]
    }, headers=headers)
    assert res.status_code == 200
    # Now user_single should have Matematika
    res = client.get(f"/api/quiz/categories?telegram_id={user_single}")
    single_cats_updated = [c["name"] for c in res.json()["categories"]]
    assert single_cats_updated == ["Matematika"], f"Expected ['Matematika'], got {single_cats_updated}"
    print("[+] 9. Admin paneldan foydalanuvchi bo'limlarini o'zgartirish muvaffaqiyatli ishladi")

    # 10. Test section rename
    renamed_sec_name = "Biologiya_Yangi_Tahrir"
    res = client.post("/api/admin/sections/rename", json={
        "old_name": test_sec_name,
        "new_name": renamed_sec_name
    }, headers=headers)
    assert res.status_code == 200
    res = client.get("/api/admin/sections", headers=headers)
    sec_names_renamed = [s["name"] for s in res.json()["sections"]]
    assert renamed_sec_name in sec_names_renamed
    assert test_sec_name not in sec_names_renamed
    print(f"[+] 10. Bo'lim nomini o'zgartirish muvaffaqiyatli ishladi: '{test_sec_name}' -> '{renamed_sec_name}'")

    # 11. Test section delete
    res = client.post("/api/admin/sections/delete", json={"name": renamed_sec_name}, headers=headers)
    assert res.status_code == 200
    res = client.get("/api/admin/sections", headers=headers)
    sec_names_after_del = [s["name"] for s in res.json()["sections"]]
    assert renamed_sec_name not in sec_names_after_del
    print(f"[+] 11. Bo'limni o'chirish muvaffaqiyatli ishladi: '{renamed_sec_name}' o'chirildi")

    print("\n" + "="*50)
    print("BARCHA BO'LIMLAR VA RUXSATLAR TESTLARI 100% MUVAFFAQIYATLI O'TDI! [OK]")
    print("="*50)

if __name__ == "__main__":
    run_tests()
