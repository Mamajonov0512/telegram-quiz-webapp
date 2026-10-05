import sys
from fastapi.testclient import TestClient
from api import app

def check_routes():
    print("=" * 60)
    print("FASTAPI ROUTELARINI TEKSHIRISH:")
    print("=" * 60)
    
    target_endpoints = {
        "POST /api/webhook": False,
        "POST /webhook": False,
        "POST /api/bot/set-webhook": False,
        "GET /api/bot/set-webhook": False,
        "POST /bot/set-webhook": False,
        "GET /bot/set-webhook": False,
        "GET /api/bot/webhook-info": False,
        "GET /bot/webhook-info": False,
    }

    total_routes = 0
    for route in app.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if methods and path:
            total_routes += 1
            for m in methods:
                key = f"{m} {path}"
                if key in target_endpoints:
                    target_endpoints[key] = True

    print(f"Jami ro'yxatdan o'tgan routelar soni: {total_routes}")
    print("\nTalab qilingan endpointlar ro'yxatda mavjudligi:")
    all_ok = True
    for key, found in target_endpoints.items():
        status = "[OK] Mavjud" if found else "[XATO] Topilmadi"
        print(f"  {key:<30} -> {status}")
        if not found:
            all_ok = False

    print("=" * 60)
    if not all_ok:
        print("BA'ZI ENDPOINTLAR TOPILMADI!")
        sys.exit(1)

    print("\nHTTP So'rovlarni jo'natib ko'rish (TestClient):")
    client = TestClient(app)

    # 1. Health check GET /api/webhook
    r1 = client.get("/api/webhook")
    assert r1.status_code == 200, f"GET /api/webhook failed: {r1.status_code}"
    print(f"  GET /api/webhook              -> Status {r1.status_code}: {r1.json()}")

    # 2. Health check GET /webhook
    r2 = client.get("/webhook")
    assert r2.status_code == 200, f"GET /webhook failed: {r2.status_code}"
    print(f"  GET /webhook                  -> Status {r2.status_code}: {r2.json()}")

    # 3. GET /api/bot/webhook-info
    r3 = client.get("/api/bot/webhook-info")
    print(f"  GET /api/bot/webhook-info     -> Status {r3.status_code}: {r3.json()}")

    # 4. POST /api/bot/set-webhook
    r4 = client.post("/api/bot/set-webhook")
    print(f"  POST /api/bot/set-webhook    -> Status {r4.status_code}: {r4.json()}")

    # 5. POST /bot/set-webhook
    r5 = client.post("/bot/set-webhook")
    print(f"  POST /bot/set-webhook        -> Status {r5.status_code}: {r5.json()}")

    print("=" * 60)
    print("BARCHA TESTLAR 100% MUVAFFAQIYATLI O'TDI!")

if __name__ == "__main__":
    check_routes()
