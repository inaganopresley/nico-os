"""billing.routes — Stripe サブスク checkout（既存・Module A の雛形）。
スポット決済は farm/pay.py に新規追加。"""

import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

_stripe = None
try:
    import stripe
    _stripe = stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
except ImportError:
    pass

router = APIRouter()


@router.post("/billing/checkout")
async def checkout(request: Request):
    """サブスク用 Stripe checkout セッション作成。"""
    if not _stripe:
        return {"error": "Stripe not available"}
    data = await request.json()
    subscription_id = data.get("subscription_id", "")
    plan = data.get("plan", "weekly")
    try:
        session = _stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": data.get("price_id"), "quantity": 1}],
            success_url=os.environ.get("STRIPE_SUCCESS_URL", "http://localhost:8000/farm/order/success"),
            cancel_url=os.environ.get("STRIPE_CANCEL_URL", "http://localhost:8000/farm/order/cancel"),
            metadata={"subscription_id": subscription_id, "plan": plan},
        )
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        return {"error": str(e)}


@router.post("/billing/webhook")
async def billing_webhook(request: Request):
    """Stripe webhook サブスクイベント受信。"""
    if not _stripe:
        return {"status": "ok"}
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    try:
        event = _stripe.webhook.construct_event(payload, sig_header, os.environ.get("STRIPE_WEBHOOK_SECRET", ""))
    except ValueError:
        return {"status": "invalid"}
    print(f"[billing webhook] event: {event.type}")
    return {"status": "ok"}
