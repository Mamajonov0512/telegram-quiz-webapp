from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Request

from config import WEBHOOK_SECRET, WEBHOOK_URL

app = FastAPI(title="Schedule Bot API")


@app.get("/")
async def healthcheck() -> dict:
    return {"status": "ok", "message": "Schedule bot API ready"}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "webhook_url": WEBHOOK_URL}


@app.post("/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)) -> dict:
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret token")
    payload = await request.json()
    return {"status": "accepted", "payload": payload}
