"""main.py — NICO-OS アプリ起動。
farm モジュールの include_router と startup init を追加済み。
"""

import os
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# コア初期化
from core.db import conn
from core.store import get_or_create_customer


def _timed(name: str, fn):
    """startup 時に非同期で実行するヘルパ。"""
    def wrapper():
        print(f"[startup] {name} ...")
        start = time.time()
        try:
            fn()
            print(f"[startup] {name} done ({time.time() - start:.2f}s)")
        except Exception as e:
            print(f"[startup] {name} ERROR: {e}")
    return wrapper


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    _timed("core", lambda: None)()  # core テーブルは init_core で（db.py の conn を通して）
    _timed("farm", __import__("farm.store", fromlist=["init_farm"]).init_farm)()

    yield

    # shutdown
    print("[shutdown] done")


app = FastAPI(title="NICO-OS / 淡路ベジ便", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Router registration（既存 + farm）
# ============================================================

# farm モジュール（Module A: 受注・顧客・決済）
from farm import routes as farm_routes, store as farm_store

app.include_router(farm_routes.router)

# billing モジュール（サブスク checkout）
try:
    from billing import routes as billing_routes
    app.include_router(billing_routes.router)
except ImportError:
    pass


# ============================================================
# Stripe webhook（farm 分岐付き）
# ============================================================

@app.post("/billing/webhook")
async def webhook_handler(request: Request):
    """Stripe webhook。既存サブスク + farm スポット決済の両方を処理。"""
    import os
    sig = request.headers.get("stripe-signature", "")
    payload = await request.body()

    try:
        import stripe
        event = stripe.webhook.construct_event(
            payload, sig, os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        )
    except ValueError:
        return {"status": "invalid_payload"}
    except Exception:
        # Stripe が設定されていない場合は stub として受ける
        print(f"[webhook stub] event type unknown (stripe not configured)")
        return {"status": "ok"}

    event_type = event.get("type", "")
    data = event.get("object", {})

    if event_type == "checkout.session.completed":
        # farm スポット決済
        metadata = data.get("metadata", {})
        order_id = metadata.get("farm_order_id")
        if order_id:
            from farm.pay import mark_paid
            mark_paid(order_id, data.get("id", ""))
            print(f"[webhook] farm order #{order_id} → paid")

    elif event_type == "invoice.payment_succeeded":
        # サブスク継続
        pass

    return {"status": "ok"}


# ============================================================
# 簡易認証（管理画面保護）
# ============================================================

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "devtoken")


@app.middleware("http")
async def admin_auth(request: Request, call_next):
    """?key=ADMIN_TOKEN で管理系を開放。GET/POST 両対応。"""
    path = request.url.path
    if "/admin" in path and ADMIN_TOKEN:
        key = request.query_params.get("key", "")
        # POST の場合は body もチェック
        if not key and request.method == "POST":
            form = await request.form()
            key = form.get("key", "")
        if key != ADMIN_TOKEN:
            from fastapi.responses import HTMLResponse
            return HTMLResponse(
                f"""<!DOCTYPE html><html><body>
                <h1>管理画面</h1>
                <p>認証が必要です。</p>
                <form action="/farm/admin/orders?key={ADMIN_TOKEN}">
                  <input name="key" placeholder="Admin key">
                  <button type="submit">ログイン</button>
                </form>
                </body></html>""",
                status_code=401,
            )

    response = await call_next(request)
    return response


# ============================================================
# Health check
# ============================================================

@app.get("/health")
def health():
    return {"status": "ok", "module": "nico-os + farm"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
