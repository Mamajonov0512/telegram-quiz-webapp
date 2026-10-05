import database as db
from api import app
from fastapi.testclient import TestClient

client = TestClient(app)
admin_headers = {'X-Admin-Key': 'admin12345'}

def test_users_permissions():
    print("Testing record_pending_user...")
    name_with_apostrophe = "O'ktam Bo'riyev"
    res = db.record_pending_user(9990001, name_with_apostrophe, "oktam_b", "Telegram Bot")
    assert res is True
    users = db.get_allowed_users()
    u = next(x for x in users if x["telegram_id"] == 9990001)
    assert u["full_name"] == name_with_apostrophe
    assert u["is_active"] == 0
    print("  [+] Pending user recorded properly with apostrophe in name")

    print("Testing /api/admin/users/activate-all...")
    resp = client.post("/api/admin/users/activate-all", json={"is_active": True}, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] > 0
    u = next(x for x in db.get_allowed_users() if x["telegram_id"] == 9990001)
    assert u["is_active"] == 1
    print("  [+] activate-all API works, user active now")

    print("Testing /api/admin/users/sections-all...")
    resp = client.post("/api/admin/users/sections-all", json={"sections": "ALL"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    u = next(x for x in db.get_allowed_users() if x["telegram_id"] == 9990001)
    assert u["allowed_sections"] == "ALL"
    print("  [+] sections-all API works")

    print("Testing individual sections with list...")
    resp = client.post("/api/admin/users/sections", json={"telegram_id": 9990001, "sections": ["Matematika"]}, headers=admin_headers)
    assert resp.status_code == 200
    u = next(x for x in db.get_allowed_users() if x["telegram_id"] == 9990001)
    assert "Matematika" in u["allowed_sections"]
    print("  [+] individual sections API works")

    # Cleanup test user
    db.remove_allowed_user(9990001)
    print("\nBARCHA TEKSHIRUVLAR 100% MUVAFFAQIYATLI O'TDI!")

if __name__ == "__main__":
    test_users_permissions()
