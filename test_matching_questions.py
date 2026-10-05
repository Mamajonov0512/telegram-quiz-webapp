import parser
import database as db
from api import app
from fastapi.testclient import TestClient

client = TestClient(app)
admin_headers = {'X-Admin-Key': 'admin12345'}

def test_matching_questions():
    print("1. Foydalanuvchining moslashtirish savolini tahlil qilish testi...")
    user_sample = """31. Tushunchalarni ta’riflari bilan moslashtiring.
1.	Adaptatsiya 
2.	Tiklanish 
3.	Turg‘un holat 
4.	Sog‘lom turmush tarzi
a) Ishdan keyingi funksional o‘zgarishlarning ish oldi darajasiga qaytishi
b) Salomatlikni saqlash va mustahkamlashga yo‘naltirilgan kompleks hayot tarzi
c) Organizmning muayyan ta’sir yoki yuklamaga moslashuvi
d) Jismoniy ishda fiziologik funksiyalarning nisbatan barqaror darajasi
A) 1-c, 2-a, 3-d, 4-b
B) 1-a, 2-c, 3-b, 4-d
C) 1-d, 2-b, 3-a, 4-c
D) 1-b, 2-d, 3-c, 4-a
Javob: A"""

    questions, errors = parser.parse_text(user_sample)
    assert len(questions) == 1, f"Kutilgan 1 ta savol, topildi: {len(questions)}"
    assert not errors, f"Xatoliklar bo'lmasligi kerak: {errors}"
    q = questions[0]
    
    # 1. Qatorlar ajralgan holda saqlanganligini tekshirish
    q_lines = q["question_text"].split("\n")
    assert len(q_lines) == 9, f"Kutilgan 9 qator, topildi: {len(q_lines)}: {q_lines}"
    assert "1. Adaptatsiya" in q["question_text"]
    assert "2. Tiklanish" in q["question_text"]
    assert "3. Turg‘un holat" in q["question_text"]
    assert "4. Sog‘lom turmush tarzi" in q["question_text"]
    assert "a) Ishdan keyingi" in q["question_text"]
    assert "b) Salomatlikni" in q["question_text"]
    assert "c) Organizmning" in q["question_text"]
    assert "d) Jismoniy ishda" in q["question_text"]
    
    # 2. Variantlar to'g'ri olinganligini tekshirish
    assert q["option_a"] == "1-c, 2-a, 3-d, 4-b"
    assert q["option_b"] == "1-a, 2-c, 3-b, 4-d"
    assert q["option_c"] == "1-d, 2-b, 3-a, 4-c"
    assert q["option_d"] == "1-b, 2-d, 3-c, 4-a"
    assert q["correct_option"] == "A"
    print("  [+] Moslashtirish savoli va 9 ta qatori 100% to'liq va alohida qatorlarda aniqlandi!")

    print("\n2. Bir nechta savollar ketma-ket bo'sh qatorsiz kelgandagi test...")
    multi_sample = """1. Birinchi savol?
A) 1
B) 2
C) 3
D) 4
Javob: B
31. Tushunchalarni ta’riflari bilan moslashtiring.
1.	Adaptatsiya 
2.	Tiklanish 
3.	Turg‘un holat 
4.	Sog‘lom turmush tarzi
a) Ishdan keyingi funksional o‘zgarishlarning ish oldi darajasiga qaytishi
b) Salomatlikni saqlash va mustahkamlashga yo‘naltirilgan kompleks hayot tarzi
c) Organizmning muayyan ta’sir yoki yuklamaga moslashuvi
d) Jismoniy ishda fiziologik funksiyalarning nisbatan barqaror darajasi
A) 1-c, 2-a, 3-d, 4-b
B) 1-a, 2-c, 3-b, 4-d
C) 1-d, 2-b, 3-a, 4-c
D) 1-b, 2-d, 3-c, 4-a
Javob: A
32. Keyingi savol?
A) X
B) Y
C) Z
D) W
Javob: C"""

    multi_q, multi_err = parser.parse_text(multi_sample)
    assert len(multi_q) == 3, f"Kutilgan 3 ta savol, topildi: {len(multi_q)}"
    assert multi_q[1]["question_text"].split("\n")[0] == "Tushunchalarni ta’riflari bilan moslashtiring."
    assert len(multi_q[1]["question_text"].split("\n")) == 9
    print("  [+] Bo'sh qatorsiz matnda ham moslashtirish savoli va boshqa savollar aniq ajratildi!")

    print("\n3. API orqali matn yuklash (POST /api/admin/questions/import-text)...")
    resp = client.post("/api/admin/questions/import-text", json={"text": user_sample}, headers=admin_headers)
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["success"] is True
    assert res_data["saved_count"] == 1
    print("  [+] API orqali savol bazaga muvaffaqiyatli saqlandi!")

    # Check question in database
    latest_q = db.get_all_questions(limit=1)[0]
    assert "1. Adaptatsiya" in latest_q["question_text"]
    assert "\n" in latest_q["question_text"]
    print("  [+] Bazada savol matnida barcha qatorlar (\\n) saqlanib qolgani tasdiqlandi!")

    # Clean up test question
    db.delete_question(latest_q["id"])
    print("\nBARCHA TESTLAR 100% MUVAFFAQIYATLI O'TDI!")

if __name__ == "__main__":
    test_matching_questions()
