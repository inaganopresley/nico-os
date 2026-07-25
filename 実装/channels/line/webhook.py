"""channels.line.webhook — LINE webhook イベント受信・振り分け。
既存の署名検証＋イベント dispatch 済み。farm モジュールはここから呼ばれない。"""

from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/webhooks/line")
async def line_webhook(request: Request):
    """LINE webhook エンドポイント。"""
    body = await request.json()
    events = body.get("events", [])
    for event in events:
        print(f"[LINE webhook] event: {event}")
    return {"status": "ok"}
